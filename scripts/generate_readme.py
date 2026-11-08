#!/usr/bin/env python3
"""Generate the paper list document (docs/paper_list.md) and docs/papers.json
from papers.yaml.

The paper list is written to a dedicated document (``docs/paper_list.md``)
rather than embedded in README.md; the README only links to it.  This keeps
the README readable and lets the paper list grow without bloating it.

Generic for any *-research corpus: categories/subcategories and their display
names come from config/taxonomy.yaml (via research_config).

Usage:
    python3 scripts/generate_readme.py
    python3 scripts/generate_readme.py --check   # CI: fail if out of date
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

import readme_sections
import research_config


def generate_readme(papers, readme_path, cfg, check_mode=False,
                    paper_list_path=None):
    """Generate the paper list document.

    Args:
        papers: list of paper dicts.
        readme_path: path to README.md (paper-list section is removed if present).
        cfg: research config.
        check_mode: if True, exit 0 when up-to-date, 1 otherwise.
        paper_list_path: where to write the paper list (default: docs/paper_list.md
            next to README.md).
    """
    readme_path = Path(readme_path)
    if paper_list_path is None:
        paper_list_path = readme_path.parent / "docs" / "paper_list.md"
    paper_list_path = Path(paper_list_path)

    content = readme_sections.render_paper_list(papers, cfg)

    if check_mode:
        if not paper_list_path.exists():
            print("Paper list file missing. Run generate_readme.py to update.",
                  file=sys.stderr)
            sys.exit(1)
        if paper_list_path.read_text(encoding="utf-8") != content:
            print("Paper list is out-of-date. Run generate_readme.py to update.",
                  file=sys.stderr)
            sys.exit(1)
        print("Paper list is up-to-date.")
        sys.exit(0)

    paper_list_path.parent.mkdir(parents=True, exist_ok=True)
    paper_list_path.write_text(content, encoding="utf-8")
    print(f"Generated {paper_list_path}")

    # Remove paper-list section from README if present (migration from the
    # old layout where the paper list lived inline in README.md).
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        si, ei = readme_sections.find_section(
            readme_text, readme_sections.PAPERLIST_START,
            readme_sections.PAPERLIST_END)
        if si is not None:
            new_text = readme_text[:si] + readme_text[ei:]
            new_text = re.sub(r"\n{3,}", "\n\n", new_text)
            readme_path.write_text(new_text, encoding="utf-8")
            print("Removed paper list section from README.md")


def generate_json(papers, json_path):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps({"papers": papers}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Generated {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate paper_list.md and papers.json from papers.yaml"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if paper_list.md is up-to-date (exit 1 if not)",
    )
    parser.add_argument(
        "--skip-json", action="store_true", help="Skip generating papers.json"
    )
    args = parser.parse_args()

    base = Path(__file__).parent.parent
    papers_yaml = base / "papers.yaml"
    readme_path = base / "README.md"
    json_path = base / "docs" / "papers.json"
    paper_list_path = base / "docs" / "paper_list.md"

    papers = research_config.load_papers(papers_yaml)
    cfg = research_config.require_valid_config()

    generate_readme(papers, readme_path, cfg, check_mode=args.check,
                    paper_list_path=paper_list_path)

    if not args.check and not args.skip_json:
        generate_json(papers, json_path)


if __name__ == "__main__":
    main()
