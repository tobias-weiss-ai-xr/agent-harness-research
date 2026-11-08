"""Unit tests for scripts/generate_readme.py.

Verifies paper-list document generation logic on synthetic corpus data.
Hermetic.
"""

from pathlib import Path

import pytest
import yaml

import research_config
import generate_readme as gen


@pytest.fixture
def sample_papers():
    """Small synthetic corpus for testing."""
    return [
        {
            "title": "Testing Framework Design",
            "date": "2026-01",
            "url": "https://arxiv.org/abs/2601.00001",
            "category": "testing",
            "subcategory": "frameworks",
            "authors": ["Alice Tester"],
            "abstract": "A framework for testing.",
            "venue": "arXiv",
        },
        {
            "title": "Property-Based Testing with Hypothesis",
            "date": "2025-12",
            "url": "https://arxiv.org/abs/2512.00002",
            "category": "testing",
            "subcategory": "methodology",
            "authors": ["Bob Tester"],
            "abstract": "Using property-based testing.",
            "venue": "arXiv",
        },
    ]


@pytest.fixture
def sample_cfg():
    """Minimal config for testing."""
    return {
        "topic": {"name": "Test Corpus", "short": "test"},
        "taxonomy": {
            "categories": [
                {"id": "testing", "display": "Testing"},
            ],
            "subcategories": [
                {"id": "frameworks", "display": "Frameworks"},
                {"id": "methodology", "display": "Methodology"},
            ],
        },
    }


def test_generate_json_creates_file(tmp_path, sample_papers):
    """Verify JSON generation writes valid file."""
    json_path = tmp_path / "papers.json"
    gen.generate_json(sample_papers, json_path)

    assert json_path.exists()
    import json
    data = json.loads(json_path.read_text())
    assert "papers" in data
    assert len(data["papers"]) == 2
    assert data["papers"][0]["title"] == "Testing Framework Design"


def test_generate_json_creates_parent_dirs(tmp_path, sample_papers):
    """Verify JSON generation creates missing parent directories."""
    json_path = tmp_path / "nested" / "dirs" / "papers.json"
    gen.generate_json(sample_papers, json_path)

    assert json_path.exists()


def test_generate_paper_list_creates_file(tmp_path, sample_papers, sample_cfg):
    """Verify paper-list document is created with paper content."""
    readme_path = tmp_path / "README.md"
    paper_list_path = tmp_path / "docs" / "paper_list.md"
    readme_path.write_text("# Test Corpus\n\n", encoding="utf-8")

    gen.generate_readme(sample_papers, readme_path, sample_cfg, check_mode=False,
                        paper_list_path=paper_list_path)

    assert paper_list_path.exists()
    content = paper_list_path.read_text(encoding="utf-8")
    assert "Testing Framework Design" in content
    assert "Property-Based Testing with Hypothesis" in content


def test_generate_paper_list_creates_parent_dirs(tmp_path, sample_papers, sample_cfg):
    """Verify paper-list generation creates missing parent directories."""
    readme_path = tmp_path / "README.md"
    paper_list_path = tmp_path / "nested" / "dirs" / "paper_list.md"
    readme_path.write_text("# Test Corpus\n\n", encoding="utf-8")

    gen.generate_readme(sample_papers, readme_path, sample_cfg, check_mode=False,
                        paper_list_path=paper_list_path)

    assert paper_list_path.exists()


def test_generate_readme_removes_paper_list_markers(tmp_path, sample_papers, sample_cfg):
    """Verify paper-list markers are removed from README (migration)."""
    readme_path = tmp_path / "README.md"
    paper_list_path = tmp_path / "docs" / "paper_list.md"
    readme_text = f"""# Test Corpus

{gen.readme_sections.PAPERLIST_START}
Old content that should be replaced.
{gen.readme_sections.PAPERLIST_END}

Some footer text.
"""
    readme_path.write_text(readme_text, encoding="utf-8")

    gen.generate_readme(sample_papers, readme_path, sample_cfg, check_mode=False,
                        paper_list_path=paper_list_path)

    result = readme_path.read_text(encoding="utf-8")
    assert "PAPER LIST" not in result
    assert "Old content that should be replaced" not in result
    assert "Some footer text" in result


def test_generate_readme_no_markers_leaves_readme_unchanged(tmp_path, sample_papers, sample_cfg):
    """Verify README without paper-list markers is not modified."""
    readme_path = tmp_path / "README.md"
    paper_list_path = tmp_path / "docs" / "paper_list.md"
    readme_text = "# Test Corpus\n\nNo paper list here.\n"
    readme_path.write_text(readme_text, encoding="utf-8")

    gen.generate_readme(sample_papers, readme_path, sample_cfg, check_mode=False,
                        paper_list_path=paper_list_path)

    result = readme_path.read_text(encoding="utf-8")
    assert result == readme_text


def test_generate_readme_check_mode_updated(tmp_path, sample_papers, sample_cfg):
    """Verify check mode exits 1 when paper list is out of date."""
    readme_path = tmp_path / "README.md"
    paper_list_path = tmp_path / "docs" / "paper_list.md"
    readme_path.write_text("# Test Corpus\n\n", encoding="utf-8")
    paper_list_path.parent.mkdir(parents=True, exist_ok=True)
    paper_list_path.write_text("Old content.\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        gen.generate_readme(sample_papers, readme_path, sample_cfg, check_mode=True,
                            paper_list_path=paper_list_path)

    assert exc_info.value.code == 1


def test_generate_readme_check_mode_missing_file(tmp_path, sample_papers, sample_cfg):
    """Verify check mode exits 1 when paper list file is missing."""
    readme_path = tmp_path / "README.md"
    paper_list_path = tmp_path / "docs" / "paper_list.md"
    readme_path.write_text("# Test Corpus\n\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        gen.generate_readme(sample_papers, readme_path, sample_cfg, check_mode=True,
                            paper_list_path=paper_list_path)

    assert exc_info.value.code == 1


def test_generate_readme_check_mode_current(tmp_path, sample_papers, sample_cfg):
    """Verify check mode exits 0 when paper list is current."""
    readme_path = tmp_path / "README.md"
    paper_list_path = tmp_path / "docs" / "paper_list.md"
    readme_path.write_text("# Test Corpus\n\n", encoding="utf-8")

    # First, generate the paper list to make it current
    gen.generate_readme(sample_papers, readme_path, sample_cfg, check_mode=False,
                        paper_list_path=paper_list_path)

    # Now check should pass
    try:
        gen.generate_readme(sample_papers, readme_path, sample_cfg, check_mode=True,
                            paper_list_path=paper_list_path)
    except SystemExit as e:
        assert e.code == 0
