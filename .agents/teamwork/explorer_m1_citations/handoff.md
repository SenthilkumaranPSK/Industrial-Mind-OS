# Handoff Report: Verifiable Evidence Citation Extraction & Source Document Resolution

**Agent**: M1 Citation Explorer (`explorer_m1_citations`)  
**Parent Conversation ID**: `ef889b9f-7189-4139-bdab-296efd4f52ff`  
**Handoff Type**: Hard (Investigation & Blueprint Formulation Complete)  
**Date**: 2026-10-05  

---

## 1. Observation

1. **Original Incident Record File**:
   - Inspected `Near_Miss_Report_2023.txt` at workspace root (`C:\000 MINE\My Codzz\Industrial Mind OS\Near_Miss_Report_2023.txt`).
   - Line 1: `# INCIDENT REPORT & NEAR-MISS RECORD (2023-11-04)`
   - Lines 3–7: `## 1. Incident Overview` with `Equipment Tag: Pump-A12`, `Location: Primary Cooling Loop, Sector 4`.
   - Lines 9–10: `## 2. Event Description`: `"During routine operations, Pump A12 experienced a catastrophic mechanical seal failure. This resulted in a minor leak of coolant fluid onto the factory floor. The spill was contained within 15 minutes by the emergency response team, preventing it from reaching the environmental drainage system."`
   - Lines 12–13: `## 3. Root Cause Analysis (Historical)`: `"Post-incident analysis revealed that the pump had been operating with a severe vibration level of 5.8 mm/s for 48 hours prior to the failure. Operations personnel ignored the vibration alerts because they mistakenly believed the threshold was 6.5 mm/s. The sustained vibration at 5.8 mm/s shattered the inboard ceramic seals."`
   - Lines 15–18: `## 4. Corrective Action / Lessons Learned`:
     - Line 16: `"- **Strict Adherence to Limits**: The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s as per the OEM manual."`
     - Line 17: `"- **Mandatory Shutdown Protocol**: Any vibration reading exceeding 5.5 mm/s requires an immediate, mandatory shutdown of the pump to prevent seal fracture."`
     - Line 18: `"- **Training**: All technicians must be re-trained on the specific tolerance limits of the A-series pumps."`

2. **Existing Storage Architecture & Concurrency Locks**:
   - `CLAUDE.md` Lines 37 & 80: Documented that `VectorDBClient` in `backend/storage/vector_db.py` uses local disk-persisted mode (`QdrantClient(path=...)`), which holds an **exclusive filesystem lock** on `backend/qdrant_data/`. The pytest suite is intentionally designed around seams that bypass Qdrant and LLM network calls to prevent lock collisions and test flakiness.
   - `backend/storage/memory_cache.py` Lines 11–98: `DirectMemoryCache` stores `{filename: {"content": str, "owner_id": str | None}}` in `backend/memory_cache.json`.
   - `backend/storage/graph_db.py` Lines 12–180: `GraphDBClient` maintains a NetworkX `MultiDiGraph` with methods `get_context_for_entity(entity, depth=2, file_filter=..., owner_id=...)` returning `[{"source": f"Graph: {edge_data.get('source')}", "content": f"{src} -> {rel} -> {dst}"}]`.

3. **Text Sanitization Helper**:
   - `backend/core/text_utils.py` Lines 17–31: `clean_spaced_text(text: str)` uses regex `_SPACED_OUT_PATTERN = re.compile(r'\b(?:[A-Za-z][ \t]){4,}[A-Za-z]\b')` to detect and repair PDF-spaced artifacts (e.g., `"c e r a m i c"` $\rightarrow$ `"ceramic"`).

4. **Domain Specification Requirements**:
   - `spec_miner_survey_domain_2/spec_report.md` Section 4 Lines 217–233: `CitationObject` schema:
     ```python
     class CitationObject(BaseModel):
         citation_id: str = Field(..., pattern=r"^CITE-[A-Za-z0-9_\-\.]+$")
         source_doc: str
         title: str
         section: Optional[str] = None
         page_or_line: Optional[str] = None
         excerpt: str = Field(..., min_length=5)
         confidence: float = Field(default=1.0, ge=0.0, le=1.0)
     ```
   - Section 5 Lines 616–654: Mandatory grounding invariant requires every `FiveWhyNode` and `FishboneCauseItem` to resolve to valid citation IDs in the catalog; missing or broken IDs must set `is_unsubstantiated = True` and `assumed_flag = True`. Citation Grounding Ratio (CGR) $\ge 0.85$ achieves `AUDIT_GROUNDED`.

5. **Frontend Citation Integration**:
   - `frontend/src/components/SourceViewerModal.jsx` Lines 1–77: Consumes source citation objects with props `{ source, onClose }`, displaying `source.source` (document title), `source.snippet` (verbatim excerpt), and metadata context.

---

## 2. Logic Chain

1. **Deterministic Citation Identifiers**:
   - From Observation 4, the schema pattern is `r"^CITE-[A-Za-z0-9_\-\.]+$"`.
   - Generating IDs using the deterministic pattern `CITE-{DOC_SLUG}-{SEQ_NUM:03d}` (e.g. `CITE-NEARMISS-001`, `CITE-NEARMISS-002`) guarantees idempotent re-indexing, clean test assertions, and strict adherence to the regex constraint.

2. **Source Traversal & Multi-Modal Resolution**:
   - From Observations 1 & 2, evidence resides across local filesystem documents (`Near_Miss_Report_2023.txt`), memory cache (`DirectMemoryCache`), and the knowledge graph (`GraphDBClient`).
   - Using heading-based segmentation (`r'^(#{1,4})\s+(.+)$'`), the traversal engine accurately extracts section titles and maps line boundaries (e.g., `"Lines 12-14"`).
   - Knowledge graph triples (`src -> rel -> dst`) are wrapped as synthetic structural citations with `confidence = 0.85`.

3. **Excerpt Sanitization**:
   - From Observation 3, raw text extracted from uploaded PDFs contains spaced-out characters. Passing excerpts through `clean_spaced_text` guarantees clean excerpts before registering `CitationObject` instances.

4. **Seam-Isolated Vector Traversal for CI/CD**:
   - From Observation 2, Qdrant takes an exclusive file lock.
   - Therefore, `rca_ingestion.py` must decouple vector querying from text extraction: direct markdown parsing, memory cache lookup, and graph traversal operate completely in memory without booting the Qdrant local client, ensuring test suites remain 100% reliable and offline.

5. **Downstream Grounding Verification**:
   - From Observation 4, downstream causal analysis requires validating all `evidence_citation_ids` against the `CitationRegistry`.
   - If a node contains an empty list or references an unregistered citation ID, the engine programmatically sets `is_unsubstantiated = True` and `assumed_flag = True`, and computes the Citation Grounding Ratio (CGR). Any ungrounded terminal root cause triggers `CRITICAL_UNGROUNDED_ROOT_CAUSE`.

---

## 3. Caveats

1. **Qdrant Vector DB Concurrency**: If a live backend process is actively running in background, any test attempting to instantiate a local `VectorDBClient` on `backend/qdrant_data/` will fail due to the SQLite/disk lock. All citation unit tests must inject mock vector contexts or rely on direct text traversal.
2. **Scope Isolation**: Multi-tenant documents in `DirectMemoryCache` and `GraphDBClient` enforce `owner_id` filtering; un-owned legacy records (`owner_id = None`) like `Near_Miss_Report_2023.txt` are globally visible by design.
3. **No Project Code Modification**: In accordance with the explorer archetype rules, no changes have been committed to `backend/services/` or `backend/api/`. The full implementation code is documented in `analysis.md` for the M1 implementer.

---

## 4. Conclusion

The blueprint for verifiable evidence citation extraction and source document resolution in `backend/services/rca_ingestion.py` is fully defined and documented in `analysis.md`:
1. `CitationRegistry` manages in-memory registration, SHA-256 deduplication, deterministic ID generation (`CITE-{SLUG}-{SEQ:03d}`), and ID validation.
2. `EvidenceCitationExtractor` parses structured Markdown files (including `Near_Miss_Report_2023.txt`), extracts verbatim excerpts with line numbers, sanitizes PDF spaced text, and computes multi-factor confidence scores.
3. `verify_causal_grounding` enforces downstream linking invariants, flagging ungrounded or dangling causal nodes as `is_unsubstantiated=True`, and evaluating ISO/IATF compliance tiers.
4. A 16-point unit test inventory is specified to verify schema bounds, citation extraction, excerpt matching, confidence calculation, and grounding flags without external dependencies.

---

## 5. Verification Method

To independently verify the citation blueprint and downstream readiness:

1. **Verify Blueprint File**:
   - Confirm existence and completeness of `analysis.md`:
     ```powershell
     Get-Item "C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m1_citations\analysis.md"
     ```
2. **Verify Reference File Integrity**:
   - Confirm that `Near_Miss_Report_2023.txt` contains the cited sections:
     ```powershell
     Select-String -Path "C:\000 MINE\My Codzz\Industrial Mind OS\Near_Miss_Report_2023.txt" -Pattern "5.8 mm/s", "5.0 mm/s", "5.5 mm/s"
     ```
3. **Downstream Unit Test Command** (once implemented by M1 core implementer):
   ```powershell
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\backend"
   .\venv\Scripts\pytest.exe tests/test_rca_citations.py -v
   ```
4. **Invalidation Conditions**:
   - If `CitationObject.citation_id` regex pattern is modified in `backend/api/rca_schemas.py` without updating `CITE-{SLUG}-{SEQ:03d}`.
   - If `Near_Miss_Report_2023.txt` is moved or restructured.
