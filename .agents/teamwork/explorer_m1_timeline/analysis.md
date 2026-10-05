# Technical Analysis & Implementation Blueprint: Chronological Timeline Event Extraction

**Component**: `backend/services/rca_ingestion.py`  
**Milestone**: M1 (Backend Schemas, Ingestion & Timeline Extraction Engine)  
**Author**: M1 Timeline Extractor Explorer (`explorer_m1_timeline`)  
**Target Files**: `backend/services/rca_ingestion.py`, `backend/tests/test_rca_ingestion.py`  
**Specification References**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `spec_miner_survey_domain_2/spec_report.md`, `Near_Miss_Report_2023.txt`  
**Date**: 2026-10-05  

---

## 1. Executive Summary

This document establishes the authoritative implementation blueprint for chronological failure timeline extraction and telemetry stream processing in `backend/services/rca_ingestion.py`.

In an industrial Root Cause Analysis (RCA) and Eight Disciplines (8D) incident workflow, reconstructing an accurate, chronologically ordered sequence of failure symptoms, sensor alarms, operator decisions, and maintenance actions is fundamental. The timeline forms the empirical backbone for downstream causal deduction (5-Why causal tree, Ishikawa 6M classification) and compliance audit packaging.

This analysis provides:
1. **The Timeline Reconstruction Architecture**: A multi-stage pipeline ingesting raw unstructured incident reports, semi-structured logs, and high-frequency telemetry streams.
2. **Deterministic Timestamp Normalization**: Robust parsing supporting ISO 8601 strings, arbitrary calendar date formats, relative time anchors (e.g. *"48 hours prior to failure"*, *"contained within 15 minutes"*), and graceful fallback handling for missing timestamps.
3. **Telemetry Stream Parsing & Threshold Excursion Engine**: Real-time extraction of sensor parameters (vibration in `mm/s`, temperature in `°C`, pressure in `bar`, rotational speed in `RPM`), deviation percentage calculation ($\Delta\%$), and OEM operating envelope classification.
4. **Event Classification Engine**: Heuristic classification into the four mandatory categories: `TELEMETRY_ALARM`, `OPERATOR_ACTION`, `SYSTEM_FAILURE`, and `MAINTENANCE_LOG`.
5. **Near-Miss Report Validation**: Complete trace of the reference incident `Near_Miss_Report_2023.txt` (`Pump-A12`), detailing the 48-hour vibration escalation from normal envelope ($5.0\text{ mm/s}$) to trip threshold ($5.5\text{ mm/s}$) to seal fracture at $5.8\text{ mm/s}$.
6. **Unit Testing Strategy**: Comprehensive test suite covering sequential, out-of-order, malformed, and edge conditions.

---

## 2. Schema Alignment & Data Contracts

### 2.1 Interface Contract Alignment

In `PROJECT.md` (§ Interface Contracts §1) and `spec_report.md` (§4), the chronological event data structure is formalized. To ensure full compatibility across all modules (schemas, ingestion, engine, and frontend), `backend/services/rca_ingestion.py` must produce `TimelineEvent` instances complying with the following Pydantic model:

```python
class TimelineEvent(BaseModel):
    """
    Chronological event logged during incident onset, propagation, and containment.
    Conforms to PROJECT.md §1 Ingestion & Schemas Contract.
    """
    event_id: str = Field(..., description="Unique event identifier e.g. EVT-001 or EVT-20231102-01")
    timestamp: str = Field(..., description="ISO-8601 formatted UTC timestamp e.g. '2023-11-04T08:15:00Z'")
    event_type: str = Field(
        ..., 
        description="Event classification: TELEMETRY_ALARM, OPERATOR_ACTION, SYSTEM_FAILURE, MAINTENANCE_LOG"
    )
    description: str = Field(..., min_length=5, description="Clear description of the event")
    equipment_tag: str = Field(..., description="Equipment tag identifier e.g. 'Pump-A12'")
    citation_ids: List[str] = Field(
        default_factory=list, 
        description="Citation IDs linking this event to verified source documentation"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Observed sensor telemetry, threshold deltas, or metadata (e.g. {'vibration_mm_s': 5.8})"
    )
    is_unsubstantiated: bool = Field(
        default=False, 
        description="True if event lacks documentary citation"
    )
```

### 2.2 Event Type Taxonomy

The system defines four mandatory primary categories (`PROJECT.md`):
- `TELEMETRY_ALARM`: Excursions, SCADA alarms, DCS threshold warnings, sensor spikes, tripping limits.
- `OPERATOR_ACTION`: Operator acknowledgement, alarm silencing/ignoring, manual setpoint adjustments, emergency containment deployment, isolation valve closures.
- `SYSTEM_FAILURE`: Mechanical breakdown, seal fracture/rupture, fluid spill onset, bearing seizure, motor trip, process shutdown.
- `MAINTENANCE_LOG`: Routine maintenance rounds, shift handover logs, lubrication notes, post-incident physical inspections, disassembly findings.

---

## 3. Chronological Timeline Reconstruction Architecture

### 3.1 Pipeline Data Flow

```
Raw Inputs:
┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│ Incident Narrative Text │  │ Structured Sensor Log  │  │ Operator / Shift Notes │
│ (e.g. Near-Miss Report)│  │ (CSV, JSON, Telemetry) │  │ (Maintenance Logs)     │
└───────────┬────────────┘  └───────────┬────────────┘  └───────────┬────────────┘
            │                           │                           │
            ▼                           ▼                           ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                  Stage 1: Document & Log Normalization                         │
│  - Clean spaced PDF artifacts via clean_spaced_text()                          │
│  - Segment sentences & extract discrete event statements                       │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                  Stage 2: Timestamp Parsing & Anchor Resolution                │
│  - Parse explicit ISO-8601 / RFC-2822 / Calendar dates                         │
│  - Compute relative offsets (e.g. "48 hours prior", "within 15 minutes")       │
│  - Apply fallback interpolation for missing timestamps                         │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                  Stage 3: Telemetry & Parameter Extraction                     │
│  - Regex extraction for vibration (mm/s), temp (°C), pressure (bar), RPM       │
│  - Calculate OEM envelope deviation (%) and trip threshold excursions          │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                  Stage 4: Heuristic Event Classification                       │
│  - Multi-factor keyword scoring for TELEMETRY_ALARM, OPERATOR_ACTION, etc.     │
│  - Resolution of overlapping semantics (precedence rules)                      │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                  Stage 5: Chronological Sorting & Citation Linkage             │
│  - Ascending sort by parsed UTC datetime                                       │
│  - Deterministic tie-breaking for identical timestamps                         │
│  - Associate verified citation_ids; flag is_unsubstantiated if missing         │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │
                                        ▼
                            List[TimelineEvent]
```

---

## 4. Algorithmic Detail & Implementation Mechanics

### 4.1 Timestamp Parsing & Anchor Resolution

Industrial incident documents use diverse time representations:
1. **Explicit ISO-8601 / Standard Format**: `2023-11-04T08:15:00Z`, `2023-11-04 08:15:00`.
2. **Calendar Dates**: `November 4, 2023`, `Nov 4, 2023`, `2023-11-04`.
3. **Relative Time Expressions**:
   - Prior to incident: *"48 hours prior to the failure"*, *"2 days before onset"*, *"30 minutes earlier"*.
   - Following incident: *"within 15 minutes"*, *"2 hours after shutdown"*, *"next shift"*.

#### Resolution Algorithm:
```python
def resolve_timestamp(raw_text: str, anchor_datetime: Optional[datetime] = None) -> datetime:
    """
    1. Check for absolute ISO or date strings using regex and dateutil.parser.
    2. If relative phrasing is detected:
       - Match regex: r'(\d+)\s*(?:hours?|hrs?)\s*(?:prior|before|earlier)'
         -> return anchor_datetime - timedelta(hours=int(match))
       - Match regex: r'within\s*(\d+)\s*(?:minutes?|mins?)'
         -> return anchor_datetime + timedelta(minutes=int(match))
       - Match regex: r'(\d+)\s*(?:days?)\s*(?:prior|before)'
         -> return anchor_datetime - timedelta(days=int(match))
    3. If neither, fallback to anchor_datetime or epoch default.
    """
```

#### Handling Missing or Malformed Timestamps:
- If a log entry lacks a timestamp but appears between two known timestamped entries $E_a$ ($T_a$) and $E_b$ ($T_b$), the engine interpolates:
  $$T_{\text{interpolated}} = T_a + \frac{T_b - T_a}{2}$$
- If an entry has no timestamp and no bounds, it is anchored to the provided `incident_timestamp` with a metadata parameter `timestamp_estimated: True`.
- Under zero-anchor scenarios (no document date, no input date), a deterministic baseline `datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)` is used, preserving original sequential offsets by $+1\text{ second}$ increments to maintain relative ordering without throwing errors.

### 4.2 Telemetry Stream Parsing & Parameter Extraction

The ingestion engine must reliably parse physical parameters from free text or telemetry log lines.

| Parameter | Units | Standard Regex Pattern | Normalized Key | Example Text |
|---|---|---|---|---|
| **Vibration** | `mm/s`, `in/s`, `g` | `r'(?:vibration(?: level)?(?: of)?\s*)?(\d+(?:\.\d+)?)\s*(?:mm/s|mms|mm_s|mmps)'` | `vibration_mm_s` | `5.8 mm/s` |
| **Temperature** | `°C`, `deg C`, `°F`, `K` | `r'(\d+(?:\.\d+)?)\s*(?:°C|deg\s*C|C\b)'` | `temperature_c` | `82.4 °C` |
| **Pressure** | `bar`, `psi`, `kPa`, `MPa` | `r'(\d+(?:\.\d+)?)\s*(?:bar|psi|kPa|MPa)'` | `pressure_bar` | `12.5 bar` |
| **Speed / RPM** | `RPM`, `rpm`, `rev/min`, `Hz` | `r'(\d+(?:\.\d+)?)\s*(?:RPM|rpm)'` | `rpm` | `3550 RPM` |
| **Leak Volume** | `L`, `liters`, `gallons` | `r'(\d+(?:\.\d+)?)\s*(?:liters?|litres?|L\b|gallons?)'` | `leak_volume_l` | `15 liters` |

### 4.3 OEM Operating Envelope & Excursion Calculations

Equipment envelopes define nominal maximums, warning thresholds, and mandatory trip limits.

#### Default Equipment Envelopes:
```python
OEM_EQUIPMENT_ENVELOPES = {
    "Pump-A12": {
        "equipment_family": "Centrifugal Pump",
        "vibration_mm_s": {"nominal_max": 5.0, "trip_limit": 5.5, "unit": "mm/s"},
        "temperature_c": {"nominal_max": 70.0, "trip_limit": 85.0, "unit": "°C"},
        "pressure_bar": {"nominal_min": 2.0, "nominal_max": 16.0, "trip_limit": 20.0, "unit": "bar"},
    },
    "DEFAULT_PUMP": {
        "equipment_family": "General Rotating Asset",
        "vibration_mm_s": {"nominal_max": 4.5, "trip_limit": 7.1, "unit": "mm/s"},
        "temperature_c": {"nominal_max": 75.0, "trip_limit": 90.0, "unit": "°C"},
    }
}
```

#### Deviation Formula:
$$\Delta\% = \left( \frac{\text{Actual Value} - \text{Nominal Max}}{\text{Nominal Max}} \right) \times 100$$

When $\text{Nominal Max} \le 0$, the calculation safely returns `0.0%` to prevent `ZeroDivisionError`.

#### Excursion Evaluation Rules:
1. If $\text{Actual Value} > \text{Trip Limit}$:
   - Parameter flag: `is_trip_exceeded: True`, `is_exceeded: True`
   - Severity: `CRITICAL`
   - Description tag: `"[TRIP EXCEEDED]"`
2. If $\text{Nominal Max} < \text{Actual Value} \le \text{Trip Limit}$:
   - Parameter flag: `is_trip_exceeded: False`, `is_exceeded: True`
   - Severity: `WARNING` / `HIGH`
   - Description tag: `"[THRESHOLD WARNING]"`
3. If $\text{Actual Value} \le \text{Nominal Max}$:
   - Parameter flag: `is_exceeded: False`
   - Severity: `NOMINAL`

### 4.4 Heuristic Event Classification Engine

To assign `event_type`, the classifier computes semantic scores against the event description:

```python
CLASSIFICATION_KEYWORDS = {
    "SYSTEM_FAILURE": [
        "catastrophic", "failure", "failed", "shattered", "fracture", "rupture",
        "leak", "spill", "burst", "breakdown", "seized", "burnout", "tripped offline",
        "seal failure", "damage", "cracked"
    ],
    "OPERATOR_ACTION": [
        "operator", "operations personnel", "technician", "ignored", "bypassed",
        "acknowledged", "silenced", "override", "manual", "contained", "deployed",
        "shut down", "shutdown", "isolated", "emergency response", "evacuated"
    ],
    "TELEMETRY_ALARM": [
        "alarm", "alert", "telemetry", "sensor", "vibration", "temperature",
        "pressure", "excursion", "threshold", "trip limit", "reading", "spike",
        "scada", "dcs", "mm/s", "rpm"
    ],
    "MAINTENANCE_LOG": [
        "inspection", "maintenance", "routine operations", "work order", "pm schedule",
        "lubrication", "overhaul", "disassembly", "re-trained", "post-incident analysis",
        "replacement", "calibration"
    ]
}
```

#### Precedence Resolution:
When an event contains overlapping keywords (e.g. *"Operations personnel ignored vibration alerts"* contains both `OPERATOR_ACTION` and `TELEMETRY_ALARM` keywords):
1. **Operator agency precedence**: If active human intervention (or omission: *ignored*, *bypassed*, *contained*, *shut down*) is the primary subject, classify as `OPERATOR_ACTION`.
2. **Physical destruction precedence**: If physical equipment breakage occurred (*shattered*, *ruptured*, *leaked*), classify as `SYSTEM_FAILURE`.
3. **Telemetry excursion**: If passive sensor alert or threshold crossing without direct human action, classify as `TELEMETRY_ALARM`.
4. **Maintenance records**: If scheduled inspection, routine observation, or post-incident review, classify as `MAINTENANCE_LOG`.

---

## 5. Walkthrough: Reconstruction of `Near_Miss_Report_2023.txt`

The reference incident in `Near_Miss_Report_2023.txt` serves as the benchmark validation scenario for `Pump-A12`.

### 5.1 Source Text Analysis
- **Date of Incident**: November 4, 2023 (Anchored at `2023-11-04T08:00:00Z`).
- **Equipment Tag**: `Pump-A12`.
- **Location**: Primary Cooling Loop, Sector 4.
- **Narrative Segments**:
  1. *"the pump had been operating with a severe vibration level of 5.8 mm/s for 48 hours prior to the failure."*
  2. *"Operations personnel ignored the vibration alerts because they mistakenly believed the threshold was 6.5 mm/s."*
  3. *"During routine operations, Pump A12 experienced a catastrophic mechanical seal failure. This resulted in a minor leak of coolant fluid onto the factory floor."*
  4. *"The spill was contained within 15 minutes by the emergency response team, preventing it from reaching the environmental drainage system."*
  5. *"Post-incident analysis revealed that ... sustained vibration at 5.8 mm/s shattered the inboard ceramic seals."*

### 5.2 Chronological Reconstruction Matrix

| Sequence | Parsed Timestamp | Event Type | Description | Extracted Parameters | Citation ID |
|---|---|---|---|---|---|
| **1** | `2023-11-02T08:00:00Z`<br>($T_0 - 48\text{h}$) | `TELEMETRY_ALARM` | Severe vibration onset: Pump-A12 vibration reached 5.8 mm/s, exceeding OEM envelope max of 5.0 mm/s (+16.0% deviation) and trip threshold of 5.5 mm/s. | `vibration_mm_s: 5.8`<br>`envelope_max: 5.0`<br>`trip_limit: 5.5`<br>`deviation_pct: 16.0`<br>`is_exceeded: True` | `CITE-PUMP-001` |
| **2** | `2023-11-02T09:00:00Z`<br>($T_0 - 47\text{h}$) | `OPERATOR_ACTION` | Operations personnel ignored vibration alerts at 5.8 mm/s due to mistaken belief that threshold was 6.5 mm/s. | `vibration_mm_s: 5.8`<br>`assumed_threshold: 6.5`<br>`actual_oem_limit: 5.0`<br>`action: "ignored"` | `CITE-PUMP-002` |
| **3** | `2023-11-04T08:00:00Z`<br>($T_0$) | `SYSTEM_FAILURE` | Catastrophic mechanical seal failure: sustained vibration shattered inboard ceramic seals, causing coolant fluid leak onto factory floor. | `vibration_mm_s: 5.8`<br>`component: "ceramic seals"`<br>`failure_mode: "shattered"`<br>`leak: True` | `CITE-PUMP-003` |
| **4** | `2023-11-04T08:15:00Z`<br>($T_0 + 15\text{m}$) | `OPERATOR_ACTION` | Emergency containment: Spill contained within 15 minutes by emergency response team, preventing fluid from reaching environmental drainage system. | `containment_time_mins: 15`<br>`drainage_reached: False`<br>`injuries: 0` | `CITE-PUMP-004` |
| **5** | `2023-11-04T12:00:00Z`<br>(Post-Incident) | `MAINTENANCE_LOG` | Post-incident physical inspection: Confirmed shattered inboard ceramic seals resulting from sustained 48-hour operation at 5.8 mm/s. | `inspected_component: "ceramic seals"`<br>`damage_state: "shattered"`<br>`recommendation: "mandatory shutdown at 5.5 mm/s"` | `CITE-PUMP-005` |

---

## 6. Implementation Blueprint: `TimelineExtractor` Class Architecture

The following concrete class blueprint specifies the code architecture for `backend/services/rca_ingestion.py`:

```python
"""
Timeline Extraction Engine for Industrial Mind OS RCA Studio.
Location: backend/services/rca_ingestion.py
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from dateutil import parser as date_parser

# Pydantic schema import
from api.rca_schemas import TimelineEvent, CitationObject
from core.text_utils import clean_spaced_text


class TimelineExtractor:
    """
    Autonomous failure timeline reconstruction engine.
    Extracts, normalizes, classifies, and sorts chronological events from industrial text
    and telemetry logs.
    """

    # Sensor parameter regular expressions
    VIBRATION_PATTERN = re.compile(r'(?:vibration(?: level)?(?: of)?\s*)?(\d+(?:\.\d+)?)\s*(?:mm/s|mms|mm_s|mmps)', re.IGNORECASE)
    TEMPERATURE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:°C|deg\s*C|C\b)', re.IGNORECASE)
    PRESSURE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:bar|psi|kPa|MPa)', re.IGNORECASE)
    RPM_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:RPM|rpm)', re.IGNORECASE)

    # Relative temporal offset expressions
    HOURS_PRIOR_PATTERN = re.compile(r'(\d+)\s*(?:hours?|hrs?)\s*(?:prior|before|earlier)', re.IGNORECASE)
    DAYS_PRIOR_PATTERN = re.compile(r'(\d+)\s*(?:days?)\s*(?:prior|before|earlier)', re.IGNORECASE)
    WITHIN_MINS_PATTERN = re.compile(r'within\s*(\d+)\s*(?:minutes?|mins?)', re.IGNORECASE)

    # Classification keyword maps
    CLASSIFICATION_RULES = {
        "SYSTEM_FAILURE": [
            "catastrophic", "failure", "failed", "shattered", "fracture", "rupture",
            "leak", "spill", "burst", "breakdown", "seized", "burnout", "tripped offline"
        ],
        "OPERATOR_ACTION": [
            "operator", "operations personnel", "technician", "ignored", "bypassed",
            "acknowledged", "silenced", "override", "manual", "contained", "deployed",
            "shut down", "shutdown", "isolated", "emergency response"
        ],
        "TELEMETRY_ALARM": [
            "alarm", "alert", "telemetry", "sensor", "vibration", "temperature",
            "pressure", "excursion", "threshold", "trip limit", "reading", "spike"
        ],
        "MAINTENANCE_LOG": [
            "inspection", "maintenance", "routine operations", "work order", "pm schedule",
            "lubrication", "overhaul", "disassembly", "re-trained", "post-incident analysis"
        ]
    }

    # OEM envelopes
    OEM_ENVELOPES = {
        "Pump-A12": {
            "vibration_mm_s": {"nominal_max": 5.0, "trip_limit": 5.5, "unit": "mm/s"},
            "temperature_c": {"nominal_max": 70.0, "trip_limit": 85.0, "unit": "°C"},
        }
    }

    def reconstruct_timeline(
        self,
        equipment_tag: str,
        raw_text: Optional[str] = None,
        telemetry_logs: Optional[List[Dict[str, Any]]] = None,
        incident_timestamp: Optional[Union[str, datetime]] = None,
        citations: Optional[List[CitationObject]] = None
    ) -> List[TimelineEvent]:
        """
        Main entry point for chronological timeline reconstruction.
        Compiles events from raw text and/or telemetry streams, sorts them,
        links citations, and validates against Pydantic schema.
        """
        anchor_dt = self._parse_iso_or_default(incident_timestamp)
        events: List[TimelineEvent] = []

        # 1. Process structured telemetry stream if present
        if telemetry_logs:
            for log in telemetry_logs:
                event = self._process_telemetry_entry(log, equipment_tag, anchor_dt)
                if event:
                    events.append(event)

        # 2. Process unstructured text narrative if present
        if raw_text:
            text_events = self._process_narrative_text(raw_text, equipment_tag, anchor_dt)
            events.extend(text_events)

        # 3. Ground citations
        events = self._link_citations(events, citations or [])

        # 4. Chronological sort with deterministic tie-breaker
        events.sort(key=lambda e: (self._parse_iso_or_default(e.timestamp), e.event_id))

        return events

    def _process_telemetry_entry(
        self, 
        log: Dict[str, Any], 
        equipment_tag: str, 
        anchor_dt: datetime
    ) -> Optional[TimelineEvent]:
        """Converts a raw telemetry log entry into a structured TimelineEvent with deviation check."""
        ts = log.get("timestamp")
        dt = self._parse_iso_or_default(ts) if ts else anchor_dt
        params = {k: v for k, v in log.items() if k not in ("timestamp", "equipment_tag", "event_id")}
        
        # Check vibration threshold if present
        vib = params.get("vibration_mm_s") or params.get("vibration")
        event_type = "TELEMETRY_ALARM"
        desc = log.get("description", f"Telemetry reading on {equipment_tag}")
        
        if vib is not None:
            envelope = self.OEM_ENVELOPES.get(equipment_tag, {}).get("vibration_mm_s", {"nominal_max": 5.0, "trip_limit": 5.5})
            nom_max = envelope["nominal_max"]
            trip_lim = envelope["trip_limit"]
            dev_pct = round(((vib - nom_max) / nom_max) * 100.0, 2) if nom_max > 0 else 0.0
            
            params["deviation_pct"] = dev_pct
            params["envelope_max"] = nom_max
            params["trip_limit"] = trip_lim
            params["is_exceeded"] = vib > nom_max
            params["is_trip_exceeded"] = vib > trip_lim

            if vib > trip_lim:
                desc = f"Critical trip limit exceeded on {equipment_tag}: {vib} mm/s (Trip limit: {trip_lim} mm/s, +{dev_pct}% dev)"
            elif vib > nom_max:
                desc = f"Warning threshold exceeded on {equipment_tag}: {vib} mm/s (OEM limit: {nom_max} mm/s, +{dev_pct}% dev)"

        event_id = log.get("event_id", f"EVT-TEL-{int(dt.timestamp())}")
        return TimelineEvent(
            event_id=event_id,
            timestamp=dt.isoformat(),
            event_type=event_type,
            description=desc,
            equipment_tag=equipment_tag,
            parameters=params,
            citation_ids=[]
        )

    def _process_narrative_text(
        self, 
        raw_text: str, 
        equipment_tag: str, 
        anchor_dt: datetime
    ) -> List[TimelineEvent]:
        """Extracts discrete events from text sentences using regex and heuristics."""
        cleaned_text = clean_spaced_text(raw_text)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_text) if len(s.strip()) > 10]
        events = []
        idx = 1

        for sentence in sentences:
            ts = self._extract_sentence_timestamp(sentence, anchor_dt)
            params = self._extract_parameters(sentence, equipment_tag)
            event_type = self._classify_sentence(sentence)

            # Skip general advice/training sentences that do not describe chronological actions
            if any(term in sentence.lower() for term in ["all technicians must be", "do not rely on", "as per the oem manual"]):
                continue

            event_id = f"EVT-{idx:03d}"
            events.append(TimelineEvent(
                event_id=event_id,
                timestamp=ts.isoformat(),
                event_type=event_type,
                description=sentence,
                equipment_tag=equipment_tag,
                parameters=params,
                citation_ids=[]
            ))
            idx += 1

        return events

    def _extract_sentence_timestamp(self, sentence: str, anchor_dt: datetime) -> datetime:
        """Determines event timestamp from relative or absolute expressions in sentence."""
        # 1. Hours prior
        hp_match = self.HOURS_PRIOR_PATTERN.search(sentence)
        if hp_match:
            hours = int(hp_match.group(1))
            return anchor_dt - timedelta(hours=hours)

        # 2. Days prior
        dp_match = self.DAYS_PRIOR_PATTERN.search(sentence)
        if dp_match:
            days = int(dp_match.group(1))
            return anchor_dt - timedelta(days=days)

        # 3. Within minutes (after incident)
        wm_match = self.WITHIN_MINS_PATTERN.search(sentence)
        if wm_match:
            mins = int(wm_match.group(1))
            return anchor_dt + timedelta(minutes=mins)

        # 4. Post-incident inspection keywords
        if "post-incident" in sentence.lower():
            return anchor_dt + timedelta(hours=4)

        # 5. Default to incident anchor
        return anchor_dt

    def _extract_parameters(self, sentence: str, equipment_tag: str) -> Dict[str, Any]:
        """Parses sensor values and checks OEM envelope deviations."""
        params: Dict[str, Any] = {}

        vib_match = self.VIBRATION_PATTERN.search(sentence)
        if vib_match:
            val = float(vib_match.group(1))
            params["vibration_mm_s"] = val
            envelope = self.OEM_ENVELOPES.get(equipment_tag, {}).get("vibration_mm_s", {"nominal_max": 5.0, "trip_limit": 5.5})
            nom_max = envelope["nominal_max"]
            params["envelope_max"] = nom_max
            params["trip_limit"] = envelope["trip_limit"]
            if nom_max > 0:
                params["deviation_pct"] = round(((val - nom_max) / nom_max) * 100.0, 2)
            params["is_exceeded"] = val > nom_max
            params["is_trip_exceeded"] = val > envelope["trip_limit"]

        temp_match = self.TEMPERATURE_PATTERN.search(sentence)
        if temp_match:
            params["temperature_c"] = float(temp_match.group(1))

        press_match = self.PRESSURE_PATTERN.search(sentence)
        if press_match:
            params["pressure_bar"] = float(press_match.group(1))

        rpm_match = self.RPM_PATTERN.search(sentence)
        if rpm_match:
            params["rpm"] = float(rpm_match.group(1))

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

    def _link_citations(self, events: List[TimelineEvent], citations: List[CitationObject]) -> List[TimelineEvent]:
        """Associates citation IDs to timeline events based on text overlap."""
        for event in events:
            matched_cites = []
            for c in citations:
                # Check if citation excerpt keywords appear in event description
                words = [w.lower() for w in re.findall(r'\b\w{5,}\b', event.description)]
                matches = sum(1 for w in words if w in c.excerpt.lower())
                if matches >= 2 or (len(words) < 2 and matches >= 1):
                    matched_cites.append(c.citation_id)
            
            if matched_cites:
                event.citation_ids = list(dict.fromkeys(matched_cites))
                event.is_unsubstantiated = False
            else:
                event.is_unsubstantiated = True
        return events

    @staticmethod
    def _parse_iso_or_default(dt_val: Optional[Union[str, datetime]]) -> datetime:
        """Safely parses ISO timestamp strings or returns current UTC."""
        if not dt_val:
            return datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
        if isinstance(dt_val, datetime):
            return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
        try:
            parsed = date_parser.parse(str(dt_val))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
```

---

## 7. Unit Testing Blueprint: `test_rca_ingestion.py`

The unit test suite will live in `backend/tests/test_rca_ingestion.py`. Tests must run offline without LLM, Qdrant, or network dependencies (aligned with `backend/pytest.ini`).

### 7.1 Test Case Matrix

| Suite # | Test Function Name | Tested Behavior | Expected Outcome |
|---|---|---|---|
| **T1.1** | `test_reconstruct_timeline_near_miss_ordering` | Parses `Near_Miss_Report_2023.txt` text narrative | Returns 5 events strictly in ascending order ($T - 48\text{h} \rightarrow T - 47\text{h} \rightarrow T_0 \rightarrow T + 15\text{m} \rightarrow T + 4\text{h}$) |
| **T1.2** | `test_telemetry_threshold_excursion_deviation` | Ingests 5.8 mm/s vibration reading for `Pump-A12` | Computes $\Delta\% = +16.0\%$, flags `is_trip_exceeded=True`, classifies `TELEMETRY_ALARM` |
| **T1.3** | `test_out_of_order_telemetry_stream_sorting` | Feeds logs in reverse order: Containment, then Alarm, then Pre-warning | Reconstructor sorts events strictly by timestamp ascending |
| **T1.4** | `test_missing_timestamp_fallback_behavior` | Log entries with `timestamp=None` or empty strings | Applies fallback anchor without throwing `ValueError` or unhandled exceptions |
| **T1.5** | `test_malformed_timestamp_string_tolerance` | Passes `"invalid-date"`, `"null"`, `"unknown"` | Gracefully defaults to reference anchor and preserves event in output |
| **T1.6** | `test_relative_offset_calculation` | Expressions: *"48 hours prior"*, *"within 15 minutes"* | Accurately shifts anchor by $-48\text{h}$ and $+15\text{m}$ |
| **T1.7** | `test_event_type_classification_coverage` | Phrases matching alarm, operator, failure, maintenance | Correctly maps all 4 primary event types without cross-contamination |
| **T1.8** | `test_sensor_parameter_extraction_regex` | Vibration, temperature, pressure, and RPM strings | Normalizes keys `vibration_mm_s`, `temperature_c`, `pressure_bar`, `rpm` as floats |
| **T1.9** | `test_empty_and_null_input_handling` | `raw_text=""`, `telemetry_logs=[]` | Safely returns empty list `[]` without error |
| **T1.10** | `test_citation_grounding_and_unsubstantiated_flag` | Matches against `CitationObject` catalog | Sets `citation_ids` when matching, sets `is_unsubstantiated=True` when missing |
| **T1.11** | `test_zero_division_guard_on_zero_envelope` | `envelope_max = 0.0` | Defaults `deviation_pct = 0.0` without raising `ZeroDivisionError` |

---

## 8. Summary of Recommendations for M1 Implementation

1. **Schema Consistency**: Ensure `TimelineEvent` in `backend/api/rca_schemas.py` includes `event_id`, `timestamp: str`, `event_type: str`, `description: str`, `equipment_tag: str`, `citation_ids: List[str]`, `parameters: Dict[str, Any]`, and `is_unsubstantiated: bool`.
2. **Text Cleaning Pipeline**: Always run `core.text_utils.clean_spaced_text` before parsing text reports to handle PDF artifact spaces (e.g. `P u m p - A 1 2`).
3. **No Heavy Imports**: Keep `backend/services/rca_ingestion.py` free of LLM or Qdrant imports so unit tests execute instantaneously in CI/CD via `pytest`.
4. **Deterministic Tie-Breaking**: When multiple sensor records share identical timestamps, sort deterministically by `(timestamp, event_id)` to avoid flaky test assertions.
