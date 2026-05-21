#!/usr/bin/env python3
"""Tests for enrich_papers.py HTML extraction functions (P1-4).

Covers: extract_figure_url, extract_authors_html, extract_affiliations_html,
extract_section_headers, extract_captions, extract_method_summary,
extract_method_names, extract_has_real_world, strip_tags.

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_enrich_html.py
"""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENRICH_PY = REPO / "skills" / "daily-papers" / "enrich_papers.py"


def _import_enrich():
    spec = importlib.util.spec_from_file_location("enrich_papers", ENRICH_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── strip_tags ────────────────────────────────────────────────────────────


def test_strip_tags_basic():
    mod = _import_enrich()
    assert mod.strip_tags("<b>hello</b> <i>world</i>") == "hello world"
    assert mod.strip_tags("no tags here") == "no tags here"
    assert mod.strip_tags('<a href="x">link</a>') == "link"


# ── extract_figure_url ────────────────────────────────────────────────────


def test_figure_url_absolute():
    """Absolute URL is returned as-is."""
    mod = _import_enrich()
    html = '<figure><img src="https://example.com/fig1.png" /></figure>'
    assert mod.extract_figure_url(html, "2605.12345") == "https://example.com/fig1.png"


def test_figure_url_relative_slash():
    """Relative URL starting with / gets arxiv.org prefix."""
    mod = _import_enrich()
    html = '<figure><img src="/html/2605.12345/fig.png" /></figure>'
    assert mod.extract_figure_url(html, "2605.12345") == "https://arxiv.org/html/2605.12345/fig.png"


def test_figure_url_relative_bare():
    """Bare relative URL gets arxiv_id-based prefix."""
    mod = _import_enrich()
    html = '<figure><img src="extracted/fig1.png" /></figure>'
    url = mod.extract_figure_url(html, "2605.12345")
    assert url == "https://arxiv.org/html/2605.12345/extracted/fig1.png"


def test_figure_url_relative_with_version():
    """Relative URL with version prefix like 2605.12345v1/fig.png."""
    mod = _import_enrich()
    html = '<figure><img src="2605.12345v1/extracted/figures/fig1.png" /></figure>'
    url = mod.extract_figure_url(html, "2605.12345")
    assert url == "https://arxiv.org/html/2605.12345v1/extracted/figures/fig1.png"


def test_figure_url_skips_icons():
    """Icon/logo/badge images are skipped."""
    mod = _import_enrich()
    html = (
        '<figure><img src="https://example.com/orcid-icon.png" /></figure>'
        '<figure><img src="https://example.com/real-figure.png" /></figure>'
    )
    assert mod.extract_figure_url(html, "2605.12345") == "https://example.com/real-figure.png"


def test_figure_url_empty_when_no_figures():
    mod = _import_enrich()
    assert mod.extract_figure_url("<p>no figure here</p>", "2605.12345") == ""


# ── extract_authors_html ──────────────────────────────────────────────────


def test_authors_html_basic():
    mod = _import_enrich()
    html = '''
    <span class="ltx_personname">John Smith</span>
    <span class="ltx_personname">Jane <b>Doe</b></span>
    '''
    authors = mod.extract_authors_html(html)
    assert "John Smith" in authors
    assert "Jane Doe" in authors


def test_authors_html_skips_affiliations():
    """Names containing institution keywords are skipped."""
    mod = _import_enrich()
    html = '''
    <span class="ltx_personname">Alice Zhang</span>
    <span class="ltx_personname">Stanford University Department of CS</span>
    '''
    authors = mod.extract_authors_html(html)
    assert "Alice Zhang" in authors
    assert len(authors) == 1


def test_authors_html_empty():
    mod = _import_enrich()
    assert mod.extract_authors_html("<p>no authors here</p>") == []


# ── extract_affiliations_html ─────────────────────────────────────────────


def test_affiliations_html_structured():
    """Strategy 1: ltx_role_affil class."""
    mod = _import_enrich()
    html = '''
    <article>
    <span class="ltx_role_affil">Stanford University</span>
    <span class="ltx_role_affil">Google DeepMind</span>
    <div class="ltx_abstract">Abstract text here</div>
    </article>
    '''
    affils = mod.extract_affiliations_html(html)
    assert any("Stanford" in a for a in affils)
    assert any("Google" in a or "DeepMind" in a for a in affils)


def test_affiliations_html_header_region():
    """Strategy 2: institution keywords in header region plain text."""
    mod = _import_enrich()
    html = '''
    <article>
    <h1>Paper Title</h1>
    <p>Author Name</p>
    <p>Massachusetts Institute of Technology</p>
    <p>Tsinghua University</p>
    <div class="ltx_abstract">Abstract goes here</div>
    </article>
    '''
    affils = mod.extract_affiliations_html(html)
    assert any("Massachusetts" in a or "MIT" in a.upper() for a in affils)


def test_affiliations_html_empty():
    mod = _import_enrich()
    assert mod.extract_affiliations_html("<p>nothing</p>") == []


# ── extract_section_headers ───────────────────────────────────────────────


def test_section_headers_basic():
    mod = _import_enrich()
    html = '''
    <h2>1. Introduction</h2>
    <p>content</p>
    <h2>2. Method</h2>
    <p>content</p>
    <h3>2.1 Sub-approach</h3>
    '''
    headers = mod.extract_section_headers(html)
    assert "Introduction" in headers
    assert "Method" in headers
    assert "Sub-approach" in headers


def test_section_headers_strips_numbering():
    mod = _import_enrich()
    html = '<h2>3.2.1 Detailed Design</h2>'
    headers = mod.extract_section_headers(html)
    assert headers == ["Detailed Design"]


def test_section_headers_cap_25():
    mod = _import_enrich()
    html = "".join(f"<h2>{i}. Section {i}</h2>" for i in range(30))
    headers = mod.extract_section_headers(html)
    assert len(headers) <= 25


# ── extract_captions ──────────────────────────────────────────────────────


def test_captions_basic():
    mod = _import_enrich()
    html = '''
    <figcaption>Figure 1: Overview of the proposed framework and its components in detail.</figcaption>
    <caption>Table 1: Comparison results across multiple baseline methods and datasets.</caption>
    '''
    captions = mod.extract_captions(html)
    assert len(captions) == 2
    assert "Overview" in captions[0]


def test_captions_filters_short():
    """Captions shorter than 10 chars are skipped."""
    mod = _import_enrich()
    html = '<figcaption>Fig 1</figcaption><figcaption>Figure 1: A long enough caption for testing.</figcaption>'
    captions = mod.extract_captions(html)
    assert len(captions) == 1


def test_captions_cap_8():
    mod = _import_enrich()
    html = "".join(f"<figcaption>Figure {i}: A reasonably long caption text here.</figcaption>" for i in range(12))
    captions = mod.extract_captions(html)
    assert len(captions) <= 8


# ── extract_has_real_world ────────────────────────────────────────────────


def test_has_real_world_true():
    mod = _import_enrich()
    html = "<p>We deployed on a physical robot for real-world experiment validation.</p>"
    assert mod.extract_has_real_world(html) is True


def test_has_real_world_false():
    mod = _import_enrich()
    html = "<p>We evaluate on simulation benchmarks only.</p>"
    assert mod.extract_has_real_world(html) is False


# ── extract_method_names ──────────────────────────────────────────────────


def test_method_names_camelcase():
    mod = _import_enrich()
    html = "<p>We compare our approach with DreamerV3 and DreamerV3 and OpenVLA and OpenVLA in simulation.</p>"
    names = mod.extract_method_names(html, "Our Novel Method")
    assert "DreamerV3" in names or "OpenVLA" in names


def test_method_names_filters_stop_words():
    """Section heading names like 'Method' are in stop set."""
    mod = _import_enrich()
    html = "<p>Method Method Method Method Abstract Abstract Abstract Abstract</p>"
    names = mod.extract_method_names(html, "Test Paper")
    assert "Method" not in names
    assert "Abstract" not in names


def test_method_names_filters_title_words():
    """Words from the paper title are excluded."""
    mod = _import_enrich()
    html = "<p>FlowNet FlowNet FlowNet ControlNet ControlNet ControlNet</p>"
    names = mod.extract_method_names(html, "FlowNet: A New Approach")
    assert "FlowNet" not in names
    assert "ControlNet" in names


# ── extract_method_summary ────────────────────────────────────────────────


def test_method_summary_from_method_section():
    mod = _import_enrich()
    long_text = "We propose a novel approach that combines diffusion models with reinforcement learning. " * 10
    html = f'<h2>3. Method</h2><p>{long_text}</p><h2>4. Experiments</h2>'
    summary = mod.extract_method_summary(html)
    assert len(summary) >= 100
    assert len(summary) <= 560
    assert "diffusion" in summary


def test_method_summary_fallback_to_introduction():
    mod = _import_enrich()
    long_text = "Our key contribution is a unified framework for audio generation that leverages pretrained models. " * 8
    html = f'<h2>1. Introduction</h2><p>{long_text}</p><h2>2. Related Work</h2>'
    summary = mod.extract_method_summary(html)
    assert len(summary) >= 100


def test_method_summary_empty_when_too_short():
    mod = _import_enrich()
    html = '<h2>Method</h2><p>Short.</p><h2>Results</h2>'
    summary = mod.extract_method_summary(html)
    assert summary == ""


def test_method_summary_strips_citations():
    mod = _import_enrich()
    long_text = "We build on prior work [1] and extend [2,3] the framework significantly for better results. " * 8
    html = f'<h2>Method</h2><p>{long_text}</p><h2>Experiments</h2>'
    summary = mod.extract_method_summary(html)
    assert "[1]" not in summary
    assert "[2,3]" not in summary


# ── Runner ────────────────────────────────────────────────────────────────

TESTS = [
    test_strip_tags_basic,
    test_figure_url_absolute,
    test_figure_url_relative_slash,
    test_figure_url_relative_bare,
    test_figure_url_relative_with_version,
    test_figure_url_skips_icons,
    test_figure_url_empty_when_no_figures,
    test_authors_html_basic,
    test_authors_html_skips_affiliations,
    test_authors_html_empty,
    test_affiliations_html_structured,
    test_affiliations_html_header_region,
    test_affiliations_html_empty,
    test_section_headers_basic,
    test_section_headers_strips_numbering,
    test_section_headers_cap_25,
    test_captions_basic,
    test_captions_filters_short,
    test_captions_cap_8,
    test_has_real_world_true,
    test_has_real_world_false,
    test_method_names_camelcase,
    test_method_names_filters_stop_words,
    test_method_names_filters_title_words,
    test_method_summary_from_method_section,
    test_method_summary_fallback_to_introduction,
    test_method_summary_empty_when_too_short,
    test_method_summary_strips_citations,
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
