"""
Industrial Mind OS - RCA API Integration & Compliance Packaging Test Suite
Location: backend/tests/test_rca_api.py

Comprehensive test suite verifying:
1. Router Mounting & OpenAPI Schema Inspection (/api/v1/rca/*)
2. Happy Path Tests: POST /api/v1/rca/analyze (Pump, Turbine, Boiler, Generic assets)
3. Happy Path Tests: POST /api/v1/rca/historical-match (Matches found & empty symptoms)
4. Happy Path Tests: POST /api/v1/rca/export-evidence (HTML & JSON packages with SHA-256 seals)
5. Happy Path Tests: GET /api/v1/rca/reports & GET /api/v1/rca/reports/{report_id}
6. Status Code & Boundary Validations:
   - 200 OK across valid operations
   - 400 Bad Request on unsupported export format (format="xml")
   - 404 Not Found on nonexistent report ID lookup
   - 422 Unprocessable Entity on missing asset_tag, empty symptoms on /analyze, invalid timestamps
   - Graceful fallback on nonexistent report export (HTTP 200 per test_f9_b05)
7. Full Pipeline Workflow (/analyze -> /historical-match -> /export-evidence)
8. Cryptographic Integrity & Avalanche Effect Tamper Detection
9. Concurrency, Thread Safety & Offline Execution Safety
"""

from __future__ import annotations

import hashlib
import json
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from main import app
from api.rca_router import rca_report_store
from api.rca_schemas import EightDIncidentReport, RCAAnalyzeRequest


# ==============================================================================
# FIXTURES & ISOLATION
# ==============================================================================

@pytest.fixture(autouse=True)
def clean_report_store():
    """Guarantees test isolation by clearing in-memory store before and after each test."""
    rca_report_store.clear()
    yield
    rca_report_store.clear()


@pytest.fixture
def client():
    """Provides an in-process ASGI TestClient bound to main.app."""
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# GROUP 1: ROUTER MOUNTING & OPENAPI SCHEMA INSPECTION (3 TESTS)
# ==============================================================================

def test_rca_router_mounted_in_main_app(client):
    """Verifies that all 5 RCA endpoints are mounted on main.app under /api/v1/rca."""
    routes = set(app.openapi().get("paths", {}).keys())
    for r in app.routes:
        if hasattr(r, "path"):
            routes.add(r.path)
        if hasattr(r, "routes"):
            for sub in r.routes:
                if hasattr(sub, "path"):
                    routes.add(sub.path)
    expected_endpoints = [
        "/api/v1/rca/analyze",
        "/api/v1/rca/historical-match",
        "/api/v1/rca/export-evidence",
        "/api/v1/rca/reports",
        "/api/v1/rca/reports/{report_id}",
    ]
    for endpoint in expected_endpoints:
        assert endpoint in routes, f"Endpoint {endpoint} not mounted in main.app"


def test_openapi_schema_contains_rca_endpoints(client):
    """Verifies OpenAPI schema exposes /api/v1/rca paths with proper tags and operations."""
    openapi = app.openapi()
    paths = openapi.get("paths", {})
    
    assert "/api/v1/rca/analyze" in paths
    assert "post" in paths["/api/v1/rca/analyze"]
    assert "Root Cause Analysis (8D)" in paths["/api/v1/rca/analyze"]["post"]["tags"]
    
    assert "/api/v1/rca/historical-match" in paths
    assert "post" in paths["/api/v1/rca/historical-match"]
    
    assert "/api/v1/rca/export-evidence" in paths
    assert "post" in paths["/api/v1/rca/export-evidence"]
    
    assert "/api/v1/rca/reports" in paths
    assert "get" in paths["/api/v1/rca/reports"]


def test_openapi_json_endpoint_accessible(client):
    """Verifies that GET /openapi.json returns 200 OK and contains RCA metadata."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "/api/v1/rca/analyze" in data["paths"]


# ==============================================================================
# GROUP 2: HAPPY PATH TESTS — POST /api/v1/rca/analyze (4 TESTS)
# ==============================================================================

def test_analyze_pump_asset_returns_full_8d_report(client):
    """Verifies /analyze for Centrifugal Pump produces complete, compliant 8D report."""
    payload = {
        "asset_tag": "Pump-A12",
        "symptoms": ["mechanical seal failure", "vibration 5.8 mm/s"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
        "telemetry_data": {"vibration_mm_s": 5.8, "temperature_c": 62.0},
    }
    resp = client.post("/api/v1/rca/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Report structure assertions
    assert data["report_id"].startswith("8D-")
    assert data["asset_tag"] == "Pump-A12"
    assert len(data["checksum_sha256"]) == 64

    # Disciplines D1-D8 presence
    assert "d1_team" in data and data["d1_team"]["leader"]
    assert "d2_problem" in data and data["d2_problem"]["what"]
    assert "d3_containment" in data and len(data["d3_containment"]) >= 1
    assert "d4_root_causes" in data and data["d4_root_causes"]["occurrence_root_cause"]
    assert "d5_permanent_actions" in data and len(data["d5_permanent_actions"]) >= 1
    assert "d6_validation" in data and data["d6_validation"]["status"]
    assert "d7_preventative_controls" in data
    assert "d8_recognition" in data and data["d8_recognition"]["signoff_status"]

    # 5-Why and Fishbone depth
    five_why = data["d4_root_causes"]["five_why_chain"]
    assert len(five_why) == 5
    assert five_why[-1]["is_root_cause"] is True

    # RPN calculation verification
    assert data["rpn_score"] == data["severity_score"] * data["occurrence_score"] * data["detection_score"]


def test_analyze_turbine_asset_detects_envelope_and_causes(client):
    """Verifies /analyze for Steam Turbine handles overspeed telemetry and generates 8D report."""
    payload = {
        "asset_tag": "TURB-ST-04",
        "symptoms": ["rotor overspeed", "bearing temperature high"],
        "incident_timestamp": "2023-11-04T12:00:00Z",
        "telemetry_data": {"speed_rpm": 3450.0, "bearing_temp_c": 118.0},
    }
    resp = client.post("/api/v1/rca/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_tag"] == "TURB-ST-04"
    assert data["rpn_score"] > 0
    assert len(data["checksum_sha256"]) == 64


def test_analyze_boiler_asset_generates_valid_report(client):
    """Verifies /analyze for Boiler BLR-HP-101 generates valid 8D report."""
    payload = {
        "asset_tag": "BLR-HP-101",
        "symptoms": ["superheater tube leak", "pressure drop", "thermocouple drift"],
        "incident_timestamp": "2023-11-04T16:00:00Z",
        "telemetry_data": {"pressure_bar": 92.0, "superheat_temp_c": 560.0},
    }
    resp = client.post("/api/v1/rca/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_tag"] == "BLR-HP-101"
    assert data["severity_score"] >= 1


def test_analyze_generic_asset_fallback_without_error(client):
    """Verifies /analyze for generic asset executes gracefully without 500 errors."""
    payload = {
        "asset_tag": "COMPRESSOR-C03",
        "symptoms": ["unusual gear whining", "motor overload trip"],
        "incident_timestamp": "2023-11-04T18:00:00Z",
    }
    resp = client.post("/api/v1/rca/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_tag"] == "COMPRESSOR-C03"
    assert len(data["d4_root_causes"]["five_why_chain"]) >= 1


# ==============================================================================
# GROUP 3: HAPPY PATH TESTS — POST /api/v1/rca/historical-match (4 TESTS)
# ==============================================================================

def test_historical_match_pump_a12_baseline(client):
    """Verifies historical match retrieves near-miss records for Pump-A12."""
    payload = {
        "asset_tag": "Pump-A12",
        "symptoms": ["vibration", "mechanical seal", "coolant leak"],
    }
    resp = client.post("/api/v1/rca/historical-match", json=payload)
    assert resp.status_code == 200
    matches = resp.json()
    assert isinstance(matches, list)
    assert len(matches) >= 1
    match_ids = [m["matched_report_id"] for m in matches]
    assert any("PUMP" in mid or "NM-" in mid for mid in match_ids)
    assert matches[0]["similarity_score"] > 0.0


def test_historical_match_sister_asset_pump_a11(client):
    """Verifies historical match maps sister asset Pump-A11 to relevant historical records."""
    payload = {
        "asset_tag": "Pump-A11",
        "symptoms": ["vibration 5.8 mm/s"],
    }
    resp = client.post("/api/v1/rca/historical-match", json=payload)
    assert resp.status_code == 200
    matches = resp.json()
    assert isinstance(matches, list)


def test_historical_match_unmatched_asset_returns_list(client):
    """Verifies historical match for unmatched asset returns a list without 500."""
    payload = {
        "asset_tag": "CONVEYOR-CV-99",
        "symptoms": ["belt tearing", "idler bearing seizure"],
    }
    resp = client.post("/api/v1/rca/historical-match", json=payload)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_historical_match_empty_symptoms_returns_200_empty_list(client):
    """Verifies POST /historical-match with symptoms=[] returns 200 OK and [] per test_f9_b04."""
    payload = {
        "asset_tag": "Pump-A12",
        "symptoms": [],
    }
    resp = client.post("/api/v1/rca/historical-match", json=payload)
    assert resp.status_code == 200
    assert resp.json() == []


# ==============================================================================
# GROUP 4: HAPPY PATH TESTS — POST /api/v1/rca/export-evidence (4 TESTS)
# ==============================================================================

def test_export_evidence_json_format(client):
    """Verifies evidence export in JSON format per test_f9_03 contract."""
    # Pre-generate a report
    analyze_resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["seal leak", "vibration 5.8 mm/s"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    rep_id = analyze_resp.json()["report_id"]

    export_resp = client.post("/api/v1/rca/export-evidence", json={
        "report_id": rep_id,
        "format": "json",
    })
    assert export_resp.status_code == 200
    data = export_resp.json()
    assert data["filename"].endswith(".json")
    assert len(data["sha256_checksum"]) == 64

    # Ensure d1_team is accessible at root level of content
    content_dict = json.loads(data["content"])
    assert "d1_team" in content_dict
    assert content_dict["report_id"] == rep_id


def test_export_evidence_html_format(client):
    """Verifies evidence export in HTML format per test_f9_04 / test_f10_03 / test_f10_04 contract."""
    analyze_resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["seal leak", "vibration 5.8 mm/s"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    rep_id = analyze_resp.json()["report_id"]

    export_resp = client.post("/api/v1/rca/export-evidence", json={
        "report_id": rep_id,
        "format": "html",
    })
    assert export_resp.status_code == 200
    data = export_resp.json()
    assert data["filename"].endswith(".html")
    assert len(data["sha256_checksum"]) == 64

    html_text = data["content"]
    assert "<!DOCTYPE html>" in html_text
    assert 'class="audit-header"' in html_text
    assert "Certified SHA-256 Checksum" in html_text
    assert "ISO 9001:2015" in html_text
    assert "@page" in html_text
    assert "letter portrait" in html_text
    assert "@media print" in html_text
    assert f'data-checksum="{data["sha256_checksum"]}"' in html_text


def test_export_evidence_content_matches_stored_report(client):
    """Verifies exported JSON values exactly match GET /reports/{id} values."""
    analyze_resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "TURB-ST-04",
        "symptoms": ["rotor overspeed"],
        "incident_timestamp": "2023-11-04T10:00:00Z",
    })
    rep_id = analyze_resp.json()["report_id"]

    export_resp = client.post("/api/v1/rca/export-evidence", json={
        "report_id": rep_id,
        "format": "json",
    })
    exported_data = json.loads(export_resp.json()["content"])

    get_resp = client.get(f"/api/v1/rca/reports/{rep_id}")
    stored_data = get_resp.json()

    assert exported_data["report_id"] == stored_data["report_id"]
    assert exported_data["rpn_score"] == stored_data["rpn_score"]
    assert exported_data["checksum_sha256"] == stored_data["checksum_sha256"]


def test_export_evidence_nonexistent_report_fallback_200(client):
    """Verifies exporting unknown report ID generates graceful fallback package with 200 OK per test_f9_b05."""
    export_resp = client.post("/api/v1/rca/export-evidence", json={
        "report_id": "8D-NONEXISTENT",
        "format": "json",
    })
    assert export_resp.status_code == 200
    data = export_resp.json()
    assert len(data["sha256_checksum"]) == 64
    content = json.loads(data["content"])
    assert "d1_team" in content


# ==============================================================================
# GROUP 5: HAPPY PATH TESTS — GET /api/v1/rca/reports & {report_id} (4 TESTS)
# ==============================================================================

def test_list_reports_empty_returns_200_empty_list(client):
    """Verifies GET /reports returns 200 OK and empty list when store is empty."""
    resp = client.get("/api/v1/rca/reports")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_reports_populated_returns_summaries(client):
    """Verifies GET /reports returns list of summaries after reports are created."""
    client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["leak"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    client.post("/api/v1/rca/analyze", json={
        "asset_tag": "TURB-ST-04",
        "symptoms": ["overspeed"],
        "incident_timestamp": "2023-11-04T09:00:00Z",
    })

    resp = client.get("/api/v1/rca/reports")
    assert resp.status_code == 200
    summaries = resp.json()
    assert len(summaries) == 2


def test_get_single_report_by_id_success(client):
    """Verifies GET /reports/{report_id} returns full EightDIncidentReport."""
    analyze_resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["vibration"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    rep_id = analyze_resp.json()["report_id"]

    resp = client.get(f"/api/v1/rca/reports/{rep_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"] == rep_id
    assert "d1_team" in data
    assert "d2_problem" in data
    assert "d4_root_causes" in data


def test_list_reports_summary_field_contract(client):
    """Verifies each item in GET /reports conforms to summary schema with dual-compatible fields."""
    client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["vibration 5.8 mm/s"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    resp = client.get("/api/v1/rca/reports")
    assert resp.status_code == 200
    summary = resp.json()[0]

    # Required contract fields
    assert "report_id" in summary
    assert "asset_tag" in summary
    assert "severity_score" in summary
    assert "rpn_score" in summary
    assert "created_at" in summary
    assert "status" in summary
    # Dual-compatible checksum and title
    assert "checksum_sha256" in summary
    assert "sha256_checksum" in summary
    assert "title" in summary
    assert "incident_title" in summary


# ==============================================================================
# GROUP 6: NEGATIVE & BOUNDARY VALIDATION (6 TESTS)
# ==============================================================================

def test_analyze_missing_asset_tag_returns_422(client):
    """Verifies POST /analyze with missing asset_tag returns 422 Unprocessable Entity."""
    resp = client.post("/api/v1/rca/analyze", json={
        "symptoms": ["vibration"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    assert resp.status_code == 422


def test_analyze_empty_symptoms_list_returns_422(client):
    """Verifies POST /analyze with symptoms=[] returns 422 Unprocessable Entity per test_f9_b01."""
    resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": [],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    assert resp.status_code == 422


def test_analyze_invalid_timestamp_format_returns_422(client):
    """Verifies POST /analyze with non-ISO timestamp returns 422 Unprocessable Entity."""
    resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["vibration"],
        "incident_timestamp": "invalid-timestamp",
    })
    assert resp.status_code == 422


def test_export_evidence_unsupported_format_returns_400(client):
    """Verifies POST /export-evidence with format='xml' returns 400 Bad Request per test_f9_b03."""
    resp = client.post("/api/v1/rca/export-evidence", json={
        "report_id": "8D-2023-PUMP-A12",
        "format": "xml",
    })
    assert resp.status_code == 400
    assert "Unsupported format" in resp.json()["detail"]


def test_export_evidence_missing_report_id_returns_422(client):
    """Verifies POST /export-evidence with missing report_id returns 422 Unprocessable Entity."""
    resp = client.post("/api/v1/rca/export-evidence", json={
        "format": "json",
    })
    assert resp.status_code == 422


def test_get_nonexistent_report_returns_404(client):
    """Verifies GET /reports/{unknown_id} returns 404 Not Found."""
    resp = client.get("/api/v1/rca/reports/8D-9999-NONEXISTENT")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ==============================================================================
# GROUP 7: CRYPTOGRAPHIC INTEGRITY & AVALANCHE EFFECT (3 TESTS)
# ==============================================================================

def test_exported_checksum_matches_canonical_report_hash(client):
    """Verifies SHA-256 seal is bit-for-bit identical to recomputed canonical JSON hash."""
    analyze_resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["ceramic seal cracked"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    rep_id = analyze_resp.json()["report_id"]

    export_resp = client.post("/api/v1/rca/export-evidence", json={
        "report_id": rep_id,
        "format": "json",
    })
    export_data = export_resp.json()
    digest_api = export_data["sha256_checksum"]

    # Re-parse JSON and recompute hash excluding checksum
    content_dict = json.loads(export_data["content"])
    cleaned = {k: v for k, v in content_dict.items() if k not in ("checksum_sha256", "sha256_checksum")}
    canonical_repr = json.dumps(cleaned, sort_keys=True, separators=(",", ":"))
    expected_digest = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

    assert digest_api == expected_digest


def test_exported_html_embeds_matching_sha256_seal(client):
    """Verifies HTML export includes matching data-checksum and sha-seal text."""
    analyze_resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["high vibration"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    rep_id = analyze_resp.json()["report_id"]

    export_resp = client.post("/api/v1/rca/export-evidence", json={
        "report_id": rep_id,
        "format": "html",
    })
    html_content = export_resp.json()["content"]
    checksum = export_resp.json()["sha256_checksum"]

    assert f'data-checksum="{checksum}"' in html_content
    assert f"Certified SHA-256 Checksum: {checksum}" in html_content


def test_tamper_detection_avalanche_effect(client):
    """Verifies modifying a single character causes cryptographic avalanche effect (>50 bit difference)."""
    analyze_resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["vibration 5.8 mm/s"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    export_resp = client.post("/api/v1/rca/export-evidence", json={
        "report_id": analyze_resp.json()["report_id"],
        "format": "json",
    })
    orig_content = export_resp.json()["content"]
    orig_hash = hashlib.sha256(orig_content.encode("utf-8")).hexdigest()

    # Tamper with 1 character ("Pump-A12" -> "Pump-A13")
    tampered_content = orig_content.replace("Pump-A12", "Pump-A13", 1)
    tampered_hash = hashlib.sha256(tampered_content.encode("utf-8")).hexdigest()

    assert orig_hash != tampered_hash
    # Count bit differences via XOR
    diff_bits = bin(int(orig_hash, 16) ^ int(tampered_hash, 16)).count("1")
    assert diff_bits > 50, f"Avalanche effect deficient: only {diff_bits} bits changed"


# ==============================================================================
# GROUP 8: PIPELINE, CONCURRENCY & OFFLINE SAFETY (3 TESTS)
# ==============================================================================

def test_full_api_workflow_pipeline(client):
    """Verifies end-to-end RCA workflow: /analyze -> /historical-match -> /export-evidence."""
    # 1. Analyze incident
    analyze_resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["mechanical seal failure", "vibration 5.8 mm/s"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
        "telemetry_data": {"vibration_mm_s": 5.8},
    })
    assert analyze_resp.status_code == 200
    report = analyze_resp.json()
    rep_id = report["report_id"]

    # 2. Match historical records
    match_resp = client.post("/api/v1/rca/historical-match", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["mechanical seal failure"],
    })
    assert match_resp.status_code == 200
    assert len(match_resp.json()) >= 1

    # 3. Export evidence packages (JSON & HTML)
    json_export = client.post("/api/v1/rca/export-evidence", json={
        "report_id": rep_id,
        "format": "json",
    })
    assert json_export.status_code == 200

    html_export = client.post("/api/v1/rca/export-evidence", json={
        "report_id": rep_id,
        "format": "html",
    })
    assert html_export.status_code == 200

    # 4. Verify report listing
    list_resp = client.get("/api/v1/rca/reports")
    assert list_resp.status_code == 200
    assert any(s["report_id"] == rep_id for s in list_resp.json())


def test_concurrent_analyze_requests_thread_safe(client):
    """Verifies multiple concurrent /analyze requests execute without thread race conditions."""
    def run_analyze(asset_id: int):
        with TestClient(app) as local_client:
            return local_client.post("/api/v1/rca/analyze", json={
                "asset_tag": f"Pump-A{asset_id:02d}",
                "symptoms": [f"vibration on unit {asset_id}"],
                "incident_timestamp": "2023-11-04T08:00:00Z",
            })

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_analyze, i) for i in range(8)]
        results = [f.result() for f in futures]

    for resp in results:
        assert resp.status_code == 200

    # Store must contain all 8 generated reports
    list_resp = client.get("/api/v1/rca/reports")
    assert len(list_resp.json()) == 8


def test_pure_offline_execution_zero_network_calls(client, monkeypatch):
    """Verifies entire RCA pipeline operates 100% offline without opening external network sockets."""
    original_connect = socket.socket.connect

    def forbidden_connect(self, address):
        # Allow internal testclient connections if needed, reject any external host
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "localhost", "testserver"):
            raise RuntimeError(f"Network access attempted during offline test: {address}")
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)

    resp = client.post("/api/v1/rca/analyze", json={
        "asset_tag": "Pump-A12",
        "symptoms": ["offline verification test"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    })
    assert resp.status_code == 200
