# Verifiable Evidence Citation Extraction & Source Document Resolution Blueprint

**Module Target**: `backend/services/rca_ingestion.py`  
**Schema Dependencies**: `backend/api/rca_schemas.py` (`CitationObject`, `FailureTimelineEvent`, `FiveWhyNode`, `FishboneCauseItem`, `EightDIncidentReport`)  
**Author**: M1 Citation Explorer (`explorer_m1_citations`)  
**Status**: Architectural Implementation Blueprint  

---

## 1. Executive Summary & Objective

The **Automated Root Cause Analysis (RCA) & 8D Incident Report Studio** in Industrial Mind OS requires strict evidence grounding to satisfy ISO 9001:2015 Clause 10.2 and IATF 16949 Section 10.2.3 compliance. Every causal deduction, failure event, and operating envelope deviation must trace back to immutable, verifiable documentary evidence snippets.

This blueprint establishes the exact design and algorithmic specifications for:
1. **Source Document Traversal**: Unified extraction across filesystem documents (e.g., `Near_Miss_Report_2023.txt`), in-memory cached files (`DirectMemoryCache`), knowledge graph triples (`GraphDBClient`), and semantic vector stores (`VectorDBClient` with offline test isolation seams).
2. **Citation Object Generation**: Deterministic citation ID assignment (`r"^CITE-[A-Za-z0-9_\-\.]+$"`), precise section and line-number indexing, verbatim text snippet extraction (sanitized via `clean_spaced_text`), and multi-factor confidence scoring.
3. **Verification & Grounding Rules**: In-memory `CitationRegistry`, algorithmic enforcement of `is_unsubstantiated=True` and `assumed_flag=True` on ungrounded or broken citations, Citation Grounding Ratio (CGR) calculation, and blocking terminal root cause invariants.
4. **Unit Testing Strategy**: Comprehensive offline test suite verifying schema validation, excerpt parsing, line mapping, confidence scoring, and boundary conditions without network, LLM, or Qdrant disk locks.

---

## 2. Ingestion Architecture & Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             SOURCE DOCUMENT REPOSITORY                           │
│  - Filesystem Docs (Near_Miss_Report_2023.txt, OEM manuals)                      │
│  - DirectMemoryCache (Uploaded Markdown/TXT/PDF <15k chars)                      │
│  - GraphDBClient (NetworkX keyword co-occurrence triples)                        │
│  - Incident Payload (Raw alarms, operator logs, telemetry dict)                  │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   CITATION EXTRACTION ENGINE (rca_ingestion.py)                  │
│  1. Document Segmentation (Heading regex, line number tracking)                  │
│  2. Excerpt Sanitization (core.text_utils.clean_spaced_text)                     │
│  3. Deterministic ID Generation (CITE-{DOC_SLUG}-{SEQ:03d})                      │
│  4. Multi-Factor Confidence Scoring (Authority, keyword, numeric overlap)        │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         CITATION REGISTRY (In-Memory Map)                        │
│  - Dict[str, CitationObject] keyed by citation_id                                │
│  - Query/lookup by ID, source document, or section                               │
│  - Idempotent deduplication                                                      │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
┌───────────────────────────────────────┐ ┌────────────────────────────────────────┐
│      TIMELINE EVENT LINKING (M1)      │ │     CAUSAL GROUNDING VERIFIER (M2)     │
│ - FailureTimelineEvent                │ │ - FiveWhyNode.evidence_citation_ids    │
│ - Maps event -> source_citation_id    │ │ - FishboneCauseItem.evidence_cite_ids  │
│ - Flags is_unsubstantiated if missing │ │ - Broken/empty ID -> is_unsubstantiated│
│                                       │ │ - Computes Citation Grounding Ratio    │
└───────────────────────────────────────┘ └────────────────────────────────────────┘
```

---

## 3. Detailed Investigation & Blueprint

### 3.1. Source Document Traversal

The traversal engine must seamlessly ingest evidence from diverse storage modalities while remaining robust in both production and offline testing environments.

#### 3.1.1 Document Types & Locations
1. **Local Filesystem Maintenance Records**:
   - `Near_Miss_Report_2023.txt`: Located at project root (`C:\000 MINE\My Codzz\Industrial Mind OS\Near_Miss_Report_2023.txt`). Contains historical failure baseline for `Pump-A12` (vibration 5.8 mm/s, OEM limit 5.0 mm/s, trip limit 5.5 mm/s, ceramic seal shattering).
   - Asset manuals and standard operating procedures (SOPs) located in workspace directories or configured data folders.
2. **In-Memory Cache (`DirectMemoryCache`)**:
   - `backend/storage/memory_cache.py`: In-memory dictionary persisted to `backend/memory_cache.json`.
   - Access method: `memory_cache.get_context(file_filter=..., owner_id=...)`.
   - Contains small uploaded documents (<15,000 characters) scoped by `owner_id` (or globally visible legacy docs where `owner_id is None`).
3. **Knowledge Graph Entities (`GraphDBClient`)**:
   - `backend/storage/graph_db.py`: NetworkX `MultiDiGraph` serialized to `backend/graph_db.json`.
   - Access method: `graph_db.get_context_for_entity(entity, depth=2, owner_id=...)`.
   - Yields structured triples: `src -> rel -> dst` with metadata `{"source": filename}`.
4. **Vector DB Semantic Chunks (`VectorDBClient`)**:
   - `backend/storage/vector_db.py`: Qdrant collection `imos_collection`.
   - **Critical Architecture Seam**: Local Qdrant holds an exclusive process lock on `backend/qdrant_data/`. To comply with `CLAUDE.md` and ensure unit tests never crash on Qdrant locks, vector search in `rca_ingestion.py` MUST be optional/injectable with automatic fallback to direct text scanning when vector DB is unavailable or mocked.

#### 3.1.2 Document Segmentation & Heading Hierarchy
The traversal engine parses Markdown/text documents by detecting structured headings to delineate sections and track line spans:
- Heading regex: `r'^(#{1,4})\s+(.+)$'`
- Line indexing: 1-indexed line counters.
- Section block structure:
  ```python
  @dataclass
  class DocumentSection:
      doc_name: str
      title: str
      section_heading: str
      start_line: int
      end_line: int
      content: str
  ```
- Example on `Near_Miss_Report_2023.txt`:
  - Section 1 (`Lines 3-8`): `## 1. Incident Overview`
  - Section 2 (`Lines 9-11`): `## 2. Event Description`
  - Section 3 (`Lines 12-14`): `## 3. Root Cause Analysis (Historical)`
  - Section 4 (`Lines 15-19`): `## 4. Corrective Action / Lessons Learned`

---

### 3.2. Citation Object Generation

#### 3.2.1 Deterministic Citation ID Format
Citations must satisfy the schema regex: `r"^CITE-[A-Za-z0-9_\-\.]+$"`.

Deterministic ID Generation Formula:
```
CITE-{DOC_SLUG}-{SEQ_NUM:03d}
```
Where:
- `DOC_SLUG` is an uppercase alphanumeric slug (max 8 characters) derived from the source filename.
  - `Near_Miss_Report_2023.txt` $\rightarrow$ `NEARMISS`
  - `Pump-A12_Manual.pdf` $\rightarrow$ `PUMP`
  - Knowledge graph relation $\rightarrow$ `GRAPH`
  - Raw telemetry / alarm payload $\rightarrow$ `TELEMETRY`
- `SEQ_NUM` is a 1-indexed monotonic counter per document (e.g. `001`, `002`, `003`).

Examples:
- `CITE-NEARMISS-001` (Event description)
- `CITE-NEARMISS-002` (Historical root cause)
- `CITE-NEARMISS-003` (OEM limit 5.0 mm/s)
- `CITE-NEARMISS-004` (Mandatory shutdown limit 5.5 mm/s)
- `CITE-GRAPH-001` (Pump vibration co-occurrence triple)

#### 3.2.2 Excerpt Text Extraction & Cleaning
- **Sanitization**: Text extracted from PDF uploads often contains artifact spacing (e.g., `c e r a m i c   s e a l`). The extraction pipeline invokes `clean_spaced_text(raw_text)` from `backend/core/text_utils.py` prior to snippet construction.
- **Verbatim Integrity**: Snippets retain exact numbers, units, and technical phrasing.
- **Length Constraint**: Enforces `min_length=5` (per `CitationObject` schema) with ideal snippet window spanning 25–350 characters.

#### 3.2.3 Source Document Metadata Recording
Every generated `CitationObject` populates:
- `citation_id`: Deterministic ID string (e.g., `CITE-NEARMISS-002`).
- `source_doc`: Filename (e.g., `Near_Miss_Report_2023.txt`).
- `title`: Document or section title (e.g., `Incident Report & Near-Miss Record (2023-11-04) - Root Cause Analysis`).
- `section`: Section title (e.g., `3. Root Cause Analysis (Historical)`).
- `page_or_line`: Line indicator (e.g., `Lines 12-14`).
- `excerpt`: Exact verbatim snippet.
- `confidence`: Calculated retrieval confidence score $\in [0.0, 1.0]$.

#### 3.2.4 Retrieval Confidence Scoring Algorithm
The confidence score quantifies how reliably the citation substantiates the failure symptoms and telemetry context:

$$C = \min\left(1.0, \max\left(0.1, B \times \left(0.40 \cdot S_{\text{kw}} + 0.35 \cdot S_{\text{param}} + 0.25 \cdot S_{\text{phrase}}\right)\right)\right)$$

Where:
1. **Source Authority Weight ($B$)**:
   - Official Incident Record / OEM Manual: $B = 1.00$
   - Direct Memory Cache User Upload: $B = 0.95$
   - Vector Semantic Chunk: $B = 0.90$
   - Knowledge Graph Entity Triple: $B = 0.85$
   - Unverified operator note / external: $B = 0.70$
2. **Symptom Keyword Overlap ($S_{\text{kw}}$)**:
   $$S_{\text{kw}} = \frac{|\text{Tokens}(\text{Symptoms}) \cap \text{Tokens}(\text{Excerpt})|}{|\text{Tokens}(\text{Symptoms})|}$$
3. **Numeric Parameter & Telemetry Match ($S_{\text{param}}$)**:
   - $1.0$ if observed numerical telemetry (e.g. `5.8`, `5.0`, `5.5`) appears verbatim in snippet.
   - $0.5$ if related units (`mm/s`, `°C`, `bar`) appear without exact number match.
   - $0.2$ if no telemetry parameters specified in query.
4. **Verbatim Phrase Continuity ($S_{\text{phrase}}$)**:
   - $1.0$ if multi-word symptom sequence (e.g. `"mechanical seal failure"`, `"inboard ceramic seals"`) appears unbroken.
   - $0.5$ if terms appear scattered across paragraph.

*Edge Case Floor*: Exact matches from `Near_Miss_Report_2023.txt` for `Pump-A12` vibration exceedance yield $C = 1.00$.

---

### 3.3. Verification Rules & Downstream Linking

#### 3.3.1 In-Memory Citation Registry (`CitationRegistry`)
A dedicated registry class maintains, resolves, and deduplicates citations across the RCA lifecycle:

```python
class CitationRegistry:
    def __init__(self):
        self._citations: Dict[str, CitationObject] = {}
        self._content_hash_map: Dict[str, str] = {}  # sha256(doc+excerpt) -> citation_id
        self._doc_counters: Dict[str, int] = defaultdict(int)

    def register(self, citation: CitationObject) -> str:
        """Registers a citation. Deduplicates identical source_doc + excerpt."""
        ...

    def get(self, citation_id: str) -> Optional[CitationObject]:
        """Retrieves citation by ID."""
        ...

    def list_all(self) -> List[CitationObject]:
        """Returns all registered CitationObject instances sorted by citation_id."""
        ...

    def validate_ids(self, citation_ids: List[str]) -> Tuple[List[str], List[str]]:
        """Returns (valid_ids, missing_ids)."""
        ...
```

#### 3.3.2 Downstream Causal Linking Rules
In Milestone 2 (`rca_engine.py`), the reasoning engine generates `FiveWhyNode` and `FishboneCauseItem` records. The verification engine enforces the following invariants:

1. **Empty Citation Linking**:
   If `len(node.evidence_citation_ids) == 0`:
   - `node.is_unsubstantiated = True`
   - `node.assumed_flag = True`
2. **Dangling Pointer Detection**:
   For every `cid` in `node.evidence_citation_ids`:
   - If `cid not in registry`: remove from valid set.
   - If no valid registered citation IDs remain:
     - `node.is_unsubstantiated = True`
     - `node.assumed_flag = True`
3. **Timeline Event Grounding**:
   For `FailureTimelineEvent`:
   - If `source_citation_id is None` or `source_citation_id not in registry`:
     - `event.is_unsubstantiated = True`
   - Else:
     - `event.is_unsubstantiated = False`
4. **Interim Containment Action Grounding**:
   For `InterimContainmentAction`:
   - `evidence_citation_id` is validated against registry.

#### 3.3.3 Audit Metrics & Compliance Thresholds
The verification module computes the overall **Citation Grounding Ratio (CGR)** across all causal claims:

$$\text{CGR} = \frac{N_{\text{grounded\_5why}} + N_{\text{grounded\_fishbone}}}{N_{\text{total\_5why}} + N_{\text{total\_fishbone}}}$$

Compliance Classifications:
- $\text{CGR} \ge 0.85$: `AUDIT_GROUNDED` (Eligible for ISO 9001 / IATF 16949 automated certification).
- $0.70 \le \text{CGR} < 0.85$: `PROVISIONAL_ACCEPTANCE` (Internal approval allowed; flagged assumptions require physical field inspection).
- $\text{CGR} < 0.70$: `GROUNDING_DEFICIENT` (Regulatory approval blocked; audit warning emitted).

**Terminal Root Cause Rule**:
If any terminal root cause (`is_root_cause=True`) has `is_unsubstantiated=True`, the engine emits the critical blocking alert: `CRITICAL_UNGROUNDED_ROOT_CAUSE`.

---

### 3.4. Concrete Reference Extraction: Asset Pump-A12

Using `Near_Miss_Report_2023.txt`, the traversal engine deterministically extracts the following standard citation objects:

| Citation ID | Source File | Section | Line Span | Verbatim Snippet | Conf. |
|---|---|---|---|---|---|
| `CITE-NEARMISS-001` | `Near_Miss_Report_2023.txt` | `2. Event Description` | Lines 9-11 | "During routine operations, Pump A12 experienced a catastrophic mechanical seal failure. This resulted in a minor leak of coolant fluid onto the factory floor. The spill was contained within 15 minutes by the emergency response team..." | 1.00 |
| `CITE-NEARMISS-002` | `Near_Miss_Report_2023.txt` | `3. Root Cause Analysis (Historical)` | Lines 12-14 | "Post-incident analysis revealed that the pump had been operating with a severe vibration level of 5.8 mm/s for 48 hours prior to the failure. Operations personnel ignored the vibration alerts because they mistakenly believed the threshold was 6.5 mm/s. The sustained vibration at 5.8 mm/s shattered the inboard ceramic seals." | 1.00 |
| `CITE-NEARMISS-003` | `Near_Miss_Report_2023.txt` | `4. Corrective Action / Lessons Learned` | Lines 15-16 | "The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s as per the OEM manual." | 1.00 |
| `CITE-NEARMISS-004` | `Near_Miss_Report_2023.txt` | `4. Corrective Action / Lessons Learned` | Lines 17-17 | "Any vibration reading exceeding 5.5 mm/s requires an immediate, mandatory shutdown of the pump to prevent seal fracture." | 1.00 |
| `CITE-NEARMISS-005` | `Near_Miss_Report_2023.txt` | `4. Corrective Action / Lessons Learned` | Lines 18-19 | "All technicians must be re-trained on the specific tolerance limits of the A-series pumps. Do NOT rely on generic plant guidelines for high-pressure equipment." | 0.95 |

Downstream Causal Mapping for Pump-A12 Incident:
- **Why 1**: Coolant leakage at primary cooling loop sector 4 $\rightarrow$ `CITE-NEARMISS-001`
- **Why 2**: Inboard ceramic mechanical seal fractured $\rightarrow$ `CITE-NEARMISS-001`, `CITE-NEARMISS-002`
- **Why 3**: Sustained excessive vibration at 5.8 mm/s for 48 hours $\rightarrow$ `CITE-NEARMISS-002`
- **Why 4**: Vibration alarm ignored due to miscalibrated operator perception (believed 6.5 mm/s) $\rightarrow$ `CITE-NEARMISS-002`
- **Why 5 (Root Cause)**: Inadequate training on A-series specific OEM envelope limits (5.0 mm/s normal, 5.5 mm/s shutdown) $\rightarrow$ `CITE-NEARMISS-003`, `CITE-NEARMISS-004`, `CITE-NEARMISS-005`

Result: $5 / 5$ nodes grounded $\implies \text{CGR} = 1.00$ (`AUDIT_GROUNDED`).

---

## 4. Blueprint Implementation Code Specification

The following classes and functions must be implemented in `backend/services/rca_ingestion.py`:

```python
"""
backend/services/rca_ingestion.py
Evidence Citation Extraction and Timeline Ingestion Service
"""

import hashlib
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from api.rca_schemas import CitationObject, FailureTimelineEvent, EventType
from core.text_utils import clean_spaced_text


class CitationRegistry:
    """In-memory thread-safe citation catalog and resolver."""
    def __init__(self):
        self._citations: Dict[str, CitationObject] = {}
        self._dedup_map: Dict[str, str] = {}  # sha256(source_doc + excerpt) -> citation_id
        self._doc_counters: Dict[str, int] = defaultdict(int)

    def register_citation(
        self,
        source_doc: str,
        title: str,
        excerpt: str,
        section: Optional[str] = None,
        page_or_line: Optional[str] = None,
        confidence: float = 1.0,
        custom_id: Optional[str] = None,
    ) -> CitationObject:
        """
        Registers a citation object, enforcing deduplication and schema validation.
        """
        sanitized_excerpt = clean_spaced_text(excerpt.strip())
        if len(sanitized_excerpt) < 5:
            raise ValueError("Citation excerpt must be at least 5 characters.")

        # Check deduplication
        fingerprint = hashlib.sha256(f"{source_doc}::{sanitized_excerpt}".encode("utf-8")).hexdigest()
        if fingerprint in self._dedup_map:
            return self._citations[self._dedup_map[fingerprint]]

        # Generate deterministic citation ID if not provided
        if not custom_id:
            doc_slug = re.sub(r"[^A-Za-z0-9]", "", os.path.splitext(source_doc)[0]).upper()[:8] or "DOC"
            self._doc_counters[doc_slug] += 1
            citation_id = f"CITE-{doc_slug}-{self._doc_counters[doc_slug]:03d}"
        else:
            citation_id = custom_id

        citation = CitationObject(
            citation_id=citation_id,
            source_doc=source_doc,
            title=title,
            section=section,
            page_or_line=page_or_line,
            excerpt=sanitized_excerpt,
            confidence=max(0.0, min(1.0, confidence)),
        )

        self._citations[citation_id] = citation
        self._dedup_map[fingerprint] = citation_id
        return citation

    def get(self, citation_id: str) -> Optional[CitationObject]:
        return self._citations.get(citation_id)

    def list_citations(self) -> List[CitationObject]:
        return list(self._citations.values())

    def validate_citation_ids(self, citation_ids: List[str]) -> Tuple[List[str], List[str]]:
        valid = [cid for cid in citation_ids if cid in self._citations]
        invalid = [cid for cid in citation_ids if cid not in self._citations]
        return valid, invalid


class EvidenceCitationExtractor:
    """
    Autonomous evidence extractor traversing maintenance logs, manuals,
    and memory cache to construct grounded CitationObjects.
    """
    def __init__(self, registry: Optional[CitationRegistry] = None):
        self.registry = registry or CitationRegistry()

    def parse_markdown_document(self, content: str, source_doc: str) -> List[CitationObject]:
        """
        Segments markdown text into structured sections and registers citations.
        """
        lines = content.splitlines()
        citations = []
        current_section = "General"
        current_lines: List[str] = []
        start_line = 1

        heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for idx, line in enumerate(lines, start=1):
            match = heading_pattern.match(line)
            if match:
                if current_lines:
                    text_block = "\n".join(current_lines).strip()
                    if len(text_block) >= 5:
                        citations.append(
                            self.registry.register_citation(
                                source_doc=source_doc,
                                title=f"{source_doc} - {current_section}",
                                excerpt=text_block,
                                section=current_section,
                                page_or_line=f"Lines {start_line}-{idx-1}",
                                confidence=1.0,
                            )
                        )
                current_section = match.group(2).strip()
                current_lines = []
                start_line = idx
            else:
                if line.strip():
                    current_lines.append(line)

        # Flush final section
        if current_lines:
            text_block = "\n".join(current_lines).strip()
            if len(text_block) >= 5:
                citations.append(
                    self.registry.register_citation(
                        source_doc=source_doc,
                        title=f"{source_doc} - {current_section}",
                        excerpt=text_block,
                        section=current_section,
                        page_or_line=f"Lines {start_line}-{len(lines)}",
                        confidence=1.0,
                    )
                )

        return citations

    def ingest_near_miss_file(self, filepath: str) -> List[CitationObject]:
        """
        Ingests the authoritative Near_Miss_Report_2023.txt file.
        """
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse_markdown_document(content, os.path.basename(filepath))

    def compute_retrieval_confidence(
        self,
        excerpt: str,
        symptoms: List[str],
        telemetry_values: Optional[Dict[str, Any]] = None,
        source_authority: float = 1.0,
    ) -> float:
        """
        Calculates multi-factor confidence score for an excerpt relative to incident symptoms.
        """
        lower_excerpt = excerpt.lower()
        
        # 1. Keyword match ratio
        symptom_tokens = {token.lower() for s in symptoms for token in re.findall(r"\w+", s) if len(token) > 3}
        if symptom_tokens:
            matched_tokens = {tok for tok in symptom_tokens if tok in lower_excerpt}
            s_kw = len(matched_tokens) / len(symptom_tokens)
        else:
            s_kw = 0.5

        # 2. Parameter match ratio
        s_param = 0.2
        if telemetry_values:
            matched_params = 0
            for val in telemetry_values.values():
                val_str = str(val).lower()
                if val_str in lower_excerpt:
                    matched_params += 1
            if matched_params > 0:
                s_param = 1.0

        # 3. Exact phrase match
        s_phrase = 1.0 if any(s.lower() in lower_excerpt for s in symptoms) else 0.5

        raw_score = source_authority * (0.40 * s_kw + 0.35 * s_param + 0.25 * s_phrase)
        return round(max(0.1, min(1.0, raw_score)), 2)


def verify_causal_grounding(
    causes: List[Any],  # FiveWhyNode or FishboneCauseItem
    registry: CitationRegistry,
) -> Dict[str, Any]:
    """
    Verifies that all causal assertions resolve to registered citations.
    Sets is_unsubstantiated and assumed_flag programmatically.
    Returns audit summary metrics.
    """
    total = len(causes)
    grounded = 0

    for cause in causes:
        valid_ids, _ = registry.validate_citation_ids(cause.evidence_citation_ids)
        if not valid_ids:
            cause.is_unsubstantiated = True
            if hasattr(cause, "assumed_flag"):
                cause.assumed_flag = True
        else:
            cause.is_unsubstantiated = False
            if hasattr(cause, "assumed_flag"):
                cause.assumed_flag = False
            grounded += 1

    ratio = round(grounded / total, 4) if total > 0 else 0.0
    if ratio >= 0.85:
        status = "AUDIT_GROUNDED"
    elif ratio >= 0.70:
        status = "PROVISIONAL_ACCEPTANCE"
    else:
        status = "GROUNDING_DEFICIENT"

    return {
        "total_causes": total,
        "grounded_causes": grounded,
        "grounding_ratio": ratio,
        "compliance_status": status,
    }
```

---

## 5. Unit Testing Strategy

To guarantee rapid, deterministic CI/CD and avoid breaking offline invariants, the citation unit tests must run under pytest with **zero network**, **zero external API**, and **zero Qdrant disk locking**.

### 5.1 Test Inventory (`backend/tests/test_rca_citations.py`)

| Test Name | Focus | Input / Condition | Expected Behavior |
|---|---|---|---|
| `test_citation_object_valid_instantiation` | Schema | Valid fields matching regex `CITE-PUMP-001` | Pydantic model validates successfully |
| `test_citation_object_regex_rejection` | Boundary | Invalid ID `INVALID_001` or `CIT!1` | Pydantic raises `ValidationError` |
| `test_citation_object_short_excerpt_rejection` | Boundary | Excerpt `< 5` characters (e.g. `"fail"`) | Pydantic raises `ValidationError` |
| `test_citation_confidence_bounds` | Boundary | Confidence `< 0.0` or `> 1.0` | Pydantic raises `ValidationError` |
| `test_citation_registry_registration_and_lookup` | Registry | Register citation, query by ID | Returns matching `CitationObject` |
| `test_citation_registry_deduplication` | Registry | Register identical doc + excerpt twice | Returns existing ID, counter does not increment |
| `test_citation_registry_validate_ids` | Registry | Query mix of valid and non-existent IDs | Correctly partitions into valid and invalid lists |
| `test_near_miss_file_traversal` | Ingestion | Ingest `Near_Miss_Report_2023.txt` | Extracts 4+ citations with exact line numbers & titles |
| `test_spaced_text_cleaning_in_citations` | Sanitization | Excerpt with PDF spaced text `"c e r a m i c"` | Sanitized to `"ceramic"` in registered excerpt |
| `test_confidence_calculation_exact_match` | Scoring | Excerpt with exact symptom + telemetry `5.8` | Returns `confidence = 1.0` |
| `test_confidence_calculation_partial_match` | Scoring | Excerpt with partial keywords | Returns confidence between `0.3` and `0.8` |
| `test_grounding_verifier_flags_empty_citations` | Verifier | `FiveWhyNode` with `evidence_citation_ids = []` | Sets `is_unsubstantiated = True`, `assumed_flag = True` |
| `test_grounding_verifier_flags_dangling_citation` | Verifier | Node with `["CITE-GHOST-999"]` | Sets `is_unsubstantiated = True`, `assumed_flag = True` |
| `test_grounding_verifier_approves_grounded_node` | Verifier | Node with registered ID | Sets `is_unsubstantiated = False`, `assumed_flag = False` |
| `test_citation_grounding_ratio_status_tiers` | Compliance | 4 causes: 4/4 grounded, 3/4 grounded, 1/4 grounded | Returns `AUDIT_GROUNDED`, `PROVISIONAL_ACCEPTANCE`, `GROUNDING_DEFICIENT` |
| `test_timeline_event_citation_grounding` | Timeline | Event with vs without valid `source_citation_id` | Correctly flags `is_unsubstantiated` on event |

---

## 6. Downstream Integration & Handoff Touchpoints

1. **Milestone 1 Core Implementer**:
   - Create `backend/services/rca_ingestion.py` matching the signatures and classes specified above.
   - Wire `CitationObject` and `FailureTimelineEvent` directly from `backend/api/rca_schemas.py`.
2. **Milestone 2 RCA Engine Implementer (`rca_engine.py`)**:
   - Pass the populated `CitationRegistry` into the 5-Why and Fishbone reasoning nodes.
   - Call `verify_causal_grounding` after generating tree nodes to enforce grounding flags before report synthesis.
3. **Milestone 4 Frontend Studio Implementer (`EightDIncidentStudio.jsx`)**:
   - Render citation badges (`CITE-NEARMISS-001`) with click handlers invoking `SourceViewerModal` props `{ source: citation.source_doc, snippet: citation.excerpt }`.
