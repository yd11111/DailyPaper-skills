#!/usr/bin/env python3
"""Static tests verifying HF Trending has been removed from daily pipeline.

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py

Exits 0 if all assertions pass, 1 otherwise. Each test prints PASS/FAIL.
Tests are pure static analysis + import-time checks — no network, no
side effects on vault.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

SKILLS = Path.home() / ".claude" / "skills"
FETCH_PY = SKILLS / "daily-papers" / "fetch_and_score.py"
USER_CFG = SKILLS / "_shared" / "user-config.json"
FETCH_SKILL = SKILLS / "daily-papers-fetch" / "SKILL.md"
REVIEW_SKILL = SKILLS / "daily-papers-review" / "SKILL.md"


def _import_fetch_module():
    """Import fetch_and_score.py as a module without executing main()."""
    spec = importlib.util.spec_from_file_location("fetch_and_score", FETCH_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_score_paper_no_is_trending_kwarg():
    """score_paper must NOT accept an is_trending keyword argument."""
    mod = _import_fetch_module()
    paper = {"title": "test", "abstract": "test"}
    try:
        mod.score_paper(paper, is_trending=True)
    except TypeError:
        return
    raise AssertionError("score_paper still accepts is_trending kwarg")


def test_no_trending_exemption_constant():
    """Module must not define TRENDING_AGE_EXEMPTION_UPVOTES."""
    mod = _import_fetch_module()
    assert not hasattr(mod, "TRENDING_AGE_EXEMPTION_UPVOTES"), (
        "TRENDING_AGE_EXEMPTION_UPVOTES still defined in fetch_and_score.py"
    )


def test_user_config_no_trending_field():
    """user-config.json must not contain trending_age_exemption_upvotes."""
    cfg = json.loads(USER_CFG.read_text())
    daily = cfg.get("daily_papers", {})
    assert "trending_age_exemption_upvotes" not in daily, (
        "trending_age_exemption_upvotes still present in user-config.json"
    )


def test_fetch_py_no_trending_string():
    """fetch_and_score.py code (excluding comments) must not contain 'trending'."""
    text = FETCH_PY.read_text()
    code_lines = [
        ln for ln in text.splitlines()
        if not ln.lstrip().startswith("#") and not ln.lstrip().startswith('"""')
    ]
    code_text = "\n".join(code_lines)
    matches = re.findall(r"(?i)trending", code_text)
    assert not matches, (
        f"fetch_and_score.py code still contains {len(matches)} 'trending' "
        f"refs (case-insensitive)"
    )


def test_fetch_skill_no_trending_string():
    """daily-papers-fetch/SKILL.md must not contain 'trending'."""
    text = FETCH_SKILL.read_text()
    matches = re.findall(r"(?i)trending", text)
    assert not matches, (
        f"daily-papers-fetch/SKILL.md still contains {len(matches)} 'trending' refs"
    )


def test_review_skill_no_trending_string():
    """daily-papers-review/SKILL.md must not contain 'trending'."""
    text = REVIEW_SKILL.read_text()
    matches = re.findall(r"(?i)trending", text)
    assert not matches, (
        f"daily-papers-review/SKILL.md still contains {len(matches)} 'trending' refs"
    )


def test_review_skill_no_age_exempted_string():
    """daily-papers-review/SKILL.md must not reference age_exempted."""
    text = REVIEW_SKILL.read_text()
    matches = re.findall(r"age_exempted", text)
    assert not matches, (
        f"daily-papers-review/SKILL.md still contains {len(matches)} 'age_exempted' refs"
    )


TESTS = [
    test_score_paper_no_is_trending_kwarg,
    test_no_trending_exemption_constant,
    test_user_config_no_trending_field,
    test_fetch_py_no_trending_string,
    test_fetch_skill_no_trending_string,
    test_review_skill_no_trending_string,
    test_review_skill_no_age_exempted_string,
]


def main():
    failed = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{len(TESTS) - failed} / {len(TESTS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
