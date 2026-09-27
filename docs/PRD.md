# PRD — BIS Knowledge Ingestion Pipeline & RAG Engine

**Project:** SIH26107 — AI-powered Intelligent Assistant for Indian Standards and BIS Services **Scope of this PRD:** Ameen's ownership area only — the AI Engine, specifically the BIS data pipeline (knowledge ingestion) and the RAG system built on top of it. This PRD does not cover the rest of the SIH team's work (frontend, multilingual UI layer, deployment infra owned by others, etc.) except where the RAG engine must expose an interface to them. **Intended consumer of this document:** Claude Code, to scaffold and implement the system incrementally, phase by phase. **Status:** v1 — niche and core IS numbers verified against live BIS sources as of 2026-09-23. Some structural details (marked ⚠️ OPEN VERIFICATION) still require hands-on inspection before Phase 2 collector code is written, per the project's own engineering discipline (no guessed URL patterns).

---

## 1. Problem Statement Recap (for context only)

SIH26107 asks for an AI assistant that helps industries and consumers with Indian Standards / BIS: answering standards questions, recommending applicable standards, explaining certification schemes and processes, consumer BIS queries, hallmarking guidance, testing lab suggestions, multilingual interaction, and — critically — **source-backed, retrieval-grounded answers with document/clause references**.

Ameen's responsibility is everything upstream and inside the AI Engine that makes "source-backed, retrieval-grounded" true: turning scattered official BIS information into a structured, traceable knowledge corpus, and building the RAG system that retrieves from it.

---

## 2. Goals

1. Prove, end-to-end, on one real product niche, that official BIS information can be automatically collected, structured as a knowledge graph + documents, and turned into RAG-ready chunks with full provenance.
2. Every chunk retrievable by the RAG system must be traceable back to: IS number → document → page/section/clause → original BIS source URL.
3. Preserve the standard-vs-mandatory-certification distinction (QCOs modeled as separate, explicit entities, never inferred).
4. Make the collector config-driven and niche-agnostic, so a second niche can be added by writing a config file, not new code.
5. Produce a working retriever + LLM answer layer that a judge can query live during SIH demo and get a grounded answer with citations.

### Non-Goals (explicitly out of scope for this PRD)

- Training or fine-tuning an LLM.
- Bypassing any BIS paywall/authentication to obtain full standard text.
- Covering all BIS standards or product categories — one niche only for MVP.
- Building the multilingual UI, consumer hallmarking flows, or lab-suggestion UI (those consume this system's output but aren't built here).
- Production-grade auth, scaling, or multi-tenant concerns — this is a hackathon MVP.

---

## 3. Niche Selection (verified)

### Decision: **Electrical Appliances for Domestic Water Heating**

(broader than "just electric water heaters" — this is the actual BIS QCO product group, which gives a richer graph than any single-standard niche)

### Why this niche, vs. the alternatives considered

| Niche | Verification finding | Verdict |
| --- | --- | --- |
| **Domestic Water Heating (chosen)** | Confirmed official QCO — *"Electrical Appliances for domestic water heating (Quality Control) Order, 2023"*, Gazette S.O. 1253(E), published 5 Mar 2024 — links **5 IS numbers** under one order. Product manual for IS 2082 confirmed hosted directly on `bis.gov.in`. Multiple amendments exist. | **Selected** — richest verified multi-node graph at MVP scale |
| Protective Helmets (IS 4151) | Product manual + 2 amendments confirmed, but QCO covers only **1** IS number → graph collapses to a single node, doesn't demonstrate `HAS_QCO`/`RELATED_TO` fan-out. Also an overused SIH/road-safety example. | Rejected — too thin for graph demo |
| Cement | Data exists but spans dozens of IS numbers/grades — too large to scope for an MVP without heavy manual pruning; also a very common example in BIS-related hackathon projects already. | Rejected — poor MVP fit, oversaturated example |
| LED Lights/Luminaires, Pressure Cookers | Not verified in depth (deprioritized once water heaters confirmed sufficient) | Not pursued further |

### Verified core dataset (human-reviewed, CORE/SUPPORTING/RELATED)

| IS Number | Title | Class | Verified facts |
| --- | --- | --- | --- |
| **IS 2082:2018** | Stationary Storage Type Electric Water Heaters – Specification | CORE | Product manual confirmed public on `bis.gov.in` (`PM_IS-2082.pdf`); 1 amendment; QCO-mandatory |
| **IS 368:2014** | Electric Immersion Water Heaters | CORE | Listed in QCO; product manual existence to be confirmed during Phase 1 crawl |
| **IS 17150:2019** | Mini Domestic Water Heater for use with Piped Natural Gas (PNG) | CORE | Listed in QCO — **note:** gas-fired, not electric; model `fuel_type` explicitly, don't silently bucket as "electric" |
| **IS 302 (Part 2/Sec 21):2018** | Particular requirements — stationary storage type electric water heaters (safety base standard) | SUPPORTING | Referenced by IS 2082 as its safety base — this is the concrete example of the "base safety standard → product standard" relationship pattern |
| **IS 302 (Part 2/Sec 35):2017** | Particular requirements — electric instantaneous water heaters | SUPPORTING | Safety base standard; anchor for a possible future "instantaneous heater" sub-branch (not in MVP core, but graph-linkable) |
| IS 302 (Part 1) | General requirements for household electrical appliances | RELATED | Parent general-safety standard both 302-2-21 and 302-2-35 depend on. Link as `RELATED_TO`, not a core ingestion target for MVP. |

**Access status (verified, recorded per your data model, not assumed):**

- Product manuals → **public**, hosted directly on `bis.gov.in`
- QCO gazette notification → **public** (multiple mirrors found; treat the original Gazette/PIB or `bis.gov.in`-hosted PDF as canonical, mirrors as fallback only)
- Full current standard text (IS 2082:2018, IS 368:2014, etc.) → **restricted**, sold via BIS Standards Portal — record `full_standard_access: restricted`. Do not substitute old superseded editions from third-party archives as if they were the current restricted standard; if included at all, they must be tagged `superseded: true, authoritative: false` and clearly separated from current-standard chunks.
- Laboratory list → BIS publishes **general** recognised-lab lists (Group-1/Group-2 PDFs), not filtered per-IS. A separate lookup tool exists: `lims.bis.gov.in` ("IS-Wise Test Facilities" search). This is the correct source for `TESTED_BY` — not the static PDF lists.

---

## 4. ⚠️ Open Verification Items (must resolve before writing collector code)

These follow directly from your own Step 4/5 discipline ("do not invent undocumented URL patterns"). I could not fully resolve these via search/fetch alone and they need hands-on inspection (browser devtools / manual navigation), which is the first task of Phase 1:

1. **"Know Your Standard" is now a JS single-page app**, relocated to `https://standards.bis.gov.in/website/know-your-standards` (not the old static page). It is search-driven (enter IS number or keyword) and almost certainly calls a backend API to render results. **Action:** open it in a browser, use devtools Network tab, search for IS 2082, and capture the actual API endpoint(s) and response shape. This determines whether the collector can call the API directly (ideal) or needs headless-browser scraping (fallback, slower but fine for MVP scale).
2. **`lims.bis.gov.in`** (labs/testing facilities, "IS-Wise Test Facilities") — same treatment: inspect actual search mechanism for IS 2082 before assuming it's scrapable via simple requests.
3. Confirm whether IS 368 and IS 17150 have their own product manuals on `bis.gov.in` (only IS 2082's manual was directly confirmed this round) — do this as part of the Phase 1 metadata crawl, not assumed.
4. Confirm the canonical, first-party host of the QCO gazette PDF (vs. the third-party mirrors found during research) — prefer `bis.gov.in`, `egazette.gov.in`, or `dpiit.gov.in` if the notification is hosted there.

**These are Phase 1, Task 1 — not blockers to writing this PRD, but they are blockers to writing collector code**, exactly per your Step 4→6 ordering.

---

## 5. System Architecture

```
                    ┌─────────────────────────────────────┐
                    │        NICHE CONFIG (JSON)            │
                    │  niche + verified IS number list      │
                    └───────────────────┬───────────────────┘
                                         ▼
┌───────────────────────────── DATA PIPELINE ─────────────────────────────┐
│                                                                           │
│  Stage 1: Metadata Collection  (collectors/kys.py)                      │
│      ↓                                                                   │
│  Stage 2: Document Discovery & Download                                 │
│      (collectors/product_manuals.py, qco.py, guidelines.py, labs.py)    │
│      ↓                                                                   │
│  Stage 3: Text Extraction  (processors/pdf_extractor.py — PyMuPDF)      │
│      ↓                                                                   │
│  Stage 4: Text Cleaning  (processors/text_cleaner.py)                   │
│      ↓                                                                   │
│  Stage 5: Metadata Extraction  (processors/metadata_extractor.py)       │
│      ↓                                                                   │
│  Stage 6: Relationship Mapping  (processors/relationship_mapper.py)     │
│      ↓                                                                   │
│  Stage 7: Validation  (validators/*)                                    │
│      ↓                                                                   │
│  Stage 8: Completeness Report  (reports/)                               │
│                                                                           │
└─────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │   RAG-READY CHUNK STORE        │
                    │  (chunks + provenance metadata)│
                    └───────────────┬───────────────┘
                                     ▼
┌────────────────────────────── RAG ENGINE ────────────────────────────────┐
│                                                                            │
│  Embedding + Indexing  →  Vector Store (Chroma, MVP-appropriate)          │
│      ↓                                                                    │
│  Retriever (hybrid: vector similarity + IS-number/metadata filter)       │
│      ↓                                                                    │
│  Reranking (optional, MVP: skip or simple cross-encoder)                 │
│      ↓                                                                    │
│  Prompt Assembly (retrieved chunks + provenance + user query)            │
│      ↓                                                                    │
│  LLM (Claude, via API — no fine-tuning)                                  │
│      ↓                                                                    │
│  Source-backed Answer + citations (IS no. / doc / page / section / URL)  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────┘
```

This is intentionally **two loosely-coupled subsystems with one contract between them**: the RAG-ready chunk store. That contract (Section 7.4) is what lets you build and validate the pipeline completely before touching RAG, exactly as you specified in your Step 10.

---

## 6. Data Pipeline — Detailed Requirements

### 6.1 Stage 1 — Niche Configuration

**Input:** `config/niches/water_heaters.json`

```json
{
  "niche": "Electrical Appliances for Domestic Water Heating",
  "is_numbers": [
    { "is_number": "IS 2082:2018", "class": "CORE" },
    { "is_number": "IS 368:2014", "class": "CORE" },
    { "is_number": "IS 17150:2019", "class": "CORE" },
    { "is_number": "IS 302 (Part 2/Sec 21):2018", "class": "SUPPORTING" },
    { "is_number": "IS 302 (Part 2/Sec 35):2017", "class": "SUPPORTING" }
  ],
  "qco_reference": {
    "title": "Electrical Appliances for domestic water heating (Quality Control) Order, 2023",
    "gazette_id": "S.O. 1253(E)",
    "published": "2024-03-05"
  }
}
```

Collector must be generic over this file — no niche-specific logic in code, only in config.

### 6.2 Stage 2 — Metadata Collection

For every IS number, attempt to collect via the (to-be-confirmed, see §4) Know Your Standard interface and fall back to direct navigation of Product Certification pages:

```
IS Number, Title, Product, Category, Status, Edition/Year, Source URL,
Document links, Product Manual (or not_found), SIT, Amendments,
QCO/notifications, Certification info, Laboratory info, Related standards
```

Missing fields are recorded explicitly (`"status": "not_found"`), never omitted.

### 6.3 Stage 3 — Document Collection

Per document: verify official BIS-family source (`bis.gov.in`, `standards.bis.gov.in`, `lims.bis.gov.in`, or an official Gazette host), determine access status, download only public material, record source URL, retrieval timestamp, SHA-256 hash, local path.

```json
{
  "document_id": "DOC_001",
  "is_number": "IS 2082:2018",
  "document_type": "product_manual",
  "source_url": "https://bis.gov.in/wp-content/uploads/2019/05/PM_IS-2082.pdf",
  "local_path": "documents/IS_2082/product_manual.pdf",
  "access_status": "public",
  "retrieved_at": "2026-09-23",
  "sha256": "..."
}
```

### 6.4 Stage 4 — Text Extraction

PyMuPDF, page-numbered output preserved per page (needed for citations). One `.txt` (or structured JSON with per-page text) per source PDF.

### 6.5 Stage 5 — Text Cleaning

Remove repeated headers/footers, fix broken line breaks, normalize whitespace — preserve headings, clause numbers, page numbers, tables where feasible. Must not alter substantive meaning.

### 6.6 Stage 6 — Metadata Extraction

Deterministic extraction first (regex/rules for clause numbers, IS references). LLM used only for harder structured extraction (scope, testing/sampling requirements) — LLM output is never the source of truth; original document + URL stay attached to every extracted fact.

### 6.7 Stage 7 — Relationship Mapping

Explicit `source_id | relationship | target_id` table. Minimum relationship types for this niche:

```
IS2082    | HAS_PRODUCT_MANUAL | DOC001
IS2082    | HAS_AMENDMENT      | DOC00x
IS2082    | HAS_QCO            | QCO_2023_SO1253E
IS2082    | BASED_ON           | IS302-2-21     (safety base standard)
IS368     | HAS_QCO            | QCO_2023_SO1253E
IS17150   | HAS_QCO            | QCO_2023_SO1253E
IS2082    | TESTED_BY          | LAB_xxx         (once lims.bis.gov.in mechanism confirmed)
IS2082    | RELATED_TO         | IS368           (same QCO group)
```

### 6.8 Stage 8 — Validation

Per-document checklist: official BIS source? correct IS-number association? readable? text extraction succeeded? duplicate (by URL+hash)? source URL present? access status known? metadata internally consistent?

### 6.9 Stage 9 — Completeness Report

Per IS number, a table of expected vs. found:

| Data Type | Status |
| --- | --- |
| Standard metadata | Available |
| Full Standard | Restricted |
| Product Manual | Available / Not Found |
| SIT | Available / Not Found |
| Amendments | Available (n) |
| QCO | Available |
| Laboratories | Available / Not Found |
| Related Standards | Available |

This report is a required deliverable, not optional telemetry — it's how you and judges assess corpus integrity at a glance.

### 6.10 Error Handling

Per-document try/except; one failure never halts the batch. Log to `reports/errors.json`:

```json
{ "document": "DOC003", "status": "error", "reason": "HTTP timeout", "retry_count": 3 }
```

### 6.11 Deduplication & Updates

Dedup by `URL + SHA-256`. On re-run: compare hash; if unchanged, skip; if changed, store as a new version (`retrieved_at`/`last_checked`/`document_hash` history), never silently overwrite.

---

## 7. RAG Engine — Detailed Requirements

### 7.1 Chunking Strategy

Semantic boundaries first (Section → Subsection → Clause → Paragraph), not arbitrary fixed-size splitting. Fixed-size chunking only as a fallback when a document has no extractable structure (rare for BIS product manuals, which are clause-numbered).

### 7.2 Chunk Schema (the pipeline↔RAG contract)

```json
{
  "chunk_id": "IS2082_PM_P3_C02",
  "text": "...",
  "is_number": "IS 2082:2018",
  "document_type": "product_manual",
  "document_id": "DOC001",
  "page": 3,
  "section": "Sampling Guidelines",
  "clause": "2(a)",
  "source_url": "https://bis.gov.in/wp-content/uploads/2019/05/PM_IS-2082.pdf",
  "product_category": "Electrical Appliances for Domestic Water Heating",
  "access_status": "public"
}
```

Every field except `clause` (not always applicable) is mandatory. A chunk missing `source_url` or `is_number` must fail validation and never enter the index.

### 7.3 Retrieval

- **Vector store:** Chroma (local, zero-infra — appropriate for hackathon MVP; swap later if needed, not now)
- **Embedding model:** any solid open embedding model available in the environment (e.g., a sentence-transformers model) — no LLM fine-tuning, per your constraint
- **Retrieval mode:** hybrid — vector similarity + metadata filter (e.g., filter by `is_number` or `document_type` when the query names a specific standard or document kind)
- **Top-k:** tune empirically; start at k=5–8 chunks per query

### 7.4 Generation

- LLM: Claude via API, no fine-tuning
- Prompt must instruct the model to **answer only from retrieved chunks**, cite `is_number` + `document_type` + `page`/`section` for every claim, and explicitly say when the standard is restricted (i.e., surface `access_status` to the user rather than pretending full-text knowledge)
- Must refuse to answer, or clearly flag low confidence, when retrieval returns no relevant chunks — no fabrication of BIS facts (mirrors your Stage 6 rule against LLM-fabricated metadata)

### 7.5 Answer Contract (what the RAG layer returns to the rest of the SIH team)

```json
{
  "answer": "...",
  "citations": [
    {
      "is_number": "IS 2082:2018",
      "document_type": "product_manual",
      "page": 3,
      "section": "Sampling Guidelines",
      "source_url": "...",
      "access_status": "public"
    }
  ],
  "confidence": "high | low | insufficient_evidence"
}
```

This is the interface boundary with the rest of the team's frontend/multilingual layer — stable contract, independent of internal pipeline changes.

---

## 8. Storage Layout

```
bis-data-pipeline/
├── config/
│   └── niches/
│       └── water_heaters.json
├── collectors/
│   ├── kys.py              # Know Your Standard (API or headless, per §4 finding)
│   ├── product_manuals.py
│   ├── guidelines.py
│   ├── labs.py              # lims.bis.gov.in, per §4 finding
│   └── qco.py
├── processors/
│   ├── pdf_extractor.py     # PyMuPDF, page-preserving
│   ├── text_cleaner.py
│   ├── metadata_extractor.py
│   └── relationship_mapper.py
├── validators/
│   ├── document_validator.py
│   └── corpus_validator.py
├── storage/
│   └── data/
│       ├── raw/{html,documents}/
│       └── processed/{metadata,text,relationships}/
│       IS_2082/
│         metadata.json
│         relationships.json
│         documents/{product_manual.pdf, amendment_1.pdf, ...}
│         text/{product_manual.txt, ...}
├── rag/
│   ├── chunker.py
│   ├── embed_index.py       # builds/updates the Chroma index
│   ├── retriever.py
│   ├── prompt_templates.py
│   └── answer_service.py    # exposes the Answer Contract (§7.5)
├── reports/
│   ├── completeness_report.json
│   └── errors.json
├── pipeline.py               # orchestrates Stages 1–9
└── README.md
```

---

## 9. Tech Stack

| Layer | Choice | Rationale |
| --- | --- | --- |
| Language | Python | Per your spec |
| HTTP | `requests` | Simple pipeline HTTP |
| HTML parsing | BeautifulSoup | Static pages |
| Headless (if needed per §4) | Playwright | Only if KYS/LIMS require JS rendering |
| PDF extraction | PyMuPDF | Page-preserving text extraction |
| Structured storage | JSON files (MVP) → SQLite if query needs grow | Avoid over-engineering per your Constraint #10 |
| Vector store | Chroma | Zero-infra, fast to stand up |
| LLM | Claude API | No training from scratch |
| Data processing | Pandas | Where genuinely useful (reports, dedup) |

---

## 10. Milestones (mapped to Claude Code build phases)

**Phase 0 — Verification (before any collector code)**

- Resolve all items in §4 (KYS API/structure, LIMS structure, IS 368/17150 manual confirmation, canonical QCO host)
- Manually inspect one representative IS number (IS 2082) end-to-end and document exactly what BIS exposes

**Phase 1 — Single-IS Collector (proves the pattern)**

- Build collector for IS 2082 only
- Manual validation of output against §6.9 completeness table

**Phase 2 — Generalize to All 5 IS Numbers**

- Run the same collector across the full niche config
- Validate + generate completeness report

**Phase 3 — Processing Pipeline**

- Extraction → cleaning → metadata extraction → relationship mapping → validation, for the full niche corpus

**Phase 4 — Chunking + Indexing**

- Semantic chunking, chunk schema validation, embedding + Chroma index build

**Phase 5 — Retriever + Generation**

- Retriever, prompt templates, answer service implementing the Answer Contract (§7.5)
- End-to-end query test: ask real BIS questions about domestic water heaters, verify grounded, cited answers

**Phase 6 — Demo Hardening**

- Error handling polish, a small set of pre-validated demo queries, completeness report presentable for judges

---

## 11. Success Criteria (SIH-demo level)

- A judge can ask a natural-language question about electric water heater certification (e.g., "Is BIS certification mandatory for immersion water heaters, and which standard applies?") and get an answer that:
  - Is correct
  - Cites the specific IS number, document, and page/section
  - Correctly distinguishes "standard exists" from "certification mandatory" (citing the QCO, not just the standard)
  - Explicitly states when full standard text is restricted rather than fabricating its content
- Completeness report for all 5 IS numbers is presentable and shows no silently-dropped data
- Pipeline re-run is idempotent (no duplicate documents, hash-based dedup works)
- One additional niche (config-only) can be swapped in without code changes, as a scalability proof point if time allows

---

## 12. Engineering Constraints (carried over, non-negotiable)

1. Official BIS sources are the source of truth.
2. Never bypass restricted/paywalled content.
3. Never assume a standard is publicly downloadable — verify per-document.
4. Never equate "standard exists" with "certification mandatory" — QCOs are separate entities.
5. Preserve source URLs on everything.
6. Preserve page/section/clause provenance on every chunk.
7. Never silently discard missing data — record `not_found` explicitly.
8. Never hand-build the corpus document-by-document — automate after human-reviewed IS list.
9. Never hardcode a niche into collector code — config-driven only.
10. Don't over-engineer before the first end-to-end pipeline run works.
11. Never let an LLM fabricate or infer missing BIS facts.
12. Every RAG chunk must remain traceable to its original BIS source.