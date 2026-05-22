#!/usr/bin/env python3
"""
Zotero 数据库查询辅助脚本（CLI 工具）
用于 paper-reader skill 的 Zotero 集成
"""

import sqlite3
import argparse
import sys
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

import zotero_db as _zotero
from user_config import zotero_db_path

ZOTERO_DB = zotero_db_path()


def copy_db():
    """复制数据库以避免锁定"""
    return _zotero.copy_readonly()


def list_collections(conn):
    """列出所有分类"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.collectionID, c.collectionName, c.parentCollectionID,
               COUNT(ci.itemID) as item_count
        FROM collections c
        LEFT JOIN collectionItems ci ON c.collectionID = ci.collectionID
        GROUP BY c.collectionID
        ORDER BY c.parentCollectionID NULLS FIRST, c.collectionName
    """)

    print("ID\t| 分类名称\t\t\t| 父分类\t| 文献数")
    print("-" * 70)
    for row in cursor.fetchall():
        parent = str(row[2]) if row[2] else "根目录"
        name = row[1][:24] if row[1] else ""
        print(f"{row[0]}\t| {name:24}\t| {parent:8}\t| {row[3]}")


def list_papers_in_collection(conn, collection_id, recursive=False):
    """列出分类下的论文（支持递归子分类）"""
    cursor = conn.cursor()

    if recursive:
        collection_ids = _zotero.get_all_child_collections(conn, collection_id)
        placeholders = ','.join('?' * len(collection_ids))
        query = f"""
            SELECT DISTINCT i.itemID, idv.value as title,
                   (SELECT value FROM itemData id2
                    JOIN itemDataValues idv2 ON id2.valueID = idv2.valueID
                    JOIN fields f2 ON id2.fieldID = f2.fieldID
                    WHERE id2.itemID = i.itemID AND f2.fieldName = 'date' LIMIT 1) as date
            FROM items i
            JOIN collectionItems ci ON i.itemID = ci.itemID
            JOIN itemData id ON i.itemID = id.itemID
            JOIN itemDataValues idv ON id.valueID = idv.valueID
            JOIN fields f ON id.fieldID = f.fieldID
            WHERE ci.collectionID IN ({placeholders})
              AND f.fieldName = 'title'
              AND i.itemTypeID != 14
            ORDER BY date DESC
        """
        cursor.execute(query, collection_ids)
        print(f"(递归查询，包含 {len(collection_ids)} 个分类)")
    else:
        cursor.execute("""
            SELECT i.itemID, idv.value as title,
                   (SELECT value FROM itemData id2
                    JOIN itemDataValues idv2 ON id2.valueID = idv2.valueID
                    JOIN fields f2 ON id2.fieldID = f2.fieldID
                    WHERE id2.itemID = i.itemID AND f2.fieldName = 'date' LIMIT 1) as date
            FROM items i
            JOIN collectionItems ci ON i.itemID = ci.itemID
            JOIN itemData id ON i.itemID = id.itemID
            JOIN itemDataValues idv ON id.valueID = idv.valueID
            JOIN fields f ON id.fieldID = f.fieldID
            WHERE ci.collectionID = ?
              AND f.fieldName = 'title'
              AND i.itemTypeID != 14
            ORDER BY date DESC
        """, (collection_id,))

    print("ItemID\t| 日期\t\t| 标题")
    print("-" * 80)
    for row in cursor.fetchall():
        title = row[1][:50] if row[1] else ""
        date = row[2][:10] if row[2] else "N/A"
        print(f"{row[0]}\t| {date}\t| {title}")


def search_paper(conn, keyword):
    """搜索论文标题"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.itemID, idv.value as title,
               (SELECT value FROM itemData id2
                JOIN itemDataValues idv2 ON id2.valueID = idv2.valueID
                JOIN fields f2 ON id2.fieldID = f2.fieldID
                WHERE id2.itemID = i.itemID AND f2.fieldName = 'date' LIMIT 1) as date
        FROM items i
        JOIN itemData id ON i.itemID = id.itemID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        JOIN fields f ON id.fieldID = f.fieldID
        WHERE f.fieldName = 'title'
          AND i.itemTypeID != 14
          AND idv.value LIKE ?
        ORDER BY date DESC
        LIMIT 20
    """, (f"%{keyword}%",))

    print(f"搜索: '{keyword}'")
    print("ItemID\t| 日期\t\t| 标题")
    print("-" * 80)
    for row in cursor.fetchall():
        title = row[1][:50] if row[1] else ""
        date = row[2][:10] if row[2] else "N/A"
        print(f"{row[0]}\t| {date}\t| {title}")


def get_pdf_path(conn, item_id):
    """获取论文 PDF 路径（带 CLI 输出）"""
    pdf_path = _zotero.get_pdf_path(conn, item_id)
    if pdf_path:
        fields = _zotero.get_item_fields(conn, item_id)
        print(f"标题: {fields.get('title', 'Unknown')}")
        print(f"PDF路径: {pdf_path}")
        print(f"文件存在: Yes")
    else:
        print(f"未找到 itemID={item_id} 的 PDF 附件")
    return pdf_path


def get_collection_path(conn, collection_id):
    """获取分类的完整路径"""
    return _zotero.get_collection_path(conn, collection_id)


def get_item_collections(conn, item_id):
    """获取论文所在的所有分类"""
    return _zotero.get_item_collections(conn, item_id)


def add_to_collection_db(item_id, collection_id):
    """将论文添加到分类（需要直接操作原数据库）"""
    # 注意：这会直接修改 Zotero 数据库，需谨慎
    conn = sqlite3.connect(ZOTERO_DB)
    cursor = conn.cursor()
    try:
        # 检查是否已存在
        cursor.execute("""
            SELECT 1 FROM collectionItems
            WHERE collectionID = ? AND itemID = ?
        """, (collection_id, item_id))
        if cursor.fetchone():
            print(f"论文 {item_id} 已在分类 {collection_id} 中")
            return False

        # 添加到分类
        cursor.execute("""
            INSERT INTO collectionItems (collectionID, itemID, orderIndex)
            VALUES (?, ?, 0)
        """, (collection_id, item_id))
        conn.commit()
        print(f"已将论文 {item_id} 添加到分类 {collection_id}")
        return True
    except Exception as e:
        print(f"添加失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def remove_from_collection_db(item_id, collection_id):
    """从分类中移除论文"""
    conn = sqlite3.connect(ZOTERO_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM collectionItems
            WHERE collectionID = ? AND itemID = ?
        """, (collection_id, item_id))
        if cursor.rowcount > 0:
            conn.commit()
            print(f"已从分类 {collection_id} 移除论文 {item_id}")
            return True
        else:
            print(f"论文 {item_id} 不在分类 {collection_id} 中")
            return False
    except Exception as e:
        print(f"移除失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def move_to_collection(item_id, new_collection_id, old_collection_id=None):
    """移动论文到新分类（先添加到新分类，再从旧分类移除）"""
    # 先添加到新分类
    add_to_collection_db(item_id, new_collection_id)

    # 如果指定了旧分类，从旧分类移除
    if old_collection_id:
        remove_from_collection_db(item_id, old_collection_id)


def find_collection_by_name(conn, name):
    """根据名称查找分类（模糊匹配，显示所有结果）"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT collectionID, collectionName, parentCollectionID
        FROM collections
        WHERE collectionName LIKE ?
    """, (f"%{name}%",))
    results = cursor.fetchall()
    for r in results:
        path = _zotero.get_collection_path(conn, r[0])
        print(f"ID: {r[0]}, 路径: {path}")
    return results


def get_paper_info(conn, item_id):
    """获取论文详细信息"""
    fields = _zotero.get_item_fields(conn, item_id)
    title = fields.get("title", "Unknown")
    collections = _zotero.get_item_collections(conn, item_id)
    collection_paths = [_zotero.get_collection_path(conn, c[0]) for c in collections]

    print(f"ItemID: {item_id}")
    print(f"标题: {title}")
    print(f"日期: {fields.get('date', 'N/A')}")
    print(f"URL: {fields.get('url', 'N/A')}")
    print(f"所在分类: {', '.join(collection_paths) if collection_paths else '无'}")

    return {
        'item_id': item_id,
        'title': title,
        'fields': fields,
        'collections': collections,
        'collection_paths': collection_paths
    }


def main():
    parser = argparse.ArgumentParser(description='Zotero 数据库查询工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # 列出分类
    subparsers.add_parser('collections', help='列出所有分类')

    # 列出分类下的论文
    papers_parser = subparsers.add_parser('papers', help='列出分类下的论文')
    papers_parser.add_argument('collection_id', type=int, help='分类ID')
    papers_parser.add_argument('--recursive', '-r', action='store_true', help='递归包含子分类')

    # 搜索论文
    search_parser = subparsers.add_parser('search', help='搜索论文')
    search_parser.add_argument('keyword', help='搜索关键词')

    # 获取 PDF 路径
    pdf_parser = subparsers.add_parser('pdf', help='获取 PDF 路径')
    pdf_parser.add_argument('item_id', type=int, help='论文 ItemID')

    # 获取论文信息
    info_parser = subparsers.add_parser('info', help='获取论文详细信息')
    info_parser.add_argument('item_id', type=int, help='论文 ItemID')

    # 查找分类
    find_parser = subparsers.add_parser('find-collection', help='根据名称查找分类')
    find_parser.add_argument('name', help='分类名称（支持模糊匹配）')

    # 添加到分类
    add_parser = subparsers.add_parser('add-to-collection', help='将论文添加到分类')
    add_parser.add_argument('item_id', type=int, help='论文 ItemID')
    add_parser.add_argument('collection_id', type=int, help='目标分类ID')

    # 从分类移除
    remove_parser = subparsers.add_parser('remove-from-collection', help='从分类移除论文')
    remove_parser.add_argument('item_id', type=int, help='论文 ItemID')
    remove_parser.add_argument('collection_id', type=int, help='分类ID')

    # 移动到新分类
    move_parser = subparsers.add_parser('move', help='移动论文到新分类')
    move_parser.add_argument('item_id', type=int, help='论文 ItemID')
    move_parser.add_argument('new_collection_id', type=int, help='新分类ID')
    move_parser.add_argument('--from', dest='old_collection_id', type=int, help='旧分类ID（可选）')

    args = parser.parse_args()

    if not ZOTERO_DB.exists():
        print(f"Zotero 数据库不存在: {ZOTERO_DB}")
        return

    conn = copy_db()

    try:
        if args.command == 'collections':
            list_collections(conn)
        elif args.command == 'papers':
            list_papers_in_collection(conn, args.collection_id, recursive=args.recursive)
        elif args.command == 'search':
            search_paper(conn, args.keyword)
        elif args.command == 'pdf':
            get_pdf_path(conn, args.item_id)
        elif args.command == 'info':
            get_paper_info(conn, args.item_id)
        elif args.command == 'find-collection':
            find_collection_by_name(conn, args.name)
        elif args.command == 'add-to-collection':
            add_to_collection_db(args.item_id, args.collection_id)
        elif args.command == 'remove-from-collection':
            remove_from_collection_db(args.item_id, args.collection_id)
        elif args.command == 'move':
            move_to_collection(args.item_id, args.new_collection_id, args.old_collection_id)
        else:
            parser.print_help()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
