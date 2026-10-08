"""
Industrial Mind OS - Adversarial Challenge Suite for Certified Compliance Packaging
Location: backend/tests/test_compliance_adversarial_challenge.py

Empirical stress testing and adversarial challenge covering:
1. XSS injection attacks across all dynamic fields (problem description, symptoms,
   asset tags, containment actions, why-tree nodes, fishbone categories, citations,
   OEM deviations, sign-off blocks).
2. CSS print rules (@page letter portrait, @media print, page-break, avoid-break).
3. Certified audit headers and ISO/IATF/AIAG regulatory metadata.
4. JSON package validity, canonical deterministic formatting, and SHA-256 seal invariance.
5. API export endpoint edge cases, unsupported formats, and tamper detection.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from main import app
from api.rca_router import rca_report_store
from api.rca_schemas import (
    ContainmentAction,
    CorrectiveAction,
    EightDIncidentReport,
    ExportEvidenceRequest,
    FishboneBranch,
    FiveWhyNode,
    ProblemDescription,
    RCAAnalyzeRequest,
    TeamFormation,
    ValidationPlan,
)
from services.compliance_package import (
    build_audit_html,
    build_audit_json,
    compute_canonical_sha256,
    generate_compliance_package,
    verify_compliance_checksum,
)


@pytest.fixture(autouse=True)
def clean_store():
    """Ensure in-memory store is pristine before and after each test."""
    rca_report_store.clear()
    yield
    rca_report_store.clear()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# SECTION 1: XSS INJECTION CHALLENGE TESTS
# ==============================================================================

class TestXSSInjectionAttacks:
    """Adversarial testing against cross-site scripting vulnerabilities."""

    XSS_PAYLOADS = [
        '<script>alert("XSS_1")</script>',
        '<img src="x" onerror="alert(document.cookie)">',
        '<svg/onload=alert("SVG_XSS")>',
        '"><script>alert(1)</script>',
        '<iframe src="javascript:alert(1)"></iframe>',
        '"><svg onload=alert(1)>',
        '<body onload=alert(1)>',
        '<input type="text" autofocus onfocus="alert(1)">',
        '</script><script>alert("BREAKOUT")</script>',
        '&lt;script&gt;alert(1)&lt;/script&gt;',
        'javascript:/*--></title></style></textarea></script></xmp><svg/onload=\'+/"/+/onmouseover=1/+/[*///0=1//alert(1)]//\'>',
    ]

    def test_xss_in_asset_tag_properly_escaped(self):
        """Verifies malicious asset tags cannot execute raw HTML/scripts in visible body."""
        for payload in self.XSS_PAYLOADS:
            report_dict = {
                "report_id": "8D-XSS-ASSET",
                "asset_tag": f"Turbine-{payload}",
                "d2_problem": {"what": "Bearing failure", "equipment_tag": f"Turbine-{payload}"},
            }
            html_output = build_audit_html(report_dict)
            body_html = html_output[:html_output.find('<script id="compliance-audit-data"')]

            # Any angle brackets in asset tag must be escaped as &lt; / &gt; in the visible presentation
            assert f"Turbine-{payload}" not in body_html or "<" not in payload, f"Raw payload leaked in body for: {payload}"
            assert html.escape(f"Turbine-{payload}") in body_html

    def test_xss_in_problem_description_5w2h_escaped(self):
        """Verifies 5W2H problem description dimensions escape injection strings in visible body."""
        payload = '<script>document.location="http://evil.com"</script>'
        img_payload = '<img src=x onerror="fetch(\'/steal\')">'

        report_dict = {
            "report_id": "8D-XSS-5W2H",
            "asset_tag": "Pump-XSS",
            "d2_problem": {
                "incident_title": f"Exploit: {payload}",
                "what": f"Failure: {img_payload}",
                "where": 'Plant <b onmouseover="alert(1)">Alpha</b>',
                "when": '2026-10-07T00:00:00Z <script>alert("when")</script>',
                "who": 'Operator <iframe src="evil.html">',
                "why": 'Loss <svg onload=alert("why")>',
                "how": 'Telemetry <style>body{display:none;}</style>',
                "how_many": '10 units <details open ontoggle=alert(1)>',
                "operational_impact": 'Total outage <form action="evil.com"><input type="submit">',
            },
        }

        html_output = build_audit_html(report_dict)
        body_html = html_output[:html_output.find('<script id="compliance-audit-data"')]

        dangerous_tags = [
            '<script>document.location',
            '<img src=x onerror',
            '<b onmouseover',
            '<iframe src=',
            '<svg onload=',
            '<style>body{display:none;}</style>',
            '<details open ontoggle=',
            '<form action="evil.com"',
        ]
        for tag in dangerous_tags:
            assert tag not in body_html, f"Dangerous unescaped tag found in visible body: {tag}"

        # Confirm escaped variants are present
        assert html.escape(report_dict["d2_problem"]["incident_title"]) in body_html
        assert html.escape(report_dict["d2_problem"]["what"]) in body_html

    def test_xss_in_containment_actions_escaped(self):
        """Verifies D3 containment actions properly escape descriptions, owners, and IDs."""
        action_payload = 'Emergency stop <script>alert("ICA_XSS")</script>'
        owner_payload = 'Lead Tech <img src=x onerror=alert("owner")>'
        id_payload = 'ICA-<script>1</script>'
        status_payload = 'ACTIVE<svg/onload=alert(1)>'

        report_dict = {
            "report_id": "8D-XSS-ICA",
            "asset_tag": "Boiler-B01",
            "d3_containment": [
                {
                    "action_id": id_payload,
                    "action": action_payload,
                    "owner": owner_payload,
                    "status": status_payload,
                    "effectiveness_pct": 100.0,
                }
            ],
        }

        html_output = build_audit_html(report_dict)
        body_html = html_output[:html_output.find('<script id="compliance-audit-data"')]

        assert '<script>alert("ICA_XSS")</script>' not in body_html
        assert '<img src=x onerror=alert("owner")>' not in body_html
        assert '<svg/onload=alert(1)>' not in body_html
        assert html.escape(action_payload) in body_html
        assert html.escape(owner_payload) in body_html
        assert html.escape(id_payload) in body_html
        assert html.escape(status_payload) in body_html

    def test_xss_in_5why_tree_and_fishbone_branches(self):
        """Verifies D4 why nodes and fishbone categories escape malicious strings."""
        why_stmt = 'Bearing overheated <script>alert("WHY_FAIL")</script>'
        fishbone_cat = 'Machine <iframe src="xss"></iframe>'
        fishbone_cause = 'Lubrication breakdown <svg onload=alert("6M")>'

        report_dict = {
            "report_id": "8D-XSS-D4",
            "asset_tag": "Gen-01",
            "d4_root_causes": {
                "occurrence_root_cause": 'Primary fault <script>alert("OCC")</script>',
                "escape_root_cause": 'Detection failed <script>alert("ESC")</script>',
                "five_why_chain": [
                    {
                        "why_id": 'WHY-1<script>alert(1)</script>',
                        "level": 1,
                        "cause_statement": why_stmt,
                        "citation_ids": ['CITE-1<script>2</script>'],
                        "is_root_cause": False,
                    }
                ],
                "fishbone_analysis": {
                    "branches": [
                        {
                            "category": fishbone_cat,
                            "causes": [fishbone_cause],
                            "citation_ids": ['CITE-M1'],
                        }
                    ]
                },
            },
        }

        html_output = build_audit_html(report_dict)

        assert '<script>alert("WHY_FAIL")</script>' not in html_output
        assert '<script>alert("OCC")</script>' not in html_output
        assert '<script>alert("ESC")</script>' not in html_output
        assert '<iframe src="xss"></iframe>' not in html_output
        assert '<svg onload=alert("6M")>' not in html_output
        assert html.escape(why_stmt) in html_output
        assert html.escape(fishbone_cat) in html_output
        assert html.escape(fishbone_cause) in html_output

    def test_xss_in_citations_and_signoff_fields(self):
        """Verifies documentary citations and D8 sign-off notes are escaped."""
        cite_doc = 'Manual <script>alert("DOC")</script>.pdf'
        cite_excerpt = 'Exceeded tolerance <img src=1 onerror=alert("EXCERPT")>'
        approver = 'Dr. Vance <script>alert("APPROVER")</script>'
        notes = 'Award given <svg onload=alert("NOTES")>'

        report_dict = {
            "report_id": "8D-XSS-D8",
            "asset_tag": "Comp-03",
            "citations": [
                {
                    "citation_id": "CITE-XSS-1",
                    "source_doc": cite_doc,
                    "confidence": 0.95,
                    "excerpt": cite_excerpt,
                }
            ],
            "d8_recognition": {
                "approver_name": approver,
                "approver_role": "Director",
                "recognition_notes": notes,
                "lessons_learned": "Never trust input <script>alert(1)</script>",
            },
        }

        html_output = build_audit_html(report_dict)

        assert '<script>alert("DOC")</script>' not in html_output
        assert '<img src=1 onerror=alert("EXCERPT")>' not in html_output
        assert '<script>alert("APPROVER")</script>' not in html_output
        assert '<svg onload=alert("NOTES")>' not in html_output
        assert html.escape(cite_doc) in html_output
        assert html.escape(cite_excerpt) in html_output
        assert html.escape(approver) in html_output
        assert html.escape(notes) in html_output

    def test_script_data_island_breakout_vulnerability(self):
        """
        Adversarial test: checks if an attacker injecting '</script><script>alert(1)</script>'
        into a problem description or symptom causes the HTML parser to prematurely close
        the data island <script> tag and create a new executable script element.
        """
        from html.parser import HTMLParser

        class ScriptTagCollector(HTMLParser):
            def __init__(self):
                super().__init__()
                self.scripts = []

            def handle_starttag(self, tag, attrs):
                if tag.lower() == "script":
                    self.scripts.append(dict(attrs))

        payload = '</script><script id=injected_exploit>alert("PWNED")</script>'
        report_dict = {
            "report_id": "8D-XSS-BREAKOUT",
            "asset_tag": "Pump-A12",
            "d2_problem": {
                "what": f"Mechanical seal rupture: {payload}",
            },
        }

        html_doc = build_audit_html(report_dict)

        collector = ScriptTagCollector()
        collector.feed(html_doc)
        print("COLLECTED SCRIPTS:", collector.scripts)

        injected = [s for s in collector.scripts if s.get("id") != "compliance-audit-data"]

        # There should only be the official data island script tag
        assert len(collector.scripts) == 1, (
            f"VULNERABILITY CONFIRMED: Embedded canonical JSON inside <script id='compliance-audit-data'> "
            f"allowed raw '</script>' breakout resulting in {len(collector.scripts)} script tags: {collector.scripts}"
        )
        assert len(injected) == 0, (
            f"VULNERABILITY CONFIRMED: Embedded canonical JSON inside <script id='compliance-audit-data'> "
            f"allowed raw '</script>' breakout resulting in {len(collector.scripts)} script tags: {collector.scripts}"
        )

        # Verify that data island parses as clean JSON and reconstructs the uncorrupted string
        match = re.search(r'<script id="compliance-audit-data"[^>]*>(.*?)</script>', html_doc, re.DOTALL)
        assert match is not None, "Data island script tag missing from HTML output"
        parsed_json = json.loads(match.group(1).strip())
        assert parsed_json["d2_problem"]["what"] == f"Mechanical seal rupture: {payload}"

    def test_raw_dict_numeric_field_injection_escaped(self):
        """
        Adversarial test: checks that non-numeric injection strings in numeric fields
        (severity_score, occurrence_score, detection_score, rpn_score, effectiveness_pct,
        deviation_percent, grounding_ratio) in raw dictionaries do not execute or leak unescaped tags.
        """
        sev_payload = '<script>alert("SEV")</script>'
        occ_payload = '<img src=x onerror=alert("OCC")>'
        det_payload = '<svg onload=alert("DET")>'
        rpn_payload = '<script>alert("RPN")</script>'
        eff_payload = '<script>alert("EFF")</script>'
        dev_payload = '<script>alert("DEV")</script>'
        gr_payload = '<script>alert("GR")</script>'

        report_dict = {
            "report_id": "8D-NUM-XSS",
            "asset_tag": "Pump-NUM",
            "severity_score": sev_payload,
            "occurrence_score": occ_payload,
            "detection_score": det_payload,
            "rpn_score": rpn_payload,
            "d3_containment": [
                {
                    "action_id": "ICA-01",
                    "action": "Inspect valve",
                    "owner": "Tech",
                    "effectiveness_pct": eff_payload,
                    "status": "DONE",
                }
            ],
            "d4_root_causes": {
                "citation_grounding_ratio": gr_payload,
            },
            "d7_preventative_controls": {
                "oem_deviations": [
                    {
                        "parameter_name": "Pressure",
                        "oem_envelope_limit": 10.0,
                        "actual_incident_value": 15.0,
                        "deviation_percent": dev_payload,
                        "severity_level": "CRITICAL",
                    }
                ]
            },
        }

        html_doc = build_audit_html(report_dict)
        body_html = html_doc[:html_doc.find('<script id="compliance-audit-data"')]

        for payload in [sev_payload, occ_payload, det_payload, rpn_payload, eff_payload, dev_payload, gr_payload]:
            assert payload not in body_html, f"Unescaped payload found in body: {payload}"


# ==============================================================================
# SECTION 2: CSS PRINT RULES & AUDIT HEADER VALIDATIONS
# ==============================================================================

class TestCSSPrintRulesAndAuditHeaders:
    """Verifies compliance with physical print standards and regulatory audit headers."""

    def test_css_page_letter_portrait_rule_present(self):
        """Verifies @page contains 'size: letter portrait;' and print margins."""
        report = {"report_id": "8D-CSS-01", "asset_tag": "Pump-A12"}
        html_doc = build_audit_html(report)

        # Must have @page declaration
        assert "@page" in html_doc
        # Check size: letter portrait
        assert re.search(r"@page\s*\{[^}]*size\s*:\s*letter\s+portrait\s*;", html_doc, re.IGNORECASE) is not None
        # Check margin specification
        assert re.search(r"margin\s*:\s*15mm\s+18mm\s*;", html_doc) is not None

    def test_media_print_rules_and_break_controls(self):
        """Verifies @media print block with page-break controls and color adjustments."""
        report = {"report_id": "8D-CSS-02", "asset_tag": "Turbine-T01"}
        html_doc = build_audit_html(report)

        assert "@media print" in html_doc
        assert "print-color-adjust: exact" in html_doc
        assert "-webkit-print-color-adjust: exact" in html_doc
        assert ".page-break" in html_doc
        assert "page-break-after: always" in html_doc or "break-after: page" in html_doc
        assert ".avoid-break" in html_doc
        assert "page-break-inside: avoid" in html_doc or "break-inside: avoid" in html_doc

    def test_audit_header_elements_and_metadata(self):
        """Verifies audit header container, checksum data attribute, and standards citations."""
        report = {"report_id": "8D-HDR-01", "asset_tag": "Boiler-09"}
        html_doc = build_audit_html(report)

        # Meta tags
        assert '<meta name="x-compliance-standard" content="ISO 9001:2015, IATF 16949:2016, AIAG 8D">' in html_doc
        assert '<meta name="x-compliance-checksum-sha256"' in html_doc

        # Audit header div with data-checksum
        assert 'class="audit-header"' in html_doc
        match = re.search(r'<div class="audit-header" data-checksum="([0-9a-fA-F]{64})">', html_doc)
        assert match is not None, "audit-header element must contain valid 64-char hex data-checksum attribute"

        # SHA seal paragraph
        assert 'class="sha-seal"' in html_doc
        assert f"Certified SHA-256 Checksum: {match.group(1)}" in html_doc

        # Regulatory standards in subtitle
        assert "ISO 9001:2015 Clause 10.2" in html_doc
        assert "IATF 16949:2016 Section 10.2.3" in html_doc
        assert "AIAG 8D Standard" in html_doc

    def test_quality_signoff_block_d8_structure(self):
        """Verifies D8 Quality Manager certification sign-off block with signatures."""
        report = {"report_id": "8D-SIGN-01", "asset_tag": "Comp-C1"}
        html_doc = build_audit_html(report)

        assert "class=\"signoff-card" in html_doc
        assert "D8: Quality Sign-Off & Official Audit Certification" in html_doc
        assert "Authorized Signatory:" in html_doc
        assert "Quality Assurance Manager Signature" in html_doc
        assert "Plant Operations Director Signature" in html_doc
        assert "Digital Seal:" in html_doc


# ==============================================================================
# SECTION 3: JSON PACKAGE VALIDITY, CANONICAL FORMATTING & SHA-256 SEAL
# ==============================================================================

class TestJSONPackageValidityAndSHA256Invariance:
    """Verifies deterministic JSON serialization, schema adherence, and SHA-256 seal invariance."""

    def test_json_validity_and_root_keys(self):
        """Verifies JSON output parses cleanly and contains all core root keys."""
        report = {
            "report_id": "8D-JSON-01",
            "asset_tag": "Pump-A12",
            "severity_score": 8,
            "d1_team": {"leader": "Dr. Vance", "members": ["Tech A", "Tech B"]},
            "d2_problem": {"what": "Cavitation"},
        }

        json_str = build_audit_json(report)
        parsed = json.loads(json_str)

        assert isinstance(parsed, dict)
        assert parsed["report_id"] == "8D-JSON-01"
        assert parsed["asset_tag"] == "Pump-A12"
        assert parsed["severity_score"] == 8
        assert "d1_team" in parsed
        assert "checksum_sha256" in parsed
        assert len(parsed["checksum_sha256"]) == 64

    def test_canonical_deterministic_formatting(self):
        """Verifies canonical JSON produces byte-for-byte identical output regardless of dict key order."""
        report_perm1 = {
            "report_id": "8D-DET-01",
            "asset_tag": "Turbine-T1",
            "severity_score": 7,
            "created_at": "2026-10-07T00:00:00Z",
        }
        report_perm2 = {
            "created_at": "2026-10-07T00:00:00Z",
            "severity_score": 7,
            "report_id": "8D-DET-01",
            "asset_tag": "Turbine-T1",
        }

        hash1 = compute_canonical_sha256(report_perm1)
        hash2 = compute_canonical_sha256(report_perm2)

        assert hash1 == hash2, "Canonical SHA-256 must be invariant to dict key insertion order"
        assert len(hash1) == 64

    def test_sha256_seal_invariance_verification(self):
        """Verifies verify_compliance_checksum validates pristine reports and rejects tampering."""
        report = {
            "report_id": "8D-SEAL-01",
            "asset_tag": "Motor-M1",
            "severity_score": 5,
        }
        computed_hash = compute_canonical_sha256(report)
        report["checksum_sha256"] = computed_hash

        # Verification must pass
        assert verify_compliance_checksum(report) is True

        # Tampering with any field must fail verification (avalanche effect)
        tampered_report = dict(report)
        tampered_report["severity_score"] = 6
        assert verify_compliance_checksum(tampered_report) is False

        # Tampering with asset_tag
        tampered_asset = dict(report)
        tampered_asset["asset_tag"] = "Motor-M2"
        assert verify_compliance_checksum(tampered_asset) is False

    def test_generate_compliance_package_syncs_checksum(self):
        """Verifies generate_compliance_package returns consistent hash across HTML and JSON."""
        report = {
            "report_id": "8D-SYNC-01",
            "asset_tag": "Exchanger-E1",
            "severity_score": 6,
        }

        json_content, json_hash, json_filename = generate_compliance_package(report, format="json")
        html_content, html_hash, html_filename = generate_compliance_package(report, format="html")

        assert json_hash == html_hash
        assert json_filename == "8D-SYNC-01_evidence_package.json"
        assert html_filename == "8D-SYNC-01_compliance_audit.html"
        assert json_hash in html_content


# ==============================================================================
# SECTION 4: EXPORT ENDPOINT API VERIFICATION
# ==============================================================================

class TestExportEvidenceEndpointAPI:
    """Verifies /api/v1/rca/export-evidence endpoint contracts and error paths."""

    def test_export_evidence_case_insensitive_format(self, client):
        """Verifies format parameter handles uppercase and whitespace ('HTML', ' JSON ')."""
        # Seed report via analyze endpoint
        analyze_payload = {
            "asset_tag": "Pump-A12",
            "symptoms": ["mechanical seal failure", "vibration excursion 5.8 mm/s"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
            "telemetry_data": {"vibration_mm_s": 5.8, "temperature_c": 62.0},
        }
        res_analyze = client.post("/api/v1/rca/analyze", json=analyze_payload)
        assert res_analyze.status_code == 200
        rep_id = res_analyze.json()["report_id"]

        # Test uppercase "HTML"
        res_html = client.post(
            "/api/v1/rca/export-evidence",
            json={"report_id": rep_id, "format": "HTML"},
        )
        assert res_html.status_code == 200
        data_html = res_html.json()
        assert data_html["filename"].endswith(".html")
        assert "<!DOCTYPE html>" in data_html["content"]

        # Test " JSON " with whitespace
        res_json = client.post(
            "/api/v1/rca/export-evidence",
            json={"report_id": rep_id, "format": "  JSON  "},
        )
        assert res_json.status_code == 200
        data_json = res_json.json()
        assert data_json["filename"].endswith(".json")
        parsed = json.loads(data_json["content"])
        assert parsed["report_id"] == rep_id

    def test_export_evidence_unsupported_formats_return_400(self, client):
        """Verifies unsupported formats (xml, pdf, csv, yaml) return HTTP 400 Bad Request."""
        for bad_fmt in ["xml", "pdf", "csv", "yaml", "doc"]:
            res = client.post(
                "/api/v1/rca/export-evidence",
                json={"report_id": "8D-ANY", "format": bad_fmt},
            )
            assert res.status_code == 400, f"Format '{bad_fmt}' should yield HTTP 400"
            err_detail = res.json().get("detail", "")
            assert "Unsupported format" in err_detail or "must be 'html' or 'json'" in err_detail

    def test_export_evidence_missing_report_id_returns_422(self, client):
        """Verifies missing report_id field yields HTTP 422 Unprocessable Entity."""
        res = client.post(
            "/api/v1/rca/export-evidence",
            json={"format": "html"},
        )
        assert res.status_code == 422

    def test_export_evidence_xss_payloads_in_analyze_properly_sanitized(self, client):
        """Verifies end-to-end flow: analyzing with XSS in symptoms exports sanitized HTML."""
        xss_symptoms = [
            'seal leak <script>alert("ANALYZE_XSS")</script>',
            'high vibration <img src=x onerror=alert(1)>',
        ]
        analyze_payload = {
            "asset_tag": 'Pump-XSS<svg/onload=alert("TAG")>',
            "symptoms": xss_symptoms,
            "incident_timestamp": "2023-11-04T08:00:00Z",
            "telemetry_data": {"vibration_mm_s": 5.8},
        }

        res_analyze = client.post("/api/v1/rca/analyze", json=analyze_payload)
        assert res_analyze.status_code == 200
        rep_id = res_analyze.json()["report_id"]

        # Export HTML
        res_export = client.post(
            "/api/v1/rca/export-evidence",
            json={"report_id": rep_id, "format": "html"},
        )
        assert res_export.status_code == 200
        html_body = res_export.json()["content"]
        visible_body = html_body[:html_body.find('<script id="compliance-audit-data"')]

        # Confirm no unescaped execution vectors in visible HTML
        assert '<script>alert("ANALYZE_XSS")</script>' not in visible_body
        assert '<img src=x onerror=alert(1)>' not in visible_body
        assert '<svg/onload=alert("TAG")>' not in visible_body

        # Confirm presence of escaped tokens
        assert '&lt;script&gt;' in visible_body or html.escape('seal leak <script>alert("ANALYZE_XSS")</script>') in visible_body
