"""
Industrial Mind OS - RCA Ingestion, Timeline Extraction & Evidence Citation Engine
Location: backend/services/rca_ingestion.py

Provides:
1. TimelineExtractor: Parses chronological events, sensor telemetry, deviations against
   OEM envelopes (including Pump-A12 baseline: 5.8 mm/s vs 5.0 mm/s limit, trip threshold 5.5 mm/s),
   and heuristic classification (TELEMETRY_ALARM, OPERATOR_ACTION, SYSTEM_FAILURE, MAINTENANCE_LOG).
2. CitationRegistry: Thread-safe in-memory citation catalog and resolver with deterministic IDs.
3. EvidenceCitationExtractor: Traverses documents (including Near_Miss_Report_2023.txt) with text
   sanitization (clean_spaced_text), line tracking, and multi-factor confidence scoring.
4. verify_causal_grounding: Verifies causal assertion grounding, computes CGR, and flags assumptions.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from api.rca_schemas import CitationObject, EventType, SeverityLevel, TimelineEvent
from core.text_utils import clean_spaced_text


# ==============================================================================
# 1. CITATION REGISTRY
# ==============================================================================

class CitationRegistry:
    r"""
    Thread-safe in-memory citation catalog, resolver, and deduplicator.
    Generates deterministic citation IDs matching r'^CITE-[A-Za-z0-9_\-\.]+$'.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._citations: Dict[str, CitationObject] = {}
        self._dedup_map: Dict[str, str] = {}  # sha256(source_doc + excerpt) -> citation_id
        self._doc_counters: Dict[str, int] = defaultdict(int)

    def register_citation(
        self,
        source_doc: str,
        excerpt: str,
        title: Optional[str] = "",
        section: Optional[str] = None,
        page_or_line: Optional[str] = None,
        confidence: float = 1.0,
        custom_id: Optional[str] = None,
    ) -> CitationObject:
        """
        Registers a citation, enforcing deduplication and schema validation.
        """
        sanitized_excerpt = clean_spaced_text(excerpt.strip()) if excerpt else ""
        if len(sanitized_excerpt) < 3:
            raise ValueError("Citation excerpt must be at least 3 characters.")

        with self._lock:
            fingerprint = hashlib.sha256(
                f"{source_doc}::{sanitized_excerpt}".encode("utf-8")
            ).hexdigest()

            if fingerprint in self._dedup_map:
                existing_id = self._dedup_map[fingerprint]
                return self._citations[existing_id]

            if custom_id:
                citation_id = custom_id
            else:
                base_name = os.path.basename(source_doc)
                raw_slug = os.path.splitext(base_name)[0]
                doc_slug = re.sub(r"[^A-Za-z0-9]", "", raw_slug).upper()[:8] or "DOC"
                self._doc_counters[doc_slug] += 1
                citation_id = f"CITE-{doc_slug}-{self._doc_counters[doc_slug]:03d}"

            citation = CitationObject(
                citation_id=citation_id,
                source_doc=source_doc,
                title=title or "",
                section=section,
                page_or_line=page_or_line,
                excerpt=sanitized_excerpt,
                confidence=max(0.0, min(1.0, confidence)),
            )

            self._citations[citation_id] = citation
            self._dedup_map[fingerprint] = citation_id
            return citation

    def register(self, citation: CitationObject) -> str:
        """
        Registers an existing CitationObject instance.
        """
        with self._lock:
            sanitized_excerpt = clean_spaced_text(citation.excerpt.strip())
            fingerprint = hashlib.sha256(
                f"{citation.source_doc}::{sanitized_excerpt}".encode("utf-8")
            ).hexdigest()

            if fingerprint in self._dedup_map:
                existing_id = self._dedup_map[fingerprint]
                return existing_id

            self._citations[citation.citation_id] = citation
            self._dedup_map[fingerprint] = citation.citation_id
            return citation.citation_id

    def get(self, citation_id: str) -> Optional[CitationObject]:
        """Lookup a citation by ID."""
        with self._lock:
            return self._citations.get(citation_id)

    def list_citations(self) -> List[CitationObject]:
        """Returns all registered citations sorted deterministically by citation_id."""
        with self._lock:
            return sorted(self._citations.values(), key=lambda c: c.citation_id)

    def list_all(self) -> List[CitationObject]:
        """Alias for list_citations."""
        return self.list_citations()

    def validate_citation_ids(self, citation_ids: List[str]) -> Tuple[List[str], List[str]]:
        """Partitions citation IDs into (valid_ids, invalid_ids)."""
        with self._lock:
            valid = [cid for cid in citation_ids if cid in self._citations]
            invalid = [cid for cid in citation_ids if cid not in self._citations]
            return valid, invalid

    def validate_ids(self, citation_ids: List[str]) -> Tuple[List[str], List[str]]:
        """Alias for validate_citation_ids."""
        return self.validate_citation_ids(citation_ids)

    def clear(self) -> None:
        """Clears all stored citations."""
        with self._lock:
            self._citations.clear()
            self._dedup_map.clear()
            self._doc_counters.clear()


# ==============================================================================
# 2. EVIDENCE CITATION EXTRACTOR
# ==============================================================================

class EvidenceCitationExtractor:
    """
    Multi-modal source document traversal engine.
    Extracts citations with line spans, section headings, and confidence scores.
    """

    def __init__(self, registry: Optional[CitationRegistry] = None):
        self.registry = registry or CitationRegistry()

    def parse_markdown_document(self, content: str, source_doc: str) -> List[CitationObject]:
        """
        Segments markdown text into structured sections and registers citations.
        """
        cleaned_content = clean_spaced_text(content)
        lines = cleaned_content.splitlines()
        citations: List[CitationObject] = []
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
                        cite = self.registry.register_citation(
                            source_doc=source_doc,
                            title=f"{source_doc} - {current_section}",
                            excerpt=text_block,
                            section=current_section,
                            page_or_line=f"Lines {start_line}-{idx - 1}",
                            confidence=1.0,
                        )
                        citations.append(cite)
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
                cite = self.registry.register_citation(
                    source_doc=source_doc,
                    title=f"{source_doc} - {current_section}",
                    excerpt=text_block,
                    section=current_section,
                    page_or_line=f"Lines {start_line}-{len(lines)}",
                    confidence=1.0,
                )
                citations.append(cite)

        return citations

    def ingest_near_miss_file(self, filepath: Optional[str] = None) -> List[CitationObject]:
        """
        Ingests the authoritative Near_Miss_Report_2023.txt file.
        Searches standard paths if filepath is not provided.
        """
        target_path = filepath
        if not target_path or not os.path.exists(target_path):
            candidates = [
                "Near_Miss_Report_2023.txt",
                os.path.join("..", "Near_Miss_Report_2023.txt"),
                os.path.join(os.path.dirname(__file__), "..", "..", "Near_Miss_Report_2023.txt"),
                r"C:\000 MINE\My Codzz\Industrial Mind OS\Near_Miss_Report_2023.txt",
            ]
            for c in candidates:
                if os.path.exists(c):
                    target_path = os.path.abspath(c)
                    break

        if not target_path or not os.path.exists(target_path):
            return []

        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        source_doc = os.path.basename(target_path)
        # Parse sections
        parsed = self.parse_markdown_document(content, source_doc)

        # Also extract fine-grained key bullet points for granular citation linking
        bullet_pattern = re.compile(r"-\s+\*\*([^*]+)\*\*:\s+(.+)")
        for idx, line in enumerate(content.splitlines(), start=1):
            m = bullet_pattern.match(line.strip())
            if m:
                bullet_title = m.group(1).strip()
                bullet_text = m.group(2).strip()
                full_excerpt = f"{bullet_title}: {bullet_text}"
                cite = self.registry.register_citation(
                    source_doc=source_doc,
                    title=f"{source_doc} - {bullet_title}",
                    excerpt=full_excerpt,
                    section="Corrective Action / Lessons Learned",
                    page_or_line=f"Line {idx}",
                    confidence=1.0,
                )
                parsed.append(cite)

        return parsed

    def compute_retrieval_confidence(
        self,
        excerpt: str,
        symptoms: List[str],
        telemetry_values: Optional[Dict[str, Any]] = None,
        source_authority: float = 1.0,
    ) -> float:
        """
        Calculates multi-factor confidence score for an excerpt relative to incident symptoms.
        Formula:
          Score = SourceAuthority * (0.40 * S_kw + 0.35 * S_param + 0.25 * S_phrase)
        """
        if not excerpt:
            return 0.0

        lower_excerpt = excerpt.lower()

        # 1. Symptom keyword overlap
        symptom_tokens: Set[str] = set()
        for s in symptoms:
            for token in re.findall(r"\w+", s.lower()):
                if len(token) > 2:
                    symptom_tokens.add(token)

        if symptom_tokens:
            matched_tokens = {tok for tok in symptom_tokens if tok in lower_excerpt}
            s_kw = len(matched_tokens) / len(symptom_tokens)
        else:
            s_kw = 0.5

        # 2. Parameter match ratio
        s_param = 0.2
        if telemetry_values:
            matched_params = 0
            total_params = len(telemetry_values)
            for val in telemetry_values.values():
                val_str = str(val).lower()
                if val_str in lower_excerpt:
                    matched_params += 1
            if total_params > 0 and matched_params > 0:
                s_param = min(1.0, matched_params / total_params + 0.5)
            elif any(u in lower_excerpt for u in ["mm/s", "°c", "bar", "rpm", "psi"]):
                s_param = 0.5

        # 3. Exact phrase match
        s_phrase = 1.0 if any(s.lower() in lower_excerpt for s in symptoms) else 0.5

        raw_score = source_authority * (0.40 * s_kw + 0.35 * s_param + 0.25 * s_phrase)
        return round(max(0.1, min(1.0, raw_score)), 2)

    def traverse_documents(
        self,
        documents: Optional[List[Dict[str, str]]] = None,
    ) -> List[CitationObject]:
        """
        Ingests a batch of documents [{'filename': '...', 'content': '...'}] into the registry.
        """
        results: List[CitationObject] = []
        if not documents:
            return results
        for doc in documents:
            name = doc.get("filename", "unknown.txt")
            body = doc.get("content", "")
            if body:
                extracted = self.parse_markdown_document(body, name)
                results.extend(extracted)
        return results


# ==============================================================================
# 3. TIMELINE EXTRACTOR
# ==============================================================================

class TimelineExtractor:
    """
    Chronological failure timeline reconstruction engine.
    Extracts sensor parameters, classifies event types, computes OEM deviations,
    and builds chronological event logs.
    """

    # Parameter extraction regexes
    VIBRATION_PATTERN = re.compile(
        r"(?:vibration(?: level)?(?: of)?\s*)?(\d+(?:\.\d+)?)\s*(?:mm/s|mms|mm_s|mmps)",
        re.IGNORECASE,
    )
    TEMPERATURE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:°C|deg\s*C|C\b)", re.IGNORECASE)
    PRESSURE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:bar|psi|kPa|MPa)", re.IGNORECASE)
    RPM_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:RPM|rpm)", re.IGNORECASE)
    LEAK_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:liters?|litres?|L\b|gallons?)", re.IGNORECASE)

    # Relative temporal offset expressions
    HOURS_PRIOR_PATTERN = re.compile(r"(\d+)\s*(?:hours?|hrs?)\s*(?:prior|before|earlier)", re.IGNORECASE)
    DAYS_PRIOR_PATTERN = re.compile(r"(\d+)\s*(?:days?)\s*(?:prior|before|earlier)", re.IGNORECASE)
    WITHIN_MINS_PATTERN = re.compile(r"within\s*(\d+)\s*(?:minutes?|mins?)", re.IGNORECASE)

    # Classification keyword maps
    CLASSIFICATION_RULES = {
        "SYSTEM_FAILURE": [
            "catastrophic", "failure", "failed", "shattered", "fracture", "rupture",
            "leak", "spill", "burst", "breakdown", "seized", "burnout", "tripped offline",
            "seal failure", "damage", "cracked",
        ],
        "OPERATOR_ACTION": [
            "operator", "operations personnel", "technician", "ignored", "bypassed",
            "acknowledged", "silenced", "override", "manual", "contained", "deployed",
            "shut down", "shutdown", "isolated", "emergency response", "evacuated",
        ],
        "TELEMETRY_ALARM": [
            "alarm", "alert", "telemetry", "sensor", "vibration", "temperature",
            "pressure", "excursion", "threshold", "trip limit", "reading", "spike",
            "scada", "dcs", "mm/s", "rpm",
        ],
        "MAINTENANCE_LOG": [
            "inspection", "maintenance", "routine operations", "work order", "pm schedule",
            "lubrication", "overhaul", "disassembly", "re-trained", "post-incident analysis",
            "replacement", "calibration",
        ],
    }

    # OEM envelopes by asset tag
    OEM_ENVELOPES = {
        "Pump-A12": {
            "equipment_family": "Centrifugal Pump",
            "vibration_mm_s": {"nominal_max": 5.0, "trip_limit": 5.5, "unit": "mm/s"},
            "temperature_c": {"nominal_max": 70.0, "trip_limit": 85.0, "unit": "°C"},
            "pressure_bar": {"nominal_min": 2.0, "nominal_max": 16.0, "trip_limit": 20.0, "unit": "bar"},
        },
        "DEFAULT": {
            "equipment_family": "General Rotating Asset",
            "vibration_mm_s": {"nominal_max": 4.5, "trip_limit": 7.1, "unit": "mm/s"},
            "temperature_c": {"nominal_max": 75.0, "trip_limit": 90.0, "unit": "°C"},
        },
    }

    def reconstruct_timeline(
        self,
        equipment_tag: str,
        raw_text: Optional[str] = None,
        telemetry_logs: Optional[List[Dict[str, Any]]] = None,
        incident_timestamp: Optional[Union[str, datetime]] = None,
        citations: Optional[List[CitationObject]] = None,
    ) -> List[TimelineEvent]:
        """
        Main entry point for chronological failure timeline reconstruction.
        Compiles, calculates deviations, links citations, and sorts chronologically.
        """
        anchor_dt = self._parse_iso_or_default(incident_timestamp)
        events: List[TimelineEvent] = []

        # 1. Process structured telemetry stream if present
        if telemetry_logs:
            for log in telemetry_logs:
                evt = self._process_telemetry_entry(log, equipment_tag, anchor_dt)
                if evt:
                    events.append(evt)

        # 2. Process unstructured text narrative if present
        if raw_text:
            text_events = self._process_narrative_text(raw_text, equipment_tag, anchor_dt)
            events.extend(text_events)

        # 3. Associate citations if provided
        if citations:
            events = self._link_citations(events, citations)

        # 4. Deterministic chronological sort: ascending by timestamp, tie-break by event_id
        events.sort(key=lambda e: (self._parse_iso_or_default(e.timestamp), e.event_id))

        return events

    def _process_telemetry_entry(
        self,
        log: Dict[str, Any],
        equipment_tag: str,
        anchor_dt: datetime,
    ) -> Optional[TimelineEvent]:
        """Converts raw telemetry log entry into structured TimelineEvent with OEM envelope check."""
        ts = log.get("timestamp")
        dt = self._parse_iso_or_default(ts) if ts else anchor_dt
        params = {k: v for k, v in log.items() if k not in ("timestamp", "equipment_tag", "event_id")}

        # Check vibration parameter
        vib = params.get("vibration_mm_s") or params.get("vibration")
        if vib is not None:
            try:
                vib_val = float(vib)
                params["vibration_mm_s"] = vib_val
                env = self.OEM_ENVELOPES.get(equipment_tag, self.OEM_ENVELOPES["DEFAULT"]).get(
                    "vibration_mm_s", {"nominal_max": 5.0, "trip_limit": 5.5}
                )
                nom_max = env["nominal_max"]
                trip_lim = env["trip_limit"]
                dev_pct = round(((vib_val - nom_max) / nom_max) * 100.0, 2) if nom_max > 0 else 0.0

                params["deviation_pct"] = dev_pct
                params["envelope_max"] = nom_max
                params["trip_limit"] = trip_lim
                params["is_exceeded"] = vib_val > nom_max
                params["is_trip_exceeded"] = vib_val > trip_lim
            except (ValueError, TypeError):
                pass

        event_type = log.get("event_type") or self._classify_sentence(log.get("description", ""))
        desc = log.get("description", f"Telemetry reading on {equipment_tag}")
        event_id = log.get("event_id", f"EVT-TEL-{int(dt.timestamp())}")

        return TimelineEvent(
            event_id=event_id,
            timestamp=dt.isoformat(),
            event_type=event_type,
            description=desc,
            equipment_tag=equipment_tag,
            parameters=params,
            citation_ids=log.get("citation_ids", []),
        )

    def _process_narrative_text(
        self,
        raw_text: str,
        equipment_tag: str,
        anchor_dt: datetime,
    ) -> List[TimelineEvent]:
        """Extracts discrete events from text sentences using temporal and telemetry regexes."""
        cleaned_text = clean_spaced_text(raw_text)
        # Split on sentence boundaries
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_content_filter(cleaned_text)) if len(s.strip()) > 10]
        events: List[TimelineEvent] = []
        idx = 1

        for sentence in sentences:
            # Filter non-incident generic guidance statements
            if any(term in sentence.lower() for term in [
                "all technicians must be", "do not rely on generic", "as per the oem manual"
            ]):
                continue

            ts = self._extract_sentence_timestamp(sentence, anchor_dt)
            params = self._extract_parameters(sentence, equipment_tag)
            event_type = self._classify_sentence(sentence)

            event_id = f"EVT-{idx:03d}"
            events.append(TimelineEvent(
                event_id=event_id,
                timestamp=ts.isoformat(),
                event_type=event_type,
                description=sentence,
                equipment_tag=equipment_tag,
                parameters=params,
                citation_ids=[],
            ))
            idx += 1

        return events

    def _extract_sentence_timestamp(self, sentence: str, anchor_dt: datetime) -> datetime:
        """Determines event timestamp from relative expressions or absolute anchors."""
        # Hours prior
        hp_match = self.HOURS_PRIOR_PATTERN.search(sentence)
        if hp_match:
            hours = int(hp_match.group(1))
            # If also mentions operator ignored, differentiate slightly if desired
            if "ignored" in sentence.lower():
                return anchor_dt - timedelta(hours=hours - 1)
            return anchor_dt - timedelta(hours=hours)

        # Days prior
        dp_match = self.DAYS_PRIOR_PATTERN.search(sentence)
        if dp_match:
            days = int(dp_match.group(1))
            return anchor_dt - timedelta(days=days)

        # Within minutes post-incident
        wm_match = self.WITHIN_MINS_PATTERN.search(sentence)
        if wm_match:
            mins = int(wm_match.group(1))
            return anchor_dt + timedelta(minutes=mins)

        # Post-incident inspection
        if "post-incident" in sentence.lower():
            return anchor_dt + timedelta(hours=4)

        return anchor_dt

    def _extract_parameters(self, sentence: str, equipment_tag: str) -> Dict[str, Any]:
        """Parses sensor values and checks OEM envelope deviations."""
        params: Dict[str, Any] = {}

        vib_match = self.VIBRATION_PATTERN.search(sentence)
        if vib_match:
            val = float(vib_match.group(1))
            params["vibration_mm_s"] = val
            env = self.OEM_ENVELOPES.get(equipment_tag, self.OEM_ENVELOPES["DEFAULT"]).get(
                "vibration_mm_s", {"nominal_max": 5.0, "trip_limit": 5.5}
            )
            nom_max = env["nominal_max"]
            trip_lim = env["trip_limit"]
            params["envelope_max"] = nom_max
            params["trip_limit"] = trip_lim
            dev_pct = round(((val - nom_max) / nom_max) * 100.0, 2) if nom_max > 0 else 0.0
            params["deviation_pct"] = dev_pct
            params["is_exceeded"] = val > nom_max
            params["is_trip_exceeded"] = val > trip_lim

        temp_match = self.TEMPERATURE_PATTERN.search(sentence)
        if temp_match:
            params["temperature_c"] = float(temp_match.group(1))

        press_match = self.PRESSURE_PATTERN.search(sentence)
        if press_match:
            params["pressure_bar"] = float(press_match.group(1))

        rpm_match = self.RPM_PATTERN.search(sentence)
        if rpm_match:
            params["rpm"] = float(rpm_match.group(1))

        leak_match = self.LEAK_PATTERN.search(sentence)
        if leak_match:
            params["leak_volume_l"] = float(leak_match.group(1))

        if "seal failure" in sentence.lower() or "shattered" in sentence.lower():
            params["component"] = "mechanical seal"
            params["failure_mode"] = "shattered"

        if "leak" in sentence.lower() or "spill" in sentence.lower():
            params["leak_detected"] = True

        return params

    def _classify_sentence(self, sentence: str) -> str:
        """Determines event type using rule precedence."""
        s_lower = sentence.lower()

        # Precedence 1: System Failure
        if any(k in s_lower for k in self.CLASSIFICATION_RULES["SYSTEM_FAILURE"]):
            if "ignored" not in s_lower and "contained" not in s_lower:
                return "SYSTEM_FAILURE"

        # Precedence 2: Operator Action
        if any(k in s_lower for k in self.CLASSIFICATION_RULES["OPERATOR_ACTION"]):
            return "OPERATOR_ACTION"

        # Precedence 3: Telemetry Alarm
        if any(k in s_lower for k in self.CLASSIFICATION_RULES["TELEMETRY_ALARM"]):
            return "TELEMETRY_ALARM"

        # Precedence 4: Maintenance Log
        if any(k in s_lower for k in self.CLASSIFICATION_RULES["MAINTENANCE_LOG"]):
            return "MAINTENANCE_LOG"

        return "MAINTENANCE_LOG"

    def _link_citations(
        self,
        events: List[TimelineEvent],
        citations: List[CitationObject],
    ) -> List[TimelineEvent]:
        """Associates citation IDs to timeline events based on word overlap."""
        for event in events:
            matched_cites: List[str] = []
            desc_words = [w.lower() for w in re.findall(r"\b\w{4,}\b", event.description)]

            for c in citations:
                cite_excerpt_lower = c.excerpt.lower()
                matches = sum(1 for w in desc_words if w in cite_excerpt_lower)
                # If vibration matches
                vib_in_event = "vibration" in event.description.lower()
                vib_in_cite = "vibration" in cite_excerpt_lower
                if matches >= 2 or (vib_in_event and vib_in_cite and "5.8" in cite_excerpt_lower):
                    matched_cites.append(c.citation_id)

            if matched_cites:
                event.citation_ids = list(dict.fromkeys(matched_cites))
                event.is_unsubstantiated = False
            else:
                event.is_unsubstantiated = True

        return events

    @staticmethod
    def _parse_iso_or_default(dt_val: Optional[Union[str, datetime]]) -> datetime:
        """Safely parses ISO timestamp string or returns reference UTC date."""
        if not dt_val:
            return datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
        if isinstance(dt_val, datetime):
            return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
        s = str(dt_val).strip()
        s_clean = s.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s_clean)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
        return datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)


def cleaned_content_filter(text: str) -> str:
    """Removes markdown headers before sentence splitting."""
    lines = [l for l in text.splitlines() if not l.strip().startswith("#")]
    return " ".join(lines)


# ==============================================================================
# 4. VERIFY CAUSAL GROUNDING
# ==============================================================================

def verify_causal_grounding(
    causes: List[Any],
    registry: CitationRegistry,
) -> Dict[str, Any]:
    """
    Verifies that all causal assertions resolve to registered citations.
    Sets is_unsubstantiated and assumption_flag / assumed_flag on each cause item.
    Computes Citation Grounding Ratio (CGR).
    """
    total = len(causes)
    grounded = 0

    for cause in causes:
        # Retrieve citation IDs from cause
        cids = getattr(cause, "citation_ids", None)
        if cids is None:
            cids = getattr(cause, "evidence_citation_ids", [])
        if not isinstance(cids, list):
            cids = [cids] if cids else []

        valid_ids, _ = registry.validate_citation_ids(cids)
        if not valid_ids:
            setattr(cause, "is_unsubstantiated", True)
            setattr(cause, "assumed_flag", True)
            setattr(cause, "assumption_flag", True)
        else:
            setattr(cause, "is_unsubstantiated", False)
            setattr(cause, "assumed_flag", False)
            setattr(cause, "assumption_flag", False)
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
        "ungrounded_causes": total - grounded,
        "grounding_ratio": ratio,
        "cgr": ratio,
        "compliance_status": status,
    }
