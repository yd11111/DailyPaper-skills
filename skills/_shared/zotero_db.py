"""Shared Zotero database read-only queries.

Used by: paper_daemon.py (batch processing), zotero_helper.py (CLI tool).
All functions take a sqlite3.Connection as first arg (connection-passing pattern).
"""

import shutil
import sqlite3
from pathlib import Path
from typing import Optional

from user_config import zotero_db_path, zotero_storage_dir, temp_file_path

ZOTERO_DB = zotero_db_path()
ZOTERO_STORAGE = zotero_storage_dir()
_TEMP_DB = temp_file_path("zotero_readonly.sqlite")


def copy_readonly() -> sqlite3.Connection:
    """Copy Zotero DB to temp location (avoids locking) and return connection."""
    shutil.copy(ZOTERO_DB, _TEMP_DB)
    return sqlite3.connect(str(_TEMP_DB))


def get_all_child_collections(conn: sqlite3.Connection, collection_id: int) -> list[int]:
    """Recursively collect all child collection IDs (including self)."""
    cursor = conn.cursor()
    cursor.execute("SELECT collectionID, parentCollectionID FROM collections")
    all_collections = cursor.fetchall()

    children_map: dict[int, list[int]] = {}
    for cid, parent_id in all_collections:
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(cid)

    result = [collection_id]

    def collect(cid: int) -> None:
        if cid in children_map:
            for child_id in children_map[cid]:
                result.append(child_id)
                collect(child_id)

    collect(collection_id)
    return result


def get_collection_path(conn: sqlite3.Connection, collection_id: int) -> str:
    """Build full path string for a collection (e.g. 'Parent/Child/Leaf')."""
    cursor = conn.cursor()
    cursor.execute("SELECT collectionID, collectionName, parentCollectionID FROM collections")
    collections = {row[0]: {"name": row[1], "parent": row[2]} for row in cursor.fetchall()}

    path_parts: list[str] = []
    current: Optional[int] = collection_id
    while current:
        if current in collections:
            path_parts.insert(0, collections[current]["name"])
            current = collections[current]["parent"]
        else:
            break
    return "/".join(path_parts)


def find_collection(conn: sqlite3.Connection, name: str) -> tuple[Optional[int], Optional[str]]:
    """Find collection by name (case-insensitive, substring match). Returns (id, path) or (None, None)."""
    cursor = conn.cursor()
    cursor.execute("SELECT collectionID, collectionName, parentCollectionID FROM collections")
    collections = {row[0]: {"name": row[1], "parent": row[2]} for row in cursor.fetchall()}

    for cid, info in collections.items():
        if info["name"].lower() == name.lower():
            return cid, get_collection_path(conn, cid)
    for cid, info in collections.items():
        if name.lower() in info["name"].lower():
            return cid, get_collection_path(conn, cid)
    return None, None


def get_papers_in_collection(
    conn: sqlite3.Connection, collection_id: int, recursive: bool = True
) -> list[dict]:
    """Get papers in a collection. Returns list of {item_id, title}."""
    cursor = conn.cursor()
    collection_ids = get_all_child_collections(conn, collection_id) if recursive else [collection_id]
    placeholders = ",".join("?" * len(collection_ids))
    query = f"""
        SELECT DISTINCT i.itemID, idv.value as title
        FROM items i
        JOIN collectionItems ci ON i.itemID = ci.itemID
        JOIN itemData id ON i.itemID = id.itemID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        JOIN fields f ON id.fieldID = f.fieldID
        WHERE ci.collectionID IN ({placeholders}) AND f.fieldName = 'title' AND i.itemTypeID != 14
    """
    cursor.execute(query, collection_ids)
    return [{"item_id": row[0], "title": row[1]} for row in cursor.fetchall()]


def get_pdf_path(conn: sqlite3.Connection, item_id: int) -> Optional[str]:
    """Get the PDF file path for an item. Returns absolute path or None."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ia.path, items.key
        FROM itemAttachments ia
        JOIN items ON ia.itemID = items.itemID
        WHERE ia.parentItemID = ? AND ia.contentType = 'application/pdf'
    """, (item_id,))

    row = cursor.fetchone()
    if row:
        path, key = row
        if path and path.startswith("storage:"):
            filename = path.replace("storage:", "")
            full_path = ZOTERO_STORAGE / key / filename
            if full_path.exists():
                return str(full_path)
    return None


def get_item_fields(conn: sqlite3.Connection, item_id: int) -> dict[str, str]:
    """Get all metadata fields for an item as {fieldName: value}."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.fieldName, idv.value
        FROM itemData id
        JOIN fields f ON id.fieldID = f.fieldID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        WHERE id.itemID = ?
    """, (item_id,))
    return {row[0]: row[1] for row in cursor.fetchall()}


def get_item_collections(conn: sqlite3.Connection, item_id: int) -> list[tuple[int, str]]:
    """Get all collections an item belongs to. Returns [(collection_id, name), ...]."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.collectionID, c.collectionName
        FROM collections c
        JOIN collectionItems ci ON c.collectionID = ci.collectionID
        WHERE ci.itemID = ?
    """, (item_id,))
    return cursor.fetchall()
