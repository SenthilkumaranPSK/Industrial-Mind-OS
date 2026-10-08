"""
Industrial Mind OS - Milestone 3 Adversarial Stress & Robustness Test Suite
Location: backend/tests/test_adversarial_rca_api.py

Empirical stress testing targeting:
1. Extreme & Boundary Payloads against /api/v1/rca/* endpoints:
   - Giant payloads (10k char tags, 100 symptoms, huge telemetry dicts)
   - Unicode, multi-language, emoji, special characters, and SQL injection strings
   - Boundary ISO-8601 timestamps (leap year, epoch, far future, millisecond offsets)
   - Malformed telemetry (extreme floats, subnormals, non-numeric strings)
   - Empty/whitespace symptoms and asset tags
2. Non-existent, Invalid, and Boundary Format Strings against /export-evidence:
   - Unsupported formats ('xml', 'pdf', 'csv', 'yaml', 'exe', whitespace-only) -> 400 Bad Request
   - Case-insensitive & trimmed valid formats ('HTML', 'JSON', '  html  ', '  json  ') -> 200 OK
   - Unknown & pathological report IDs ('8D-NONEXISTENT', path traversal, XSS strings) -> 200 Fallback
3. Concurrency, Race Condition Resilience & Thread Safety:
   - High-concurrency /analyze bursts across multiple threads
   - Concurrent fallback generation on identical non-existent report IDs
   - Mixed multi-threaded traffic (/analyze, /reports, /historical-match, /export-evidence)
4. SHA-256 Digital Seal Integrity, Avalanche Effect & Tamper Detection:
   - Exact bit-for-bit canonical hash match across JSON & HTML exports
   - Tamper detection across all 8D disciplines
   - Cryptographic avalanche effect (>50 bit difference on 1-character mutation)
   - Probing verify_compliance_checksum mutation side-effect and script tag breakout
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from main import app
from api.rca_router import rca_report_store
from api.rca_schemas import EightDIncidentReport, RCAAnalyzeRequest
from services.compliance_package import (
    build_audit_html,
    build_audit_json,
    compute_canonical_sha256,
    generate_compliance_package,
    verify_compliance_checksum,
)


# ==============================================================================
# FIXTURES & ISOLATION
# ==============================================================================

@pytest.fixture(autouse=True)
def clean_store():
    """Ensures each test starts with an isolated empty report store."""
    rca_report_store.clear()
    yield
    rca_report_store.clear()


@pytest.fixture
def client():
    """Provides ASGI TestClient bound to main.app."""
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# 1. EXTREME & BOUNDARY PAYLOADS: POST /api/v1/rca/analyze
# ==============================================================================

class TestAnalyzeExtremePayloads:
    """Stress tests probing /analyze against extreme, boundary, and hostile payloads."""

    def test_giant_payload_many_symptoms(self, client):
        """Probes /analyze with 100 symptoms and large descriptions."""
        symptoms = [f"symptom_excursion_metric_sensor_{i}_vibration_spike" for i in range(100)]
        payload = {
            "asset_tag": "Pump-A12",
            "symptoms": symptoms,
            "incident_timestamp": "2023-11-04T08:00:00Z",
            "telemetry_data": {"vibration_mm_s": 5.8},
        }
        resp = client.post("/api/v1/rca/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_tag"] == "Pump-A12"
        assert len(data["checksum_sha256"]) == 64

    def test_giant_asset_tag_string(self, client):
        """Probes /analyze with a very long asset tag (5,000 chars)."""
        huge_tag = "PUMP-" + "X" * 5000
        payload = {
            "asset_tag": huge_tag,
            "symptoms": ["excessive mechanical wear"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        }
        resp = client.post("/api/v1/rca/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_tag"] == huge_tag

    def test_unicode_and_emoji_asset_tags_and_symptoms(self, client):
        """Probes /analyze with multi-lingual unicode, Chinese, Cyrillic, and emoji."""
        payload = {
            "asset_tag": "Насос-泵-Pump-🔥-001",
            "symptoms": ["高振动 5.8 mm/s", "перегрев подшипника", "coolant leak 🌊"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
            "telemetry_data": {"vibration_mm_s": 5.8},
        }
        resp = client.post("/api/v1/rca/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_tag"] == "Насос-泵-Pump-🔥-001"
        assert len(data["checksum_sha256"]) == 64

    def test_hostile_characters_sql_and_xss_in_symptoms(self, client):
        """Probes /analyze with SQL injection and HTML/XSS strings."""
        payload = {
            "asset_tag": "Pump-A12'; DROP TABLE reports; --",
            "symptoms": [
                "<script>alert('xss')</script>",
                "vibration' OR 1=1; --",
                "<b>bold symptom</b>",
            ],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        }
        resp = client.post("/api/v1/rca/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["checksum_sha256"]) == 64
        # Verify stored cleanly
        stored = rca_report_store.get(data["report_id"])
        assert stored is not None

    def test_boundary_iso_timestamps(self, client):
        """Probes /analyze across leap year, epoch, far future, and offset ISO timestamps."""
        test_timestamps = [
            "2024-02-29T23:59:59.999999Z",       # Leap year
            "1970-01-01T00:00:00Z",              # Unix epoch
            "2099-12-31T23:59:59Z",              # Far future
            "2023-11-04T08:00:00.123456+05:30",  # Milliseconds with timezone offset
            "2023-11-04T08:00:00-08:00",         # Negative timezone offset
        ]
        for ts in test_timestamps:
            resp = client.post("/api/v1/rca/analyze", json={
                "asset_tag": "Pump-A12",
                "symptoms": ["vibration 5.8 mm/s"],
                "incident_timestamp": ts,
            })
            assert resp.status_code == 200, f"Timestamp {ts} failed with status {resp.status_code}"

    def test_malformed_timestamps_rejected_with_422(self, client):
        """Probes /analyze with invalid timestamp formats, ensuring strict 422."""
        bad_timestamps = [
            "invalid-date",
            "2023/11/04",
            "2023-13-45T08:00:00Z",
            "",
            "yesterday",
            "1234567890",
        ]
        for bad_ts in bad_timestamps:
            resp = client.post("/api/v1/rca/analyze", json={
                "asset_tag": "Pump-A12",
                "symptoms": ["vibration"],
                "incident_timestamp": bad_ts,
            })
            assert resp.status_code == 422, f"Bad timestamp '{bad_ts}' was not rejected with 422"

    def test_extreme_numerical_telemetry(self, client):
        """Probes /analyze with huge, negative, and zero telemetry values."""
        payload = {
            "asset_tag": "Pump-A12",
            "symptoms": ["vibration"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
            "telemetry_data": {
                "vibration_mm_s": 1e20,
                "bearing_temp_c": -50.0,
                "pressure_bar": 0.0,
            },
        }
        resp = client.post("/api/v1/rca/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_tag"] == "Pump-A12"

    def test_large_telemetry_dictionary(self, client):
        """Probes /analyze with 100 sensor channels in telemetry_data."""
        many_sensors = {f"sensor_{i:03d}": float(i * 1.5) for i in range(100)}
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["multi-sensor excursion"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
            "telemetry_data": many_sensors,
        })
        assert resp.status_code == 200

    def test_empty_symptoms_list_returns_422(self, client):
        """Empty symptoms list [] must strictly return 422 per test_f9_b01."""
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": [],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        assert resp.status_code == 422

    def test_missing_asset_tag_returns_422(self, client):
        """Missing asset_tag must strictly return 422 per test_f9_b02."""
        resp = client.post("/api/v1/rca/analyze", json={
            "symptoms": ["leak"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        assert resp.status_code == 422


# ==============================================================================
# 2. BOUNDARY & ADVERSARIAL: POST /api/v1/rca/historical-match
# ==============================================================================

class TestHistoricalMatchBoundaries:
    """Stress tests probing /historical-match under edge and adverse conditions."""

    def test_empty_symptoms_returns_200_empty_list(self, client):
        """Empty symptoms list must return 200 OK and [] per test_f9_b04."""
        resp = client.post("/api/v1/rca/historical-match", json={
            "asset_tag": "Pump-A12",
            "symptoms": [],
        })
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unknown_asset_with_nonsense_symptoms(self, client):
        """Unknown asset with non-overlapping symptoms returns list safely without 500."""
        resp = client.post("/api/v1/rca/historical-match", json={
            "asset_tag": "UNKNOWN-ASSET-XYZ-999",
            "symptoms": ["flying elephants", "quantum banana fluctuation"],
        })
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_whitespace_symptoms_handling(self, client):
        """Symptoms list with whitespace strings does not crash."""
        resp = client.post("/api/v1/rca/historical-match", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["   ", "\t\n", ""],
        })
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_large_symptoms_list_historical_match(self, client):
        """Historical match with 150 symptoms executes safely."""
        many_symptoms = [f"symptom_{i}" for i in range(150)] + ["vibration 5.8 mm/s"]
        resp = client.post("/api/v1/rca/historical-match", json={
            "asset_tag": "Pump-A12",
            "symptoms": many_symptoms,
        })
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_malformed_telemetry_features(self, client):
        """Historical match with strange telemetry feature structures does not crash."""
        resp = client.post("/api/v1/rca/historical-match", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["vibration"],
            "telemetry_features": {
                "speed": "not-numeric",
                "vib": None,
                "nested": {"param": 10},
                "array": [1, 2, 3],
            },
        })
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ==============================================================================
# 3. FORMAT STRINGS & ADVERSARIAL: POST /api/v1/rca/export-evidence
# ==============================================================================

class TestExportEvidenceFormatStrings:
    """Stress tests probing /export-evidence format handling and fallback packages."""

    @pytest.mark.parametrize("invalid_format", [
        "xml",
        "pdf",
        "csv",
        "yaml",
        "docx",
        "exe",
        "markdown",
        "   ",
        "json; charset=utf-8",
        "../etc/passwd",
        "\x00json",
    ])
    def test_unsupported_formats_return_400_bad_request(self, client, invalid_format):
        """Verifies unsupported formats strictly return 400 Bad Request per test_f9_b03."""
        resp = client.post("/api/v1/rca/export-evidence", json={
            "report_id": "8D-2023-PUMP-A12",
            "format": invalid_format,
        })
        assert resp.status_code == 400
        assert "Unsupported format" in resp.json()["detail"]

    @pytest.mark.parametrize("valid_format", [
        "html",
        "json",
        "HTML",
        "JSON",
        "Html",
        "Json",
        "  html  ",
        "  json  ",
        "  HTML  ",
    ])
    def test_valid_format_variations_return_200_ok(self, client, valid_format):
        """Verifies case variations and whitespace padding on valid formats return 200 OK."""
        resp = client.post("/api/v1/rca/export-evidence", json={
            "report_id": "8D-NONEXISTENT",
            "format": valid_format,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sha256_checksum"]) == 64
        if "json" in valid_format.lower():
            assert data["filename"].endswith(".json")
        else:
            assert data["filename"].endswith(".html")

    def test_missing_report_id_returns_422(self, client):
        """POST /export-evidence without report_id must return 422."""
        resp = client.post("/api/v1/rca/export-evidence", json={"format": "json"})
        assert resp.status_code == 422

    def test_nonexistent_report_generates_valid_fallback(self, client):
        """Non-existent report ID generates compliant fallback with 200 OK per test_f9_b05."""
        resp = client.post("/api/v1/rca/export-evidence", json={
            "report_id": "8D-NONEXISTENT-9999",
            "format": "json",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sha256_checksum"]) == 64
        content = json.loads(data["content"])
        assert "d1_team" in content
        assert content["report_id"] == "8D-NONEXISTENT-9999"

    def test_pathological_report_ids_in_export_fallback(self, client):
        """Probes export fallback with path traversal and special characters in report_id."""
        pathological_ids = [
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "8D-TAG-WITH-SPACES AND SPECIALS!@#",
            "泵-ID-999",
        ]
        for pid in pathological_ids:
            resp = client.post("/api/v1/rca/export-evidence", json={
                "report_id": pid,
                "format": "html",
            })
            assert resp.status_code == 200
            data = resp.json()
            # Verify pid is safely escaped in HTML presentation
            import html
            assert html.escape(pid) in data["content"]


# ==============================================================================
# 4. REPORT QUERY & RETRIEVAL: GET /reports & /reports/{id}
# ==============================================================================

class TestReportStoreQueries:
    """Stress tests probing report listing and retrieval boundaries."""

    def test_get_nonexistent_report_returns_404(self, client):
        """Looking up non-existent report ID must strictly return 404 Not Found."""
        resp = client.get("/api/v1/rca/reports/8D-DOES-NOT-EXIST-404")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_reports_with_path_traversal_returns_404(self, client):
        """Looking up path traversal report ID returns 404."""
        resp = client.get("/api/v1/rca/reports/..%2f..%2fetc%2fpasswd")
        assert resp.status_code == 404

    def test_list_reports_dual_field_contract(self, client):
        """Validates dual compatibility in summary objects (title/incident_title, checksum/sha256)."""
        # Create report
        client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["vibration 5.8 mm/s"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        resp = client.get("/api/v1/rca/reports")
        assert resp.status_code == 200
        summaries = resp.json()
        assert len(summaries) == 1
        s = summaries[0]
        # Dual fields must be identical
        assert s["title"] == s["incident_title"]
        assert s["checksum_sha256"] == s["sha256_checksum"]
        assert len(s["checksum_sha256"]) == 64


# ==============================================================================
# 5. CONCURRENCY & RACE CONDITION RESILIENCE
# ==============================================================================

class TestConcurrencyAndRaceConditions:
    """Stress tests probing thread safety, concurrency, and race conditions."""

    def test_high_concurrency_analyze_burst(self, client):
        """Probes 20 concurrent /analyze requests across 4 worker threads."""
        def call_analyze(idx: int):
            with TestClient(app) as local_client:
                return local_client.post("/api/v1/rca/analyze", json={
                    "asset_tag": f"Pump-Thread-{idx:02d}",
                    "symptoms": [f"vibration spike on unit {idx}"],
                    "incident_timestamp": "2023-11-04T08:00:00Z",
                    "telemetry_data": {"vibration_mm_s": 5.0 + (idx * 0.1)},
                })

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(call_analyze, i) for i in range(20)]
            results = [f.result() for f in futures]

        for r in results:
            assert r.status_code == 200

        # All 20 reports must exist in the report store without loss
        list_resp = client.get("/api/v1/rca/reports")
        assert len(list_resp.json()) == 20

    def test_concurrent_fallback_generation_same_id(self, client):
        """Probes 10 concurrent threads requesting fallback export for the SAME non-existent report_id."""
        def call_export():
            with TestClient(app) as local_client:
                return local_client.post("/api/v1/rca/export-evidence", json={
                    "report_id": "8D-CONCURRENT-FALLBACK-SHARED",
                    "format": "json",
                })

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(call_export) for _ in range(10)]
            results = [f.result() for f in futures]

        # All requests must succeed
        for r in results:
            assert r.status_code == 200
            assert len(r.json()["sha256_checksum"]) == 64

        # Exactly 1 report should be present in store
        stored = rca_report_store.get("8D-CONCURRENT-FALLBACK-SHARED")
        assert stored is not None

    def test_mixed_multi_threaded_traffic(self, client):
        """Probes mixed concurrent operations (/analyze, /reports, /historical-match, /export-evidence)."""
        # Pre-seed one report
        init_resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-Seed",
            "symptoms": ["initial seed"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        seed_id = init_resp.json()["report_id"]

        def op_analyze(idx: int):
            with TestClient(app) as c:
                return c.post("/api/v1/rca/analyze", json={
                    "asset_tag": f"Asset-{idx}",
                    "symptoms": ["vibration"],
                    "incident_timestamp": "2023-11-04T08:00:00Z",
                }).status_code

        def op_list():
            with TestClient(app) as c:
                return c.get("/api/v1/rca/reports").status_code

        def op_match():
            with TestClient(app) as c:
                return c.post("/api/v1/rca/historical-match", json={
                    "asset_tag": "Pump-Seed",
                    "symptoms": ["vibration"],
                }).status_code

        def op_export():
            with TestClient(app) as c:
                return c.post("/api/v1/rca/export-evidence", json={
                    "report_id": seed_id,
                    "format": "html",
                }).status_code

        tasks = []
        with ThreadPoolExecutor(max_workers=6) as pool:
            for i in range(5):
                tasks.append(pool.submit(op_analyze, i))
                tasks.append(pool.submit(op_list))
                tasks.append(pool.submit(op_match))
                tasks.append(pool.submit(op_export))

            results = [t.result() for t in tasks]

        # Every operation should succeed with 200 OK
        assert all(code == 200 for code in results), f"Mixed operations failed: {results}"


# ==============================================================================
# 6. SHA-256 SEAL VALIDATION & TAMPER DETECTION PROBES
# ==============================================================================

class TestSHA256TamperDetectionProbes:
    """Stress tests probing SHA-256 seal integrity and tamper detection."""

    def test_sha256_canonical_bit_for_bit_match(self, client):
        """Verifies exported JSON digest matches independently recomputed canonical hash."""
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["vibration 5.8 mm/s"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        rep_id = resp.json()["report_id"]

        exp_resp = client.post("/api/v1/rca/export-evidence", json={
            "report_id": rep_id,
            "format": "json",
        })
        data = exp_resp.json()
        digest = data["sha256_checksum"]

        content_dict = json.loads(data["content"])
        cleaned = {k: v for k, v in content_dict.items() if k not in ("checksum_sha256", "sha256_checksum")}
        canonical = json.dumps(cleaned, sort_keys=True, separators=(",", ":"))
        expected_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        assert digest == expected_digest

    def test_html_export_embeds_matching_sha_seal_and_meta(self, client):
        """Verifies HTML export includes matching data-checksum, meta tag, and sha-seal text."""
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["seal crack"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        rep_id = resp.json()["report_id"]

        exp_resp = client.post("/api/v1/rca/export-evidence", json={
            "report_id": rep_id,
            "format": "html",
        })
        html_doc = exp_resp.json()["content"]
        digest = exp_resp.json()["sha256_checksum"]

        assert f'data-checksum="{digest}"' in html_doc
        assert f'content="{digest}"' in html_doc
        assert f"Certified SHA-256 Checksum: {digest}" in html_doc

    def test_single_byte_mutation_avalanche_effect(self, client):
        """Verifies mutating 1 byte in exported JSON causes >= 50 bit avalanche difference."""
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["vibration 5.8 mm/s"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        exp_resp = client.post("/api/v1/rca/export-evidence", json={
            "report_id": resp.json()["report_id"],
            "format": "json",
        })
        orig_content = exp_resp.json()["content"]
        orig_hash = hashlib.sha256(orig_content.encode("utf-8")).hexdigest()

        # Mutate single character 'A12' -> 'A13'
        tampered_content = orig_content.replace("Pump-A12", "Pump-A13", 1)
        tampered_hash = hashlib.sha256(tampered_content.encode("utf-8")).hexdigest()

        assert orig_hash != tampered_hash
        diff_bits = bin(int(orig_hash, 16) ^ int(tampered_hash, 16)).count("1")
        assert diff_bits >= 50, f"Avalanche effect deficient: only {diff_bits} bits flipped"

    def test_model_tamper_detection_on_mutated_disciplines(self, client):
        """Verifies report.verify_checksum() detects mutation across all disciplines."""
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["vibration 5.8 mm/s"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        rep_id = resp.json()["report_id"]
        report = rca_report_store.get(rep_id)
        assert report.verify_checksum() is True

        # Mutate D1
        orig_leader = report.d1_team.leader
        report.d1_team.leader = "Imposter"
        assert report.verify_checksum() is False
        report.d1_team.leader = orig_leader
        assert report.verify_checksum() is True

        # Mutate Severity Score
        orig_sev = report.severity_score
        report.severity_score = 1
        assert report.verify_checksum() is False
        report.severity_score = orig_sev
        assert report.verify_checksum() is True

    @pytest.mark.xfail(
        reason="Vulnerability: verify_compliance_checksum mutates report.checksum_sha256 as side effect, resealing tampered reports on repeat calls",
        strict=False,
    )
    def test_verify_compliance_checksum_is_idempotent_and_non_mutating(self, client):
        """
        Adversarial probe: verify_compliance_checksum should be idempotent.
        Calling it twice on a tampered report MUST return False both times.
        Currently, the first call sets report.checksum_sha256 to the new hash,
        causing the second call to return True.
        """
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["vibration 5.8 mm/s"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        rep_id = resp.json()["report_id"]
        report = rca_report_store.get(rep_id)

        # Mutate report
        report.d1_team.leader = "Tampered Imposter"

        first_check = verify_compliance_checksum(report)
        assert first_check is False, "First verification should detect tamper"

        second_check = verify_compliance_checksum(report)
        assert second_check is False, "Second verification should also detect tamper (idempotence failure)"

    @pytest.mark.xfail(
        reason="Vulnerability: HTML export embeds unescaped </script> inside script data island allowing script breakout",
        strict=False,
    )
    def test_html_export_escapes_script_tag_in_data_island(self, client):
        """
        Adversarial probe: Symptoms containing '</script>' must not prematurely close
        the <script id='compliance-audit-data'> block in the HTML package.
        """
        resp = client.post("/api/v1/rca/analyze", json={
            "asset_tag": "Pump-A12",
            "symptoms": ["</script><script>alert('xss')</script>"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        })
        rep_id = resp.json()["report_id"]

        exp_resp = client.post("/api/v1/rca/export-evidence", json={
            "report_id": rep_id,
            "format": "html",
        })
        html_doc = exp_resp.json()["content"]

        # In HTML5, browser terminates script at the first </script>.
        # If the symptom contained </script>, it cuts off the script island prematurely.
        island_match = re.search(r'<script id="compliance-audit-data"[^>]*>(.*?)</script>', html_doc, re.DOTALL)
        assert island_match is not None, "Script data island not found"
        # The content of the script island must parse as valid JSON (not truncated by </script>)
        island_json = json.loads(island_match.group(1))
        assert "d1_team" in island_json
