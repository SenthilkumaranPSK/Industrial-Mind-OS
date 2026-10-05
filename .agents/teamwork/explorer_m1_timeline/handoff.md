# Handoff Report: Chronological Timeline Event Extraction Blueprint

**Subagent**: M1 Timeline Extractor Explorer (`explorer_m1_timeline`)  
**Recipient**: Milestone 1 Orchestrator & Implementer Agent (`ef889b9f-7189-4139-bdab-296efd4f52ff`)  
**Handoff Type**: Hard (Task Complete)  
**Date**: 2026-10-05  

---

## 1. Observation

1. **Document Contracts**:
   - `ORIGINAL_REQUEST.md` line 13-14:
     > "### R1. Incident Evidence & Timeline Extraction
     > An RCA ingestion workflow that accepts failure symptoms, timestamps, and equipment tags, then autonomously traverses internal asset manuals, maintenance logs, and the knowledge graph to compile an authoritative chronological event log with verifiable source citations."
   - `PROJECT.md` line 55:
     > "`TimelineEvent`: `event_id: str`, `timestamp: str`, `event_type: str` (TELEMETRY_ALARM, OPERATOR_ACTION, SYSTEM_FAILURE, MAINTENANCE_LOG), `description: str`, `equipment_tag: str`, `citation_ids: List[str]`, `parameters: Dict[str, Any]`"
   - `PROJECT.md` line 98-99:
     > "- `backend/api/rca_schemas.py` (Owned by M1): Pydantic v2 schemas for all 8D disciplines, citations, timelines, and analysis requests.
     > - `backend/services/rca_ingestion.py` (Owned by M1): Evidence ingestion, citation extraction, and chronological timeline reconstruction."
   - `spec_miner_survey_domain_2/spec_report.md` line 238-265:
     > Defines `FailureTimelineEvent` with `event_id`, `timestamp: datetime`, `event_type: EventType`, `description`, `equipment_tag`, `telemetry_values`, `source_citation_id`, and `is_unsubstantiated`.

2. **Sample Incident Evidence**:
   - `Near_Miss_Report_2023.txt` lines 1-19:
     - Equipment Tag: `Pump-A12` (Primary Cooling Loop, Sector 4).
     - Date: `November 4, 2023`.
     - 48-hour prior vibration: `5.8 mm/s`.
     - Operator action: Ignored vibration alerts mistakenly believing threshold was `6.5 mm/s`.
     - Catastrophic event: Shattered inboard ceramic seals, coolant fluid leak onto factory floor.
     - Containment action: Contained within `15 minutes` by emergency response team.
     - OEM manual limit: strictly `5.0 mm/s`.
     - Mandatory shutdown protocol: any vibration exceeding `5.5 mm/s`.

3. **Backend Infrastructure & Testing**:
   - `backend/pytest.ini` lines 1-4: `pythonpath = .`, `testpaths = tests`.
   - `backend/core/text_utils.py` lines 17-31: `clean_spaced_text(text: str)` cleans spaced-out PDF artifacts.
   - `CLAUDE.md` line 37: Pytest suite is deliberately free of LLM, network, or Qdrant locks so it runs completely offline.

---

## 2. Logic Chain

1. **Schema Harmonization**:
   - From Observation 1, `PROJECT.md` establishes `TimelineEvent` with string timestamps and parameters dict, while `spec_report.md` establishes typed datetime and telemetry values.
   - Therefore, `TimelineEvent` in `backend/api/rca_schemas.py` must support ISO-8601 string representations, `parameters: Dict[str, Any]` for sensor values, `citation_ids: List[str]`, and `is_unsubstantiated: bool` for evidence grounding.

2. **Temporal Reconstruction Logic**:
   - From Observation 2, industrial reports intermix absolute dates ("November 4, 2023"), backward offsets ("48 hours prior"), forward offsets ("contained within 15 minutes"), and post-incident reviews.
   - Therefore, the timeline extractor must implement relative temporal anchor arithmetic:
     - Anchor: $T_0 = \text{incident\_timestamp}$ (`2023-11-04T08:00:00Z`).
     - Vibration onset: $T_0 - 48\text{h} = \text{2023-11-02T08:00:00Z}$ (`TELEMETRY_ALARM`).
     - Alert dismissed: $T_0 - 47\text{h} = \text{2023-11-02T09:00:00Z}$ (`OPERATOR_ACTION`).
     - Seal fracture: $T_0 = \text{2023-11-04T08:00:00Z}$ (`SYSTEM_FAILURE`).
     - Containment: $T_0 + 15\text{m} = \text{2023-11-04T08:15:00Z}$ (`OPERATOR_ACTION`).
     - Inspection: $T_0 + 4\text{h} = \text{2023-11-04T12:00:00Z}$ (`MAINTENANCE_LOG`).

3. **Telemetry Excursion Logic**:
   - From Observation 2, `Pump-A12` has OEM envelope max $5.0\text{ mm/s}$ and trip threshold $5.5\text{ mm/s}$.
   - Telemetry reading of $5.8\text{ mm/s}$ gives $\Delta\% = \frac{5.8 - 5.0}{5.0} \times 100 = \mathbf{+16.0\%}$.
   - Because $5.8 > 5.5$, the engine flags `is_trip_exceeded=True` and tags the event as `CRITICAL` / `TELEMETRY_ALARM`.

4. **Event Classification & Precedence**:
   - Multiple keywords can co-occur in one sentence.
   - Therefore, a deterministic precedence hierarchy is established:
     - Active human containment / omission $\rightarrow$ `OPERATOR_ACTION`
     - Physical component destruction $\rightarrow$ `SYSTEM_FAILURE`
     - Sensor alerts / excursions $\rightarrow$ `TELEMETRY_ALARM`
     - Routine logs / inspections $\rightarrow$ `MAINTENANCE_LOG`

5. **Fault Tolerance & Sorting**:
   - If telemetry logs arrive out-of-order, or if timestamps are missing, the engine sorts strictly in ascending order using ISO timestamps with a secondary tie-breaker on `event_id`.
   - If an event lacks citations, `is_unsubstantiated` is set to `True` without failing validation.

---

## 3. Caveats

1. **LLM Extraction Dependency**: In future iterations (Milestone 2/3), an LLM extraction pass may assist with ambiguous text; however, the primary timeline extraction engine in `backend/services/rca_ingestion.py` is designed to be 100% deterministic, offline, and regex-driven to guarantee zero test flakiness and high execution speed.
2. **Equipment Envelopes**: While `Pump-A12` thresholds are explicitly known from `Near_Miss_Report_2023.txt`, novel equipment tags will fallback to `DEFAULT_PUMP` envelopes unless overridden in input parameters.
3. **No Project Source Modification**: In accordance with the read-only explorer role, no files were modified in `backend/`. All blueprints and code structures are documented in `analysis.md` and this handoff.

---

## 4. Conclusion

The timeline extraction engine architecture for `backend/services/rca_ingestion.py` has been fully formulated and specified:
1. `TimelineExtractor` provides the canonical entry point `reconstruct_timeline(equipment_tag, raw_text, telemetry_logs, incident_timestamp, citations)`.
2. It parses both free text and telemetry streams, extracts physical parameters (`vibration_mm_s`, `temperature_c`, `pressure_bar`, `rpm`), computes threshold excursions and deviation percentages against OEM boundaries, classifies events into four mandatory types, and sorts them chronologically.
3. It maps `Near_Miss_Report_2023.txt` into a 5-event chronological sequence ($T - 48\text{h} \rightarrow T - 47\text{h} \rightarrow T_0 \rightarrow T + 15\text{m} \rightarrow T + 4\text{h}$) with $+16.0\%$ vibration deviation.
4. The comprehensive unit testing plan in `backend/tests/test_rca_ingestion.py` (11 unit tests across normal, out-of-order, and missing-timestamp conditions) provides an offline verification harness.

---

## 5. Verification Method

To verify the implementation once coded by the implementer agent:
1. **Source Code Inspection**:
   - Inspect `backend/services/rca_ingestion.py` for `TimelineExtractor` and `reconstruct_timeline`.
   - Inspect `backend/tests/test_rca_ingestion.py` for test cases `test_reconstruct_timeline_near_miss_ordering`, `test_telemetry_threshold_excursion_deviation`, `test_out_of_order_telemetry_stream_sorting`, and `test_missing_timestamp_fallback_behavior`.
2. **Execute Project Test Command**:
   ```bash
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\backend"
   python -m pytest tests/test_rca_ingestion.py -v
   ```
3. **Invalidation Conditions**:
   - If events in `Near_Miss_Report_2023.txt` are not sorted strictly in ascending order ($T - 48\text{h}$ before $T_0$).
   - If deviation percentage for $5.8\text{ mm/s}$ vibration on `Pump-A12` is not $+16.0\%$.
   - If out-of-order logs fail to sort chronologically.
   - If missing or invalid timestamps cause unhandled exceptions or test crashes.
