#!/usr/bin/env python3
"""One-command bootstrap: give a forked skeleton its own identity.

Run AFTER editing config/taxonomy.yaml (topic.name / short / description):

    python3 tools/bootstrap.py        # or: make bootstrap

Reads the topic block from config/taxonomy.yaml and rewrites the template's
identity tokens (README heading, docs/index.html <title>, CITATION.cff, repo
links) so the repo stops calling itself the skeleton.

Refuses while placeholder values remain (topic.name/short/description), and
is idempotent — safe to re-run any time.

No commits, no prompts, no network. Review the diff, then:
    make validate && make check && make test
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import research_config

REPO = Path(__file__).resolve().parent.parent

# (needle, replacement) applied as plain substring swaps; replacements are
# computed from the taxonomy topic block. Unknown-in-template = already patched.
PLACEHOLDER_NAMES = (
    "TODO Topic Best Practices",
    "Your Research Topic",
    "Research Corpus Skeleton",
    "Research Corpus",
)
PLACEHOLDER_SHORTS = ("todo", "your-topic", "research")


def _placeholders_topic(cfg):
    topic = research_config.get_topic(cfg)
    name = (topic.get("name") or "").strip()
    short = (topic.get("short") or "").strip()
    desc = (topic.get("description") or "").strip()
    bad = []
    if not name or name in PLACEHOLDER_NAMES or name.startswith("TODO"):
        bad.append("topic.name")
    if not short or short in PLACEHOLDER_SHORTS:
        bad.append("topic.short")
    if not desc or desc.startswith("TODO"):
        bad.append("topic.description")
    return bad


def _repo_suffix():
    """best-practices vs research, sniffed from the surrounding prose."""
    cit = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    if "Best Practices" in cit:
        return "best-practices"
    return "research"


def main():
    cfg = research_config.load_config()
    topic = research_config.get_topic(cfg)
    name = (topic.get("name") or "").strip()
    short = (topic.get("short") or "").strip()
    suffix = _repo_suffix()
    slug = f"{short}-{suffix}" if short else ""

    problems = _placeholders_topic(cfg)
    if problems:
        print("Bootstrap refused — config/taxonomy.yaml still has placeholders:")
        for p in problems:
            print(f"  - {p}")
        print("Set topic.name / short / description first, then re-run.")
        sys.exit(1)

    swaps = [
        ("README.md", [
            ("# skeleton-best-practices", f"# {name}"),
            ("<strong>Research Corpus Skeleton</strong>", f"<strong>{name}</strong>"),
            ("github.com/tobias-weiss-ai-xr/skeleton-research",
             f"github.com/<YOUR_ORG>/{slug}"),
            ("github.com/tobias-weiss-ai-xr/skeleton-best-practices",
             f"github.com/<YOUR_ORG>/{slug}"),
        ]),
        ("docs/index.html", [
            ("<title>Research Corpus — Paper Browser</title>",
             f"<title>{name} — Paper Browser</title>"),
        ]),
        ("CITATION.cff", [
            ('title: "Research Corpus Skeleton — Data-Driven Agentic Literature Review"',
             f'title: "{name} — Data-Driven Agentic Literature Review"'),
            ('title: "<Topic> Best Practices — Curated Reference Corpus"',
             f'title: "{name} — Curated Reference Corpus"'),
            ("<YOUR_ORG>/skeleton-research", f"<YOUR_ORG>/{slug}"),
            ("<YOUR_ORG>/<topic>-best-practices", f"<YOUR_ORG>/{slug}"),
        ]),
    ]

    changed = []
    for rel, pairs in swaps:
        path = REPO / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        for old, new in pairs:
            text = text.replace(old, new)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            changed.append(rel)

    if not changed:
        print("Nothing to do — identity tokens already set for this repo.")
        return

    print(f"Bootstrapped repo identity from taxonomy: {name!r} (slug: {slug})")
    for rel in changed:
        print(f"  updated {rel}")
    print("\nNext: review the diff, then `make validate && make check && make test`.")


if __name__ == "__main__":
    main()