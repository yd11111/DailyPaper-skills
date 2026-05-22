#!/usr/bin/env python3

import copy
import json
import sys
from functools import lru_cache
from pathlib import Path


def get_temp_dir() -> Path:
    """Get platform-appropriate temp directory for daily papers data.

    On Windows: ~/tmp/ (e.g., C:/Users/username/tmp/)
    On Linux/Mac: /tmp/
    """
    if sys.platform == 'win32':
        # Windows: use user's home directory under ~/tmp
        tmp_dir = Path.home() / 'tmp'
    else:
        # Linux/Mac: use /tmp
        tmp_dir = Path('/tmp')

    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


DEFAULT_CONFIG = {
    "paths": {
        "obsidian_vault": "~/ObsidianVault",
        "paper_notes_folder": "论文笔记",
        "daily_papers_folder": "DailyPapers",
        "concepts_folder": "_概念",
        "highlights_folder": "_创新亮点",
        "compare_folder": "_对比报告",
        "zotero_db": "~/Zotero/zotero.sqlite",
        "zotero_storage": "~/Zotero/storage",
    },
    "daily_papers": {
        # Keyword/category lists intentionally EMPTY in defaults.
        # The active values must come from user-config.json.
        # If user-config.json is missing or its daily_papers section is empty,
        # fetch_and_score.py will produce zero matches — a loud, easily noticed
        # failure mode. Prior to spec #2 cleanup these defaults were left over
        # from a robotics-focused fork; if user-config.json ever got corrupted
        # the pipeline would silently run with anti-user preferences (negative
        # keywords included "text-to-speech" etc.). See audit P1-7.
        "keywords": [],
        "negative_keywords": [],
        "domain_boost_keywords": [],
        "arxiv_categories": [],
        "min_score": 2,
        "top_n": 30,
        "max_age_days": 7,
    },
    "timeouts": {
        "curl_html": 30,
        "curl_image": 10,
        "pdf_extract": 30,
        "arxiv_fetch": 30,
    },
    "automation": {
        "auto_refresh_indexes": True,
        "git_commit": False,
        "git_push": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@lru_cache(maxsize=1)
def load_user_config() -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_dir = Path(__file__).resolve().parent

    for filename in ("user-config.json", "user-config.local.json"):
        config_path = config_dir / filename
        if not config_path.exists():
            continue
        with config_path.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            _deep_merge(config, loaded)

    return config


def _expand(path_value: str) -> Path:
    return Path(path_value).expanduser()


def paths_config() -> dict:
    return load_user_config()["paths"]


def daily_papers_config() -> dict:
    return load_user_config()["daily_papers"]


def automation_config() -> dict:
    config = load_user_config()["automation"]
    if config.get("git_push") and not config.get("git_commit"):
        config = copy.deepcopy(config)
        config["git_push"] = False
    return config


def obsidian_vault_path() -> Path:
    return _expand(paths_config()["obsidian_vault"])


def paper_notes_dir() -> Path:
    return obsidian_vault_path() / paths_config()["paper_notes_folder"]


def daily_papers_dir() -> Path:
    return obsidian_vault_path() / paths_config()["daily_papers_folder"]


def concepts_dir() -> Path:
    return paper_notes_dir() / paths_config()["concepts_folder"]


def highlights_dir() -> Path:
    return paper_notes_dir() / paths_config()["highlights_folder"]


def compare_dir() -> Path:
    return paper_notes_dir() / paths_config()["compare_folder"]


def max_age_days() -> int:
    return int(daily_papers_config().get("max_age_days", 7))


def timeouts_config() -> dict:
    return load_user_config().get("timeouts", {})


def zotero_db_path() -> Path:
    return _expand(paths_config()["zotero_db"])


def zotero_storage_dir() -> Path:
    return _expand(paths_config()["zotero_storage"])


def auto_refresh_indexes_enabled() -> bool:
    return bool(automation_config()["auto_refresh_indexes"])


def git_commit_enabled() -> bool:
    return bool(automation_config()["git_commit"])


def git_push_enabled() -> bool:
    return bool(automation_config()["git_push"])


# ── Temp directory for intermediate data (Windows/Linux compatible) ──────────

def temp_dir() -> Path:
    """Get platform-appropriate temp directory.

    Windows: ~/tmp/
    Linux/Mac: /tmp/
    """
    return get_temp_dir()


def temp_file_path(filename: str) -> Path:
    """Get full path for a temp file.

    Usage:
        top30_path = temp_file_path('daily_papers_top30.json')
        enriched_path = temp_file_path('daily_papers_enriched.json')
    """
    return temp_dir() / filename
