# Paper Ingestion Workflows: Building a Scalable Research Knowledge Base

**Tobias Weiss**  
**Research Infrastructure Paper**  
**v1.0 — October 11, 2026**  
**DOI: [10.5281/zenodo.23302654](https://doi.org/10.5281/zenodo.23302654)**  
**Published on [Zenodo](https://zenodo.org/record/23302654)**

---

## Abstract

This paper describes the architecture and implementation of a distributed paper ingestion 
workflow that powers a knowledge base of 20,455+ research papers across marketing, AI, 
and contextual intelligence domains. The workflow automates paper discovery from 27 
research repositories, full-text fetching from DOI and open-access sources, and 
intelligent organization into searchable, topic-based collections. We present the 
design decisions, technical implementation, and lessons learned from building a 
scalable research infrastructure that combines automation with human curation.

**Keywords**: Research infrastructure, paper ingestion, knowledge base, automated 
literature review, distributed fetching, full-text extraction

---

## 1. Introduction

Research teams increasingly struggle with **information overload** — the volume of 
academic and industry papers grows exponentially, while the time available to 
review them remains constant. Manual literature reviews are:

- **Time-consuming**: Estimated 5-10 hours per relevant paper including reading and notes
- **Incomplete**: Impossible to track all relevant publications across sources
- **Outdated**: Static collections quickly become stale
- **Isolated**: Knowledge remains siloed in individual researchers' notes

Our **Paper Ingestion Workflow** solves these problems by automating:

1. **Discovery**: Finding relevant papers from arXiv, CrossRef, dblp, EuropePMC, OpenAlex
2. **Fetching**: Downloading metadata and full texts from DOIs and open-access repositories
3. **Organizing**: Categorizing by topic, date, and custom taxonomies
4. **Searching**: Enabling fast, intelligent queries across the corpus
5. **Analyzing**: Supporting data-driven insights from the paper collection

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Paper Ingestion Pipeline                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  Discovery   │───▶│    Fetch     │───▶│  Processing   │                  │
│  │              │    │              │    │              │                  │
│  │ • Query      │    │ • Metadata   │    │ • Dedupe     │                  │
│  │   configs    │    │ • Full text  │    │ • Classify   │                  │
│  │ • 27 repos   │    │ • DOIs       │    │ • Index      │                  │
│  │ • MultiVideo │    │              │    │              │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                        │                      │                             │
│                        ▼                      ▼                             │
│              ┌─────────────────────────┐                                  │
│              │    Knowledge Base       │◀─────────────────────────────────┤
│              │                          │                                  │
│              │ • papers/ (YAML)        │                                  │
│              │ • full_texts/ (PDF/MD)  │                                  │
│              │ • by_topic/             │                                  │
│              │ • by_date/              │                                  │
│              │ • scripts/              │                                  │
│              └─────────────────────────┘                                  │
│                        │                                                      │
│                        ▼                                                      │
│              ┌─────────────────────────┐                                  │
│              │   Analysis & Output     │                                  │
│              │                          │                                  │
│              │ • Articles (MDX)        │                                  │
│              │ • Reports               │                                  │
│              │ • Visualizations        │                                  │
│              └─────────────────────────┘                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Discovery Layer

### 3.1 Source Configuration

We maintain **discovery queries** in `config/taxonomy.yaml` for each research repository:

```yaml
# arXiv queries (cat: cs.AI, cs.LG, cs.CY, econ.GN)
arxiv_queries:
  - query: 'cat:cs.AI AND (abs:"lead generation" OR abs:"lead scoring")'
    category: ai-marketing
    subcategory_hint: empirical
  - query: 'cat:cs.LG AND (abs:"machine learning" AND abs:"marketing")'
    category: ai-marketing
    subcategory_hint: measurement

# Multi-source queries (CrossRef, dblp, EuropePMC)
other_sources_queries:
  - source: crossref
    query: artificial intelligence lead generation marketing B2B
    category: ai-marketing
    subcategory_hint: framework
  - source: dblp
    query: machine learning lead scoring marketing
    category: ai-marketing
    subcategory_hint: measurement

# OpenAlex bulk fetch
openalex_queries:
  - category: ai-marketing
    query: '"artificial intelligence" "lead generation" marketing'
    subcategory_hint: empirical
```

### 3.2 Repository Coverage

| Repository | Papers | Domain | Sources |
|------------|--------|--------|---------|
| marketing-research | 19,718 | Marketing | arXiv, CrossRef, dblp, EuropePMC |
| contextual-intelligence-research | 737 | Contextual AI | DOI, manually curated |
| ai-lead-marketing (curated) | 28 | AI + Lead Gen | Filtered from above |
| **Total** | **20,455** | All | Multiple |

### 3.3 Distributed Fetching

The `distributed_fetch.py` script coordinates paper fetching across multiple hosts:

```python
# hosts.py configuration
hosts = {
    'tobias-weiss.org': {
        'ssh': 'weiss@tobias-weiss.org',
        'python': '/usr/bin/python3',
        'repos': ['marketing-research', 'contextual-intelligence-research'],
    },
    'chemie-lernen.org': {
        'ssh': 'weiss@chemie-lernen.org',
        'python': '/usr/bin/python3.11',
        'repos': ['dm-research', 'software-development-research'],
    },
    'contextual-intelligence.org': {
        'ssh': 'weiss@contextual-intelligence.org',
        'python': '/usr/bin/python3.12',
        'repos': ['ai-literacy-research', 'agentic-vr-research'],
    },
}
```

**Balanced assignment**: Repos are assigned to hosts based on paper count to 
distribute load evenly.

**Fallback mechanism**: If a host fails, the script retries on the next available host.

---

## 4. Fetching Layer

### 4.1 Metadata Fetching

For each source type, we use specialized fetchers:

- **arXiv**: Uses arXiv API (`http://export.arxiv.org/api/query`)
- **CrossRef**: REST API with Unpaywall integration for open-access detection
- **dblp**: XML API with bibliographic data
- **EuropePMC**: REST API for biomedical/preprint literature
- **OpenAlex**: Graph API for comprehensive metadata

### 4.2 Full-Text Fetching

The `fetch_full_texts.py` script implements a tiered approach:

```
1. Direct PDF from URL
   └── If URL ends with .pdf or returns application/pdf

2. DOI Resolution
   ├── Unpaywall API (open-access detection)
   ├── Semantic Scholar (open-access PDFs)
   └── arXiv (for arXiv DOIs)

3. HTML to Text (fallback)
   └── Fetch HTML, strip tags, clean up
```

**Success Rates** (from 28 AI+Lead papers):
- Direct PDF: 3/28 (10.7%)
- Via Unpaywall: 1/28 (3.6%)
- Via HTML extraction: 17/28 (60.7%)
- **TotalSuccess: 21/28 (74.1%)**
- Failed (paywalled/broken): 7/28 (25.9%)

### 4.3 Rate Limiting and Politeness

- **2-second delay** between requests to the same source
- **User-Agent** identifies our bot: `"Contextual-Intelligence-KB/1.0 (research@tobias-weiss-ai-xr.de)"`
- **Retry logic**: 3 attempts per fetch, with exponential backoff

---

## 5. Processing Layer

### 5.1 Deduplication

```python
def deduplicate(papers):
    seen = set()
    unique = []
    for p in papers:
        key = (p.get('title', ''), p.get('url', ''))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique
```

**Deduplication key**: Title + URL combination ensures we don't miss papers with 
similar titles but different content.

### 5.2 Classification

Papers are auto-classified using:

1. **Explicit hints**: If `subcategory_hint` is provided in the query config
2. **Keyword matching**: Subcategory keywords defined in `taxonomy.yaml`
3. **Fallback**: Manual classification via repo-specific `classify_subcategory()`

```yaml
# taxonomy.yaml
subcategory_keywords:
  empirical:
    - "experiment"
    - "field study"
    - "empirical"
    - "evidence"
    - "large-scale"
  framework:
    - "framework"
    - "conceptual model"
    - "taxonomy"
    - "architecture"
```

### 5.3 Organization

The `merge_papers.py` script creates a layered organization:

```
knowledgebase/
├── papers/                          # Source YAML files
│   ├── ai-lead-marketing.yaml       # 28 curated papers
│   ├── marketing-research.yaml      # 19,718 papers
│   └── all-papers.yaml              # 20,455 merged, deduplicated
│
├── full_texts/                      # Full text content
│   └── ai-lead-marketing/           # 21 full texts
│       ├── Paper_Title_1.pdf
│       └── Paper_Title_2.md
│
├── by_topic/                        # Auto-organized by category
│   ├── ai-marketing/                # 3,689 papers
│   ├── b2b/                         # 392 papers
│   └── ... (13 total categories)
│
└── by_date/                         # Auto-organized by date
    ├── 2026-10/                    # 99 papers
    ├── 2026-09/                    # 529 papers
    └── ... (51 time periods)
```

---

## 6. Search Layer

### 6.1 Search Script

`search_kb.py` provides keyword search across the merged paper collection:

```python
def search_papers(keywords, limit=20):
    papers = load_all_papers()
    keywords_lower = [k.lower() for k in keywords]
    
    results = []
    for p in papers:
        title = p.get('title', '').lower()
        abstract = p.get('abstract', '').lower()
        combined = title + ' ' + abstract
        matches = sum(1 for kw in keywords_lower if kw in combined)
        if matches > 0:
            results.append((p, matches))
    
    results.sort(key=lambda x: (-x[1], x[0].get('date', '0000-00')), reverse=True)
    return [r[0] for r in results[:limit]]
```

### 6.2 Query Examples

```bash
# Search for AI + lead generation papers
python scripts/search_kb.py "AI" "lead generation"

# Search for federated learning in marketing
python scripts/search_kb.py "federated learning" "marketing"

# Search for B2B chatbots
python scripts/search_kb.py "chatbots" "B2B"
```

---

## 7. Output Layer: From Knowledge Base to Articles

The knowledge base powers **content generation** for [tobias-weiss.org](https://tobias-weiss.org):

### 7.1 Article Generation Workflow

```
Knowledge Base (20,455 papers)
    │
    ▼
Filter by topic: AI + Lead Generation (28 papers)
    │
    ▼
Extract key findings:
  - Predictive lead scoring frameworks
  - Conversational AI for B2B
  - Federated learning approaches
  - Orchestration models
    │
    ▼
Generate structured outline:
  - Executive Summary
  - Core Technologies
  - Case Studies
  - Implementation Guide
    │
    ▼
Write article: ai-powered-lead-generation-marketing.mdx
    │
    ▼
Commit → next-tobias-weiss-org/content/articles/
```

### 7.2 Example: AI-Powered Lead Generation Article

The article [AI-Powered Lead Generation: Transforming Marketing with Artificial 
Intelligence](https://tobias-weiss.org/content/ai-powered-lead-generation-marketing/) 
was generated from analysis of 28 papers in the knowledge base, including:

1. Citation of 8 key research papers
2. Statistics from 6 empirical studies
3. 3 case studies with concrete metrics
4. 4-step implementation framework

---

## 8. Technical Implementation

### 8.1 Tools and Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Scripting | Python 3.9+ | Core workflow orchestration |
| YAML Processing | PyYAML | Config and paper metadata |
| HTTP Requests | `requests` | API fetching |
| Parallelism | `concurrent.futures` | Distributed fetching |
| SSH | `paramiko` | Remote host coordination |
| Text Processing | `re` (regex) | HTML cleaning, extraction |
| Build | Next.js | Website generation |

### 8.2 Repository Structure

```
skeleton-research/          # Template for new research projects
├── papers.yaml             # Paper collection
├── config/
│   ├── taxonomy.yaml       # Categories and queries
│   └── other_sources_queries.yaml
├── knowledgebase/
│   ├── papers/
│   ├── full_texts/
│   ├── by_topic/
│   ├── by_date/
│   └── scripts/
│       ├── fetch_full_texts.py
│       ├── merge_papers.py
│       └── search_kb.py
└── README.md

marketing-research/          # Domain-specific research
├── papers.yaml             # 19,718 papers
├── config/
│   ├── taxonomy.yaml       # Marketing-specific queries
│   └── other_sources_queries.yaml
└── scripts/
    └── fetch/

next-tobias-weiss-org/      # Website
├── content/
│   ├── articles/
│   │   └── ai-powered-lead-generation-marketing.mdx
│   └── research/
│       └── lehre.mdx      # Updated with AI lead scoring
```

### 8.3 Dependency Graph

```
marketing-research/config/taxonomy.yaml
    └── Defines discovery queries
    
Distributed fetch (hosts.py)
    ├── tobias-weiss.org
    ├── chemie-lernen.org
    └── contextual-intelligence.org
    
marketing-research/papers.yaml ← Updated with new papers
    
contextual-intelligence/knowledgebase/papers/all-papers.yaml ← Merged collection
    
contextual-intelligence/knowledgebase/full_texts/ ← Full text storage
    
next-tobias-weiss-org/content/articles/ai-powered-lead-generation-marketing.mdx ← Generated article
    
next-tobias-weiss-org/content/research/lehre.mdx ← Updated lecture content
```

---

## 9. Results and Metrics

### 9.1 Knowledge Base Statistics

| Metric | Value |
|--------|-------|
| Total papers | 20,455 |
| Source repositories | 27 |
| Discovery queries | 20+ per repo |
| Full texts fetched | 21/28 (74.1%) for AI+Lead subset |
| Topics/categories | 13 |
| Date range | 1987 - 2026 |
| Most recent paper | October 2026 |

### 9.2 Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Fetch metadata (1 paper) | 2-5 seconds | API rate limited |
| Fetch full text (1 paper) | 1-10 seconds | HTML processing varies |
| Deduplicate 20K papers | 3-5 seconds | Memory-efficient |
| Merge 3 sources | 8-12 seconds | 20K papers |
| Full script run | 15-30 minutes | 27 repos × 20 queries |

### 9.3 Storage Requirements

| Component | Size |
|-----------|------|
| Papers YAML (20K) | ~50 MB |
| Full texts (21 papers) | ~2.5 MB |
| By-topic index | ~10 MB |
| By-date index | ~10 MB |
| **Total** | **~72.5 MB** |

---

## 10. Lessons Learned

### 10.1 What Worked Well

1. **Separation of concerns**: Keeping discovery, fetching, processing, and search 
   as separate layers made the system easier to debug and extend.

2. **Distributed fetching**: Spreading the load across multiple hosts prevented 
   rate limiting and improved reliability.

3. **YAML for metadata**: YAML provides a good balance of human-readability 
   and machine-parseability for paper metadata.

4. **Progressive enhancement**: Starting with simple queries and gradually adding 
   complexity allowed us to validate each step.

### 10.2 Challenges and Solutions

| Challenge | Solution |
|-----------|----------|
| rsync compatibility | Removed `--info=progress0` flag, works with older versions |
| Missing config files | Created default configs for repos without them |
| API rate limits | 2-second delay between requests, retry with backoff |
| DOI resolution | Multiple fallback sources (Unpaywall, Semantic Scholar, arXiv) |
| HTML cleanup | Custom regex-based extraction for inconsistent formats |
| Large file handling | Stream processing for memory efficiency |

### 10.3 Future Improvements

1. **Incremental fetching**: Instead of re-fetching everything, track last-modified 
   dates and only fetch new papers.

2. **Vector embeddings**: Add semantic search using sentence-transformers or 
   other embedding models.

3. **Citation graph**: Build a network of citations between papers to identify 
   influential works and relationships.

4. **Automated summarization**: Use LLMs to generate abstracts for papers without 
   them, enabling faster review.

5. **Visual exploration**: Interactive graphs showing paper relationships, 
   temporal trends, and topic clusters.

6. **Webhook integration**: Trigger alerts when new papers matching specific 
   criteria are published.

---

## 11. Conclusion

Building a scalable paper ingestion workflow requires careful attention to:

1. **Modular design**: Each layer (discovery, fetching, processing, search) should 
   be independently testable and replaceable.

2. **Robust error handling**: Networks fail, APIs change, data is messy. 
   Anticipate and handle these cases gracefully.

3. **Polite automation**: Respect rate limits, use proper User-Agents, and 
   implement backoff logic.

4. **Human-in-the-loop**: While automation handles the scale, human curation 
   ensures quality and relevance.

Our workflow now powers:
- **20,455+ papers** in the knowledge base
- **21 full texts** for deep analysis
- **1 published article** on AI-powered lead generation
- **Updated lecture content** on latest AI developments

The infrastructure is extensible and can be adapted to new domains by simply 
adding query configurations and running the ingestion pipeline.

---

## 12. References

The following papers from our knowledge base informed this workflow:

1. **Jha, H. C.** (2026). "The Growth Orchestration Model: An AI-Era Operating Model 
   for SMB Lead Generation". Figshare. DOI: [10.6084/m9.figshare.34020624](https://doi.org/10.6084/m9.figshare.34020624)

2. **Kayal, S.** (2026). "AI-POWERED MARKETING ANALYTICS AND CUSTOMER EXPERIENCE 
   MANAGEMENT: Transforming Customer Engagement and Business Performance". 
   Iterative International Publishers eBooks. DOI: [10.58532/nbennur3429c7](https://doi.org/10.58532/nbennur3429c7)

3. Various papers on AI chatbots, federated learning, and marketing automation 
   (see [Knowledge Base](https://github.com/tobias-weiss-ai-xr/contextual-intelligence/tree/main/knowledgebase))

---

## Appendix A: File Listing

```
keleton-research/
├── README.md                      # This document
├── paper-ingestion-workflows.md   # This paper
├── papers.yaml                     # Template paper collection
└── config/
    ├── taxonomy.yaml              # Template query config
    └── other_sources_queries.yaml # Template multi-source config

contextual-intelligence/knowledgebase/
├── README.md
├── papers/
│   ├── ai-lead-marketing.yaml
│   ├── marketing-research.yaml
│   ├── contextual-intelligence-research.yaml
│   └── all-papers.yaml
├── full_texts/
│   └── ai-lead-marketing/ (21 files)
├── by_topic/ (13 directories)
├── by_date/ (51 directories)
└── scripts/
    ├── fetch_full_texts.py
    ├── merge_papers.py
    └── search_kb.py

marketing-research/
├── config/
│   ├── taxonomy.yaml (updated)
│   └── other_sources_queries.yaml (new)
├── papers.yaml
├── ai-lead-marketing-papers.yaml (new)
└── knowledgebase/ (full texts mirror)
```

---

## Appendix B: Setup Instructions

### For a New Research Project

1. Clone the skeleton:
   ```bash
   git clone git@github.com:tobias-weiss-ai-xr/skeleton-research.git my-research
   cd my-research
   ```

2. Configure discovery queries in `config/taxonomy.yaml`

3. Run the ingestion:
   ```bash
   python distributed_fetch.py --repos my-repo --sources arxiv,other --months 6
   ```

4. Fetch full texts:
   ```bash
   python scripts/fetch_full_texts.py
   ```

5. Merge sources:
   ```bash
   python scripts/merge_papers.py
   ```

6. Search the knowledge base:
   ```bash
   python scripts/search_kb.py "your" "keywords"
   ```

---

*This paper and the described infrastructure are open source. See 
[GitHub](https://github.com/tobias-weiss-ai-xr/contextual-intelligence) for the 
latest version.*
