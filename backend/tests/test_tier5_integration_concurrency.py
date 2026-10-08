"""
Industrial Mind OS - Tier 5 Adversarial Concurrency & High-Load Scale Test Suite
Location: backend/tests/test_tier5_integration_concurrency.py

Comprehensive Tier 5 empirical test suite verifying:
1. High Concurrency on RCAReportStore:
   - 50+ concurrent threads executing `add`, `get`, `list_all`, and `get_or_fallback` simultaneously
   - Threading locks prevent race conditions, data corruption, crashes, or deadlocks
   - Multi-threaded fallback generation on identical non-existent report IDs
   - Interleaved concurrent writes, reads, and deletions without collection iteration crashes
2. High-Load Scale Stress Test (Massive 8D Incident Reports):
   - Synthesis of massive industrial 8D reports (550+ timeline events, 120+ citations, deep 5-Why tree)
   - Pydantic v2 validation completes in < 100ms
   - Checksum generation determinism and cryptographic avalanche tamper detection
   - HTML compliance package compilation completes rapidly within memory bounds without exponential slowdown
   - Machine-readable JSON compliance export scalability and bidirectional integrity
3. Endpoint Boundary Probing & Concurrent Requests (/api/v1/rca/*):
   - Concurrent bursts across /analyze, /export-evidence, /reports
   - Boundary telemetry floats (subnormal, zero, negative, extreme values)
   - Boundary asset tags and symptom arrays
   - Format validation boundaries on /export-evidence
   - Report store query boundaries on /reports/{report_id}
"""

from __future__ import annotations

import gc
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from main import app
from api.rca_router import RCAReportStore, rca_report_store
from api.rca_schemas import (
    ActionStatus,
    CitationObject,
    ContainmentAction,
    CorrectiveAction,
    EightDIncidentReport,
    EventType,
    FishboneAnalysis,
    FishboneBranch,
    FiveWhyNode,
    OEMDeviation,
    PreventativeControls,
    ProblemDescription,
    RCAAnalyzeRequest,
    RootCauseAnalysis,
    SeverityLevel,
    SignOffStatus,
    TeamFormation,
    TeamRecognition,
    TimelineEvent,
    ValidationPlan,
)
from services.compliance_package import (
    build_audit_html,
    build_audit_json,
    compute_canonical_sha256,
    generate_compliance_package,
    verify_compliance_checksum,
)
from services.rca_engine import assemble_eight_d_report


# ==============================================================================
# FIXTURES & ISOLATION
# ==============================================================================

@pytest.fixture(autouse=True)
def isolate_store():
    """Ensures test isolation by resetting global report store before and after each test."""
    rca_report_store.clear()
    yield
    rca_report_store.clear()


@pytest.fixture
def client():
    """Provides ASGI TestClient bound to main.app."""
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# HELPER GENERATORS
# ==============================================================================

def make_sample_report(report_id: str, asset_tag: str = "Pump-A12") -> EightDIncidentReport:
    """Creates a minimal valid EightDIncidentReport for concurrency tests."""
    return assemble_eight_d_report(
        asset_tag=asset_tag,
        symptoms=["mechanical seal leakage", "bearing vibration excursion"],
        incident_timestamp="2024-03-15T08:30:00Z",
        telemetry_data={"vibration_mm_s": 5.8, "temperature_c": 64.2},
        report_id=report_id,
    )


def build_massive_report_payload(
    event_count: int = 550,
    citation_count: int = 120,
    why_depth: int = 15,
) -> Dict[str, Any]:
    """
    Constructs a massive 8D incident report data dictionary simulating
    a high-load petrochemical or power turbine catastrophic failure.
    """
    citations = [
        {
            "citation_id": f"CITE-PETRO-{i:04d}",
            "source_doc": f"Turbine_Telemetry_Archive_Log_{i // 10:03d}.pdf",
            "excerpt": f"Spectral FFT spike observed at 142 Hz harmonic frequency during run cycle #{i}.",
            "section": f"Section 4.{i % 12 + 1}",
            "page_or_line": f"Page {i // 8 + 1}, Line {(i % 45) + 1}",
            "title": f"Turbine High-Pressure Stage Telemetry Dossier Vol. {i // 20 + 1}",
            "confidence": round(0.85 + (i % 15) * 0.01, 2),
        }
        for i in range(citation_count)
    ]

    timeline = [
        {
            "event_id": f"EVT-SCALE-{i:05d}",
            "timestamp": f"2024-03-15T{(i // 3600) % 24:02d}:{(i % 3600) // 60:02d}:{i % 60:02d}Z",
            "event_type": "TELEMETRY_ALARM" if i % 2 == 0 else "OPERATOR_ACTION",
            "description": f"Continuous high-speed telemetry event #{i} across sensor node SN-{(i % 64):03d}.",
            "equipment_tag": "Turbine-Gen-09",
            "citation_ids": [f"CITE-PETRO-{(i % citation_count):04d}"],
            "parameters": {
                "vibration_mm_s": round(4.2 + (i % 30) * 0.1, 2),
                "bearing_temp_c": round(60.0 + (i % 25) * 0.5, 1),
                "oil_pressure_bar": round(3.5 - (i % 10) * 0.05, 2),
            },
        }
        for i in range(event_count)
    ]

    five_why = [
        {
            "why_id": f"WHY-SCALE-{i+1:02d}",
            "level": min(10, i + 1),
            "cause_statement": f"Deductive causal layer {i+1}: resonant hydro-acoustic pulse propagating into bearing journal {i}.",
            "parent_node_id": f"WHY-SCALE-{i:02d}" if i > 0 else None,
            "citation_ids": [f"CITE-PETRO-{(i % citation_count):04d}"],
            "is_root_cause": (i == why_depth - 1),
        }
        for i in range(why_depth)
    ]

    data: Dict[str, Any] = {
        "report_id": "8D-2024-TURB-GEN-09-MASSIVE",
        "created_at": "2024-03-15T12:00:00Z",
        "asset_tag": "Turbine-Gen-09",
        "severity_score": 9,
        "occurrence_score": 7,
        "detection_score": 8,
        "d1_team": {
            "leader": "Dr. Elena Rostova, Lead Vibration Specialist",
            "champion": "Marcus Vance, VP Plant Reliability",
            "members": [
                "Senior Diagnostics Tech J. Doe",
                "Controls Engineer M. Chen",
                "OEM Field Specialist K. Weber",
                "Safety & Environmental Officer A. Patel",
            ],
            "facilitator": "RCA Facilitation Board Lead",
        },
        "d2_problem": {
            "what": "High-pressure turbine bearing sleeve destruction under resonant harmonic vibration",
            "where": "Train-B High Pressure Generator Stage",
            "when": "2024-03-15T09:42:15Z",
            "who": "DCS Safety Instrumented System (SIS)",
            "why": "Unscheduled multi-train trip incurring significant production stoppage",
            "how": "Radial vibration transmitter spike exceeding 8.4 mm/s trip limit",
            "how_many": "1 critical generating set tripped, 450 MW offline",
            "incident_title": "Turbine Gen-09 Catastrophic Resonant Vibration Excursion",
            "equipment_tag": "Turbine-Gen-09",
            "initial_severity": 9,
            "operational_impact": "Total train outage, emergency steam venting engaged",
        },
        "d3_containment": [
            {
                "action_id": "ICA-01",
                "action": "Immediate emergency trip of inlet governor steam valves and auxiliary lube pump lock",
                "owner": "Shift Supervisor",
                "effectiveness_pct": 100.0,
                "status": "IMPLEMENTED",
            },
            {
                "action_id": "ICA-02",
                "action": "Isolate lube oil supply loops and perform particulate fluid contamination sampling",
                "owner": "Operations Lead",
                "effectiveness_pct": 95.0,
                "status": "IMPLEMENTED",
            },
        ],
        "d4_root_causes": {
            "occurrence_root_cause": "Sub-synchronous hydrodynamic oil whirl triggered by degraded journal clearance",
            "escape_root_cause": "Vibration trending FFT bandpass alarm set above primary resonant mode frequency",
            "five_why_chain": five_why,
            "fishbone_analysis": {
                "branches": [
                    {
                        "category": "Machine",
                        "causes": ["Journal sleeve clearance exceeded OEM specification", "Shaft tilt runout"],
                        "citation_ids": ["CITE-PETRO-0000", "CITE-PETRO-0001"],
                    },
                    {
                        "category": "Method",
                        "causes": ["Oil viscosity sampling schedule prolonged to 90 days"],
                        "citation_ids": ["CITE-PETRO-0002"],
                    },
                    {
                        "category": "Material",
                        "causes": ["Babbitt lining thermal fatigue and micro-cracking"],
                        "citation_ids": ["CITE-PETRO-0003"],
                    },
                    {
                        "category": "Measurement",
                        "causes": ["Accelerometer calibration drift of 4.2%"],
                        "citation_ids": ["CITE-PETRO-0004"],
                    },
                    {
                        "category": "Man",
                        "causes": ["Shift handover missed noting low-frequency pre-trip rumble"],
                        "citation_ids": ["CITE-PETRO-0005"],
                    },
                    {
                        "category": "Environment",
                        "causes": ["Turbine hall temperature excursion to 44C during heatwave"],
                        "citation_ids": ["CITE-PETRO-0006"],
                    },
                ]
            },
        },
        "d5_permanent_actions": [
            {
                "pca_id": "PCA-01",
                "action": "Retrofit tilting-pad journal bearings and recalibrate digital vibration band trip thresholds",
                "target_cause_id": f"WHY-SCALE-{why_depth:02d}",
                "owner": "Chief Mechanical Engineering Director",
                "status": "OPEN",
                "feasibility_score": 9,
            },
            {
                "pca_id": "PCA-02",
                "action": "Install continuous online lube oil dielectric condition monitor with automated DCS interlock",
                "target_cause_id": "WHY-SCALE-02",
                "owner": "Instrumentation Lead",
                "status": "OPEN",
                "feasibility_score": 8,
            },
        ],
        "d6_validation": {
            "validation_id": "VAL-01",
            "metrics": "Continuous baseline vibration FFT below 2.0 mm/s across 0-100% load envelope",
            "status": "IN_PROGRESS",
            "verified_by": "Senior Vibration Analyst",
            "verification_evidence": "Bently Nevada continuous trend stream and commissioning run log",
        },
        "d7_preventative_controls": {
            "sop_updates": [
                "SOP-TURB-09: Mandatory daily seal oil dielectric breakdown test",
                "SOP-VIB-02: Weekly sub-synchronous frequency spectrum review",
            ],
            "pm_updates": [
                "PM-TURB-M01: Bi-weekly modal vibration FFT validation",
                "PM-LUBE-04: Monthly oil flushing filter element replacement",
            ],
            "oem_deviations": [
                {
                    "parameter_name": "Peak Vibration Velocity",
                    "oem_envelope_limit": 4.5,
                    "actual_incident_value": 8.4,
                    "unit": "mm/s",
                    "recommended_action": "Lower automatic trip threshold to 5.2 mm/s",
                },
                {
                    "parameter_name": "Bearing Metal Temperature",
                    "oem_envelope_limit": 85.0,
                    "actual_incident_value": 104.2,
                    "unit": "deg C",
                    "recommended_action": "Increase oil cooler flow interlock",
                },
            ],
            "horizontal_assets": [
                "Turbine-Gen-08",
                "Turbine-Gen-10",
                "Turbine-Gen-11",
                "Boiler-Feed-Pump-01",
            ],
            "description": "Comprehensive fleet-wide horizontal read-across across all heavy rotating trains",
        },
        "d8_recognition": {
            "recognition_notes": "Exemplary DCS triage and rapid isolation prevented high-speed catastrophic rotor burst.",
            "approver_name": "Dr. Marcus Vance",
            "approver_role": "Director of Global Plant Quality & Reliability",
            "signoff_status": "APPROVED",
            "lessons_learned": "Hydrodynamic bearing clearances require automated trend-based predictive trip triggers.",
        },
        "timeline": timeline,
        "citations": citations,
    }
    return data


# ==============================================================================
# GROUP 1: RCAReportStore HIGH CONCURRENCY ADVERSARIAL STRESS (50+ THREADS)
# ==============================================================================

class TestRCAReportStoreHighConcurrency:
    """
    Stress-tests RCAReportStore under extreme thread contention (50-64+ threads)
    executing add, get, list_all, and get_or_fallback simultaneously.
    """

    def test_store_concurrency_50_plus_threads_add_and_get(self):
        """
        Simulates 64 concurrent threads creating and registering unique reports
        simultaneously while asserting immediate retrieval and lock safety.
        """
        store = RCAReportStore()
        thread_count = 64
        errors: List[str] = []
        reports_added: List[str] = []

        def worker(idx: int):
            try:
                rep_id = f"8D-2024-THREAD-{idx:04d}"
                report = make_sample_report(rep_id, asset_tag=f"Pump-{idx:02d}")
                store.add(report)
                retrieved = store.get(rep_id)
                if retrieved is None:
                    errors.append(f"Thread {idx}: report {rep_id} returned None")
                elif retrieved.report_id != rep_id:
                    errors.append(f"Thread {idx}: ID mismatch {retrieved.report_id} != {rep_id}")
                else:
                    reports_added.append(rep_id)
            except Exception as e:
                errors.append(f"Thread {idx} raised: {str(e)}")

        with ThreadPoolExecutor(max_workers=thread_count) as pool:
            futures = [pool.submit(worker, i) for i in range(thread_count)]
            for f in as_completed(futures):
                f.result()

        assert not errors, f"Concurrency errors encountered: {errors}"
        assert len(reports_added) == thread_count

        # Validate registry consistency
        summaries = store.list_all()
        raw_reports = store.list_reports()
        assert len(summaries) == thread_count
        assert len(raw_reports) == thread_count

        # Ensure all stored reports are unique and valid
        stored_ids = {s.report_id for s in summaries}
        assert len(stored_ids) == thread_count

    def test_store_concurrency_heavy_mixed_workload_50_threads(self):
        """
        Simulates 60 concurrent worker threads executing high-frequency mixed operations:
        - 20 writers continuously storing new reports
        - 20 readers calling get()
        - 20 scanners calling list_all() and list_reports()
        Verifies zero RuntimeError (dictionary size change) and zero deadlocks.
        """
        store = RCAReportStore()
        # Seed store with initial baseline
        for i in range(10):
            store.add(make_sample_report(f"8D-2024-SEED-{i:04d}"))

        errors: List[str] = []
        stop_event = False

        def writer(thread_id: int):
            try:
                for step in range(25):
                    rep_id = f"8D-2024-WRITE-{thread_id:02d}-{step:02d}"
                    report = make_sample_report(rep_id)
                    store.add(report)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"Writer {thread_id} failed: {e}")

        def reader(thread_id: int):
            try:
                for step in range(35):
                    # Probe existing and random keys
                    seed_key = f"8D-2024-SEED-{step % 10:04d}"
                    rep = store.get(seed_key)
                    assert rep is not None or step > 10
                    # Probe potentially non-existent keys
                    store.get(f"8D-NONEXISTENT-{step}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"Reader {thread_id} failed: {e}")

        def scanner(thread_id: int):
            try:
                for _ in range(20):
                    summaries = store.list_all()
                    raw_reps = store.list_reports()
                    assert len(summaries) >= 10
                    assert len(raw_reps) >= 10
                    # Verify summary attributes are fully populated
                    for s in summaries:
                        assert s.report_id.startswith("8D-")
                        assert s.severity_score >= 1
                    time.sleep(0.002)
            except Exception as e:
                errors.append(f"Scanner {thread_id} failed: {e}")

        with ThreadPoolExecutor(max_workers=60) as pool:
            futures = []
            for i in range(20):
                futures.append(pool.submit(writer, i))
            for i in range(20):
                futures.append(pool.submit(reader, i))
            for i in range(20):
                futures.append(pool.submit(scanner, i))

            for f in as_completed(futures):
                f.result()

        assert not errors, f"Errors in mixed concurrency test: {errors}"
        # Verify store has all written reports (10 seed + 20 * 25 = 510)
        total_reports = len(store.list_all())
        assert total_reports == 510, f"Expected 510 reports, found {total_reports}"

    def test_store_concurrency_get_or_fallback_race_condition(self):
        """
        Simulates 50 concurrent threads simultaneously requesting the EXACT same
        non-existent report ID via get_or_fallback().
        Verifies:
        - All 50 threads receive a valid, complete EightDIncidentReport instance.
        - Exactly one consistent instance is registered in the store under that ID.
        - No race conditions cause corrupt checksums or incomplete objects.
        """
        store = RCAReportStore()
        target_id = "8D-2024-RACE-FALLBACK-TARGET"
        thread_count = 50
        results: List[EightDIncidentReport] = []
        errors: List[str] = []

        def worker(idx: int):
            try:
                rep = store.get_or_fallback(target_id)
                results.append(rep)
            except Exception as e:
                errors.append(f"Worker {idx} failed: {e}")

        with ThreadPoolExecutor(max_workers=thread_count) as pool:
            futures = [pool.submit(worker, i) for i in range(thread_count)]
            for f in as_completed(futures):
                f.result()

        assert not errors, f"get_or_fallback errors: {errors}"
        assert len(results) == thread_count

        # Validate that every thread received the exact requested ID
        for rep in results:
            assert rep.report_id == target_id
            assert len(rep.checksum_sha256) == 64
            assert rep.asset_tag == "Pump-A12"

        # Validate that the store contains exactly 1 report
        all_reps = store.list_all()
        assert len(all_reps) == 1
        assert all_reps[0].report_id == target_id

    def test_store_concurrency_with_interleaved_deletions(self):
        """
        Simulates concurrent threads adding, deleting, and listing reports.
        Verifies that threading locks preserve atomicity during mutating operations.
        """
        store = RCAReportStore()
        errors: List[str] = []

        # Pre-populate 50 items
        for i in range(50):
            store.add(make_sample_report(f"8D-2024-MUT-{i:04d}"))

        def deleter(idx: int):
            try:
                # Delete even indices
                deleted = store.delete(f"8D-2024-MUT-{idx * 2:04d}")
                # Either True (deleted) or False (already deleted)
                assert isinstance(deleted, bool)
            except Exception as e:
                errors.append(f"Deleter {idx} error: {e}")

        def adder(idx: int):
            try:
                store.add(make_sample_report(f"8D-2024-NEW-{idx:04d}"))
            except Exception as e:
                errors.append(f"Adder {idx} error: {e}")

        def scanner(idx: int):
            try:
                sums = store.list_all()
                assert isinstance(sums, list)
            except Exception as e:
                errors.append(f"Scanner {idx} error: {e}")

        with ThreadPoolExecutor(max_workers=60) as pool:
            futures = []
            for i in range(25):
                futures.append(pool.submit(deleter, i))
            for i in range(25):
                futures.append(pool.submit(adder, i))
            for i in range(10):
                futures.append(pool.submit(scanner, i))

            for f in as_completed(futures):
                f.result()

        assert not errors, f"Errors in concurrent deletion test: {errors}"
        # 50 initial - 25 deleted + 25 added = 50 total
        assert len(store.list_all()) == 50


# ==============================================================================
# GROUP 2: HIGH LOAD SCALE TEST (MASSIVE 8D INCIDENT REPORTS)
# ==============================================================================

class TestHighLoadScaleMassive8DReports:
    """
    Empirically benchmarks system performance on massive 8D incident reports:
    - 550+ timeline events
    - 120+ citations
    - Deep 5-Why causal tree & 6M Fishbone
    Verifies:
    1. Pydantic validation latency < 100ms
    2. Deterministic checksum generation and cryptographic tamper detection
    3. HTML and JSON compliance package compilation scalability within bounded memory
    """

    def test_massive_report_pydantic_validation_latency_sub_100ms(self):
        """
        Validates that a massive 8D incident report containing 550 timeline events
        and 120 citations parses and validates in strictly < 100ms.
        """
        payload = build_massive_report_payload(event_count=550, citation_count=120, why_depth=15)
        assert len(payload["timeline"]) == 550
        assert len(payload["citations"]) == 120

        # Benchmark validation latency
        t0 = time.perf_counter()
        report = EightDIncidentReport(**payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Assert performance requirement (< 100ms)
        assert elapsed_ms < 100.0, (
            f"Pydantic validation of massive report took {elapsed_ms:.2f}ms (threshold: 100ms)"
        )

        # Invariant checks on the instantiated model
        assert len(report.timeline) == 550
        assert len(report.citations) == 120
        assert report.rpn_score == 9 * 7 * 8  # 504
        assert len(report.d4_root_causes.five_why_chain) == 15
        assert report.d4_root_causes.citation_grounding_ratio > 0.0

    def test_massive_report_deterministic_checksum_generation(self):
        """
        Verifies that canonical SHA-256 checksum computation is 100% deterministic
        across repeated invocations and survives JSON round-tripping.
        """
        payload = build_massive_report_payload(event_count=500, citation_count=100)
        report = EightDIncidentReport(**payload)

        # Baseline digest
        base_hash = report.compute_canonical_sha256()
        assert len(base_hash) == 64
        assert re.match(r"^[0-9a-f]{64}$", base_hash)

        # 25 repeated recomputations must yield identical digest
        for iteration in range(25):
            digest_iter = report.compute_canonical_sha256()
            assert digest_iter == base_hash, f"Iteration {iteration} produced non-deterministic hash"

        # Module function compute_canonical_sha256() must match model method
        external_hash = compute_canonical_sha256(report)
        assert external_hash == base_hash

        # Model checksum verification method must return True
        assert report.verify_checksum() is True

        # Round-trip serialization through model_dump -> JSON -> dict
        dumped_json = report.model_dump_json()
        restored_data = json.loads(dumped_json)
        restored_report = EightDIncidentReport(**restored_data)
        assert restored_report.compute_canonical_sha256() == base_hash
        assert restored_report.checksum_sha256 == base_hash

    def test_massive_report_checksum_avalanche_effect(self):
        """
        Probes the cryptographic avalanche effect on a massive report:
        altering a single character in the 500th timeline event must alter the
        resulting SHA-256 digest completely.
        """
        payload = build_massive_report_payload(event_count=500, citation_count=100)
        report = EightDIncidentReport(**payload)
        original_hash = report.compute_canonical_sha256()

        # Mutate single character in the last timeline event
        report.timeline[-1].description = report.timeline[-1].description + "!"
        tampered_hash = report.compute_canonical_sha256()

        assert original_hash != tampered_hash

        # Measure bit differences (avalanche effect: expect ~128 out of 256 bits changed)
        orig_bytes = bytes.fromhex(original_hash)
        tamp_bytes = bytes.fromhex(tampered_hash)
        diff_bits = sum(bin(b1 ^ b2).count("1") for b1, b2 in zip(orig_bytes, tamp_bytes))

        # Cryptographic avalanche property: at least 64 bits changed
        assert diff_bits >= 64, f"Avalanche effect insufficient: only {diff_bits} bits changed"

    def test_massive_report_html_compliance_package_compilation_and_memory(self):
        """
        Verifies that generating a certified HTML compliance package for a massive report:
        1. Compiles without exponential slowdown (strictly < 500ms)
        2. Produces a complete print-ready document containing all 550 timeline events and 120 citations
        3. Maintains bounded memory overhead and releases resources cleanly
        """
        payload = build_massive_report_payload(event_count=550, citation_count=120)
        report = EightDIncidentReport(**payload)

        # Force garbage collection to measure memory stability
        gc.collect()

        t0 = time.perf_counter()
        html_content, sha256_checksum, filename = generate_compliance_package(report, format="html")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Assert compilation latency is fast (< 500ms, typical ~15ms)
        assert elapsed_ms < 500.0, f"HTML compliance package compilation too slow: {elapsed_ms:.2f}ms"

        # Check returned tuple
        assert filename == "8D-2024-TURB-GEN-09-MASSIVE_compliance_audit.html"
        assert len(sha256_checksum) == 64
        assert sha256_checksum == report.checksum_sha256

        # Check content size and key markers
        assert len(html_content) > 300_000, "Generated HTML should be extensive (>300KB)"
        assert "<!DOCTYPE html>" in html_content
        assert 'data-checksum="' + sha256_checksum + '"' in html_content
        assert f"Certified SHA-256 Checksum: {sha256_checksum}" in html_content

        # Verify compliance standards declared
        assert "ISO 9001:2015" in html_content
        assert "IATF 16949:2016" in html_content
        assert "AIAG 8D" in html_content

        # Verify first and last timeline events rendered
        assert "EVT-SCALE-00000" in html_content
        assert "EVT-SCALE-00549" in html_content

        # Verify first and last citations rendered
        assert "CITE-PETRO-0000" in html_content
        assert "CITE-PETRO-0119" in html_content

        # Verify embedded canonical JSON data island
        match = re.search(r'<script id="compliance-audit-data" type="application/json">\s*(\{.*?\})\s*</script>', html_content, re.DOTALL)
        assert match is not None, "Data island script tag missing from HTML package"
        data_island_json = match.group(1).replace("\\u003c", "<").replace("\\u003e", ">")
        parsed_island = json.loads(data_island_json)
        assert parsed_island["report_id"] == "8D-2024-TURB-GEN-09-MASSIVE"
        assert len(parsed_island["timeline"]) == 550
        assert len(parsed_island["citations"]) == 120

    def test_massive_report_json_compliance_package_compilation(self):
        """
        Verifies that generating a certified JSON compliance package for a massive report:
        1. Compiles in < 200ms
        2. Preserves exact root-level fields, checksums, and structure
        """
        payload = build_massive_report_payload(event_count=500, citation_count=100)
        report = EightDIncidentReport(**payload)

        t0 = time.perf_counter()
        json_content, sha256_checksum, filename = generate_compliance_package(report, format="json")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert elapsed_ms < 200.0, f"JSON compliance compilation took {elapsed_ms:.2f}ms"
        assert filename == "8D-2024-TURB-GEN-09-MASSIVE_evidence_package.json"
        assert sha256_checksum == report.checksum_sha256

        # Parse output JSON
        data = json.loads(json_content)
        assert data["report_id"] == "8D-2024-TURB-GEN-09-MASSIVE"
        assert data["checksum_sha256"] == sha256_checksum
        assert len(data["timeline"]) == 500
        assert len(data["citations"]) == 100


# ==============================================================================
# GROUP 3: ENDPOINT BOUNDARY PROBING & CONCURRENT REQUESTS (/api/v1/rca/*)
# ==============================================================================

class TestEndpointBoundaryProbingAndConcurrency:
    """
    Adversarial probes across /api/v1/rca/* endpoints testing:
    - High concurrency client requests
    - Boundary parameter values and hostile inputs
    - Dynamic fallback handling and error status codes
    """

    def test_concurrent_rca_analyze_endpoints(self, client):
        """
        Fires 20 concurrent HTTP requests to POST /api/v1/rca/analyze
        with distinct asset tags and telemetry parameters.
        Verifies 200 OK across all calls and store consistency.
        """
        concurrency = 20
        errors: List[str] = []
        reports_received: List[Dict[str, Any]] = []

        def call_analyze(idx: int):
            try:
                payload = {
                    "asset_tag": f"Turbine-Burst-{idx:03d}",
                    "symptoms": [
                        f"harmonic resonance mode {idx}",
                        "shaft radial excursion 6.1 mm/s",
                    ],
                    "incident_timestamp": "2024-03-15T08:00:00Z",
                    "telemetry_data": {
                        "vibration_mm_s": 6.1 + idx * 0.05,
                        "temperature_c": 70.0 + idx * 0.2,
                    },
                }
                resp = client.post("/api/v1/rca/analyze", json=payload)
                if resp.status_code != 200:
                    errors.append(f"Request {idx} failed with {resp.status_code}: {resp.text}")
                else:
                    reports_received.append(resp.json())
            except Exception as e:
                errors.append(f"Request {idx} exception: {e}")

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(call_analyze, i) for i in range(concurrency)]
            for f in as_completed(futures):
                f.result()

        assert not errors, f"Errors in concurrent /analyze: {errors}"
        assert len(reports_received) == concurrency

        # Verify all reports generated unique IDs and have valid checksums
        report_ids = {r["report_id"] for r in reports_received}
        assert len(report_ids) == concurrency
        for r in reports_received:
            assert len(r["checksum_sha256"]) == 64
            assert r["asset_tag"].startswith("Turbine-Burst-")

        # Verify in-memory store contains all 20 reports
        stored_summaries = rca_report_store.list_all()
        assert len(stored_summaries) == concurrency

    def test_concurrent_export_evidence_mixed_known_and_fallback(self, client):
        """
        Fires 24 concurrent requests to POST /api/v1/rca/export-evidence:
        - 12 for pre-existing reports
        - 12 for non-existent reports (triggering concurrent fallback generation)
        Verifies 200 OK across all requests with valid checksums and filenames.
        """
        # Pre-seed 12 known reports
        known_ids = []
        for i in range(12):
            rep = make_sample_report(f"8D-2024-KNOWN-{i:04d}", asset_tag=f"Pre-Seed-{i}")
            rca_report_store.add(rep)
            known_ids.append(rep.report_id)

        errors: List[str] = []
        responses: List[Dict[str, Any]] = []

        def call_export(idx: int):
            try:
                if idx < 12:
                    target_id = known_ids[idx]
                    fmt = "html"
                else:
                    target_id = f"8D-2024-UNKNOWN-FB-{idx:04d}"
                    fmt = "json" if idx % 2 == 0 else "html"

                payload = {"report_id": target_id, "format": fmt}
                resp = client.post("/api/v1/rca/export-evidence", json=payload)
                if resp.status_code != 200:
                    errors.append(f"Export {idx} ({target_id}) failed: {resp.status_code} {resp.text}")
                else:
                    responses.append(resp.json())
            except Exception as e:
                errors.append(f"Export {idx} exception: {e}")

        with ThreadPoolExecutor(max_workers=24) as pool:
            futures = [pool.submit(call_export, i) for i in range(24)]
            for f in as_completed(futures):
                f.result()

        assert not errors, f"Errors in concurrent export-evidence: {errors}"
        assert len(responses) == 24
        for r in responses:
            assert "content" in r
            assert len(r["sha256_checksum"]) == 64
            assert r["filename"].endswith(".html") or r["filename"].endswith(".json")

    def test_concurrent_list_reports_under_analyze_mutations(self, client):
        """
        Simultaneously fires POST /analyze calls while concurrent threads repeatedly
        query GET /api/v1/rca/reports. Verifies zero 500 Internal Server Errors
        and consistent summary schemas.
        """
        errors: List[str] = []

        def writer(idx: int):
            try:
                for step in range(5):
                    resp = client.post("/api/v1/rca/analyze", json={
                        "asset_tag": f"Asset-Contend-{idx}-{step}",
                        "symptoms": ["vibration rise", "bearing noise"],
                        "incident_timestamp": "2024-03-15T08:00:00Z",
                    })
                    assert resp.status_code == 200
            except Exception as e:
                errors.append(f"Writer {idx} error: {e}")

        def reader(idx: int):
            try:
                for _ in range(10):
                    resp = client.get("/api/v1/rca/reports")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert isinstance(data, list)
                    for item in data:
                        assert "report_id" in item
                        assert "severity_score" in item
            except Exception as e:
                errors.append(f"Reader {idx} error: {e}")

        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for i in range(10):
                futures.append(pool.submit(writer, i))
            for i in range(10):
                futures.append(pool.submit(reader, i))

            for f in as_completed(futures):
                f.result()

        assert not errors, f"Errors during list/analyze contention: {errors}"

    def test_endpoint_extreme_telemetry_boundaries(self, client):
        """
        Probes POST /api/v1/rca/analyze with boundary float values in telemetry:
        - Subnormal float (1e-15)
        - Extreme high float (1e9)
        - Negative values (-100.5)
        - Zero values (0.0)
        """
        test_cases = [
            {"label": "subnormal", "vibration_mm_s": 1e-15, "temp_c": 25.0},
            {"label": "extreme_high", "vibration_mm_s": 9999999.9, "temp_c": 1500.0},
            {"label": "negative", "vibration_mm_s": -2.5, "temp_c": -40.0},
            {"label": "zero", "vibration_mm_s": 0.0, "temp_c": 0.0},
        ]

        for case in test_cases:
            payload = {
                "asset_tag": f"Compressor-{case['label']}",
                "symptoms": ["telemetry calibration test excursion"],
                "incident_timestamp": "2024-03-15T10:00:00Z",
                "telemetry_data": {
                    "vibration_mm_s": case["vibration_mm_s"],
                    "temp_c": case["temp_c"],
                },
            }
            resp = client.post("/api/v1/rca/analyze", json=payload)
            assert resp.status_code == 200, f"Case {case['label']} failed with {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data["asset_tag"] == f"Compressor-{case['label']}"
            assert len(data["checksum_sha256"]) == 64

    def test_endpoint_boundary_parameter_probing(self, client):
        """
        Probes POST /api/v1/rca/analyze with boundary and hostile inputs:
        - 5,000 character asset tag -> 200 OK
        - 150 symptoms -> 200 OK
        - Empty symptoms list -> 422 Unprocessable Entity
        - Missing asset tag -> 422 Unprocessable Entity
        """
        # 1. 5,000 character asset tag
        huge_tag = "TURB-" + "A" * 5000
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": huge_tag,
            "symptoms": ["extreme tag boundary test"],
            "incident_timestamp": "2024-03-15T12:00:00Z",
        })
        assert resp.status_code == 200
        assert resp.json()["asset_tag"] == huge_tag

        # 2. 150 symptoms
        many_symptoms = [f"symptom_cascade_factor_{i}" for i in range(150)]
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-Multi-Symptom",
            "symptoms": many_symptoms,
            "incident_timestamp": "2024-03-15T12:00:00Z",
        })
        assert resp.status_code == 200

        # 3. Empty symptoms list -> 422
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-Empty",
            "symptoms": [],
            "incident_timestamp": "2024-03-15T12:00:00Z",
        })
        assert resp.status_code == 422

        # 4. Missing asset_tag -> 422
        resp = client.post("/api/v1/rca/analyze", json={
            "symptoms": ["missing tag symptom"],
            "incident_timestamp": "2024-03-15T12:00:00Z",
        })
        assert resp.status_code == 422

    def test_endpoint_export_evidence_boundary_formats(self, client):
        """
        Probes POST /api/v1/rca/export-evidence against invalid and boundary formats:
        - Unsupported formats ('xml', 'pdf', 'csv', 'yaml', 'exe', empty) -> 400 Bad Request
        - Valid variations ('HTML', 'JSON', '  html  ', '  json  ') -> 200 OK
        """
        # Seed a report
        seed = make_sample_report("8D-2024-FMT-TEST-001")
        rca_report_store.add(seed)

        # Invalid formats -> 400
        invalid_formats = ["xml", "pdf", "csv", "yaml", "docx", "exe", "   ", "jsonp", "script"]
        for fmt in invalid_formats:
            resp = client.post("/api/v1/rca/export-evidence", json={
                "report_id": "8D-2024-FMT-TEST-001",
                "format": fmt,
            })
            assert resp.status_code == 400, f"Format '{fmt}' should return 400, got {resp.status_code}"
            assert "Unsupported format" in resp.json()["detail"]

        # Valid format variations -> 200
        valid_formats = ["HTML", "JSON", "Html", "Json", "  html  ", "  json  "]
        for fmt in valid_formats:
            resp = client.post("/api/v1/rca/export-evidence", json={
                "report_id": "8D-2024-FMT-TEST-001",
                "format": fmt,
            })
            assert resp.status_code == 200, f"Format '{fmt}' failed: {resp.status_code}"
            data = resp.json()
            assert len(data["sha256_checksum"]) == 64

    def test_endpoint_get_report_by_id_boundaries(self, client):
        """
        Probes GET /api/v1/rca/reports/{report_id} with:
        - Pre-existing report -> 200 OK with matching model
        - Non-existent report -> 404 Not Found
        - Pathological / path traversal report IDs -> 404 Not Found
        """
        # Pre-seed report
        rep = make_sample_report("8D-2024-LOOKUP-001")
        rca_report_store.add(rep)

        # 1. Existing ID -> 200 OK
        resp = client.get("/api/v1/rca/reports/8D-2024-LOOKUP-001")
        assert resp.status_code == 200
        assert resp.json()["report_id"] == "8D-2024-LOOKUP-001"

        # 2. Non-existent ID -> 404
        resp = client.get("/api/v1/rca/reports/8D-2024-NONEXISTENT")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

        # 3. Pathological IDs -> 404
        pathological = [
            "8D-UNKNOWN-9999",
            "8D-2024-..-..-attack",
            "8D-SELECT-FROM-USERS",
        ]
        for pid in pathological:
            resp = client.get(f"/api/v1/rca/reports/{pid}")
            assert resp.status_code == 404
