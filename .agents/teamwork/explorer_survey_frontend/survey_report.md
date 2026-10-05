# Frontend Codebase Survey Report: Automated RCA & 8D Incident Report Studio

**Document Date**: 2026-10-05  
**Investigator**: Frontend Codebase Explorer (`explorer_survey_frontend`)  
**Workspace**: `C:\000 MINE\My Codzz\Industrial Mind OS\frontend`  
**Integrity Mode**: Development / Read-Only Investigation  

---

## 1. Executive Summary

Industrial Mind OS features a modern, lightweight single-page application built with **React 18.2.0**, **Vite 8.2.2**, and **Tailwind CSS 3.4.3**. The application is configured with an active artifact system that renders auxiliary panels adjacent to the primary chat interface (`App.jsx`, `ArtifactPanel.jsx`, `InsightPanel.jsx`).

The codebase is exceptionally well-suited for the addition of the **8D Incident Studio**:
1. **Clean Build Pipeline**: `npm run build` runs cleanly in **1.57 seconds** with zero errors (`exit code 0`).
2. **Modular Artifact Architecture**: The frontend already detects `[ARTIFACT: ...]` blocks via regex (`MarkdownRenderer.jsx`) and delegates rendering to `ArtifactPanel.jsx`, widening the right panel from 360px to 50% width (`lg:w-1/2`).
3. **Pre-installed Visualization Tools**: `mermaid` (11.13.0), `react-force-graph-2d` (1.29.1), `d3-force` (3.0.0), `framer-motion` (11.5.0), and `lucide-react` (0.360.0) are already present in `package.json` dependencies.
4. **Seamless Evidence Verification**: The application already features `SourceViewerModal.jsx` for verifiable citation drill-downs, which can be connected directly to the 8D report citation tags.
5. **Print & Audit Foundation**: An iframe-based print mechanism is already modeled in `ChatInterface.jsx` and can be expanded into an enterprise-grade, ISO 9001/IATF 16949 print-ready audit export.

---

## 2. Investigation Findings: The 5 Core Survey Areas

### 2.1. Frontend Build System & Pipeline Configuration

#### Build Tooling & Configuration
- **Core Stack**:
  - `react`: `^18.2.0`
  - `react-dom`: `^18.2.0`
  - `vite`: `^8.2.2`
  - `@vitejs/plugin-react`: `^6.1.0`
  - `tailwindcss`: `^3.4.3`
  - `postcss`: `^8.4.38`
  - `autoprefixer`: `^10.4.19`
- **Configuration Files**:
  - `frontend/vite.config.js`: Minimalist Vite configuration using standard `@vitejs/plugin-react`.
  - `frontend/tailwind.config.js`: Content paths covering `./index.html` and `./src/**/*.{js,ts,jsx,tsx}`.
  - `frontend/postcss.config.js`: Configures Tailwind CSS and Autoprefixer.
  - `frontend/src/api.js`: Exports `API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'`.
- **Scripts in `package.json`**:
  - `dev`: `vite`
  - `build`: `vite build`
  - `preview`: `vite preview`

#### Build Benchmark Verification
Executing `npm run build` from `C:\000 MINE\My Codzz\Industrial Mind OS\frontend`:
```
> industrial-mind-os@0.0.0 build
> vite build

vite v8.2.2 building client environment for production...
transforming...
✓ 2766 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.45 kB │ gzip:   0.32 kB
dist/assets/index-DsqLlfEf.css   41.83 kB │ gzip:   7.61 kB
dist/assets/index-B22YsQSE.js   593.56 kB │ gzip: 181.53 kB
✓ built in 1.57s
```
- **Exit Code**: `0`
- **Output Artifacts**: Clean production bundle in `dist/`.
- **Build Warning Note**: Vite emits an advisory warning that the main bundle chunk is `593.56 kB` (> 500 kB limit) due to graph and diagram packages (`mermaid`, `react-force-graph-2d`). This does not cause errors or fail the build.

---

### 2.2. Existing UI Component Hierarchy & Artifact Rendering System

#### Component Directory Map (`frontend/src/`)
```
frontend/src/
├── App.jsx                     # Root application state & 3-pane layout coordinator
├── api.js                      # API base origin configuration
├── index.css                   # Tailwind base, components, utilities
├── main.jsx                    # React 18 createRoot bootstrap
└── components/
    ├── ArtifactPanel.jsx       # Side-panel artifact renderer (HTML preview, Code, Table)
    ├── ChatInterface.jsx       # Conversational feed, thought process steps, citations, input
    ├── InsightPanel.jsx        # Retrieval confidence, search strategy, and citations
    ├── MarkdownRenderer.jsx    # ReactMarkdown parser + [ARTIFACT] extractor
    ├── GraphVisualizer.jsx     # Full-screen modal for NetworkX Knowledge Graph (ForceGraph2D)
    ├── MindMap.jsx             # Full-screen modal for Asset Topology tree projection
    ├── Sidebar.jsx             # Left sidebar: chat history, file uploads, Confluence, alerts
    ├── SourceSelectionModal.jsx# Modal for gating chat retrieval to specific files
    ├── SourceViewerModal.jsx   # Modal for inspecting exact evidence snippets & citations
    └── Auth/
        ├── AuthShell.jsx       # Split-pane authentication frame
        ├── Login.jsx           # Email / password login
        └── Register.jsx        # New user registration
```

#### Artifact Lifecycle & Rendering Flow
1. **Emission from Backend**:
   - The LangGraph orchestrator (`backend/agents/orchestrator.py:313`) instructs the synthesizer:
     `Format: [ARTIFACT: Dashboard Name] <content> [/ARTIFACT]`
2. **Extraction in Frontend**:
   - `MarkdownRenderer.jsx:extractArtifacts()` executes regex `\[ARTIFACT:\s*([^\]]+)\]([\s\S]*?)\[\/ARTIFACT\]/gi`.
   - The regex removes the artifact block from `cleanContent` (so the chat bubble remains tidy) and returns an array of `{ title, content, fullMatch }`.
   - Inline trigger: `ArtifactInlineButton` displays an attractive button in the message bubble with a type-specific icon (`Globe`, `Table2`, or `Code2`), the title, and an `ExternalLink` indicator.
   - Clicking the button fires `onArtifactOpen(artifact)`.
3. **Layout Expansion in `App.jsx`**:
   - State: `const [activeArtifact, setActiveArtifact] = useState(null)`.
   - When `activeArtifact` is active:
     - Right pane shifts from width `lg:w-[360px]` to `lg:w-1/2` (50% screen width) or `w-full` on mobile.
     - Replaces `<InsightPanel>` with `<ArtifactPanel artifact={activeArtifact} onClose={() => setActiveArtifact(null)} />`.
4. **Current `ArtifactPanel.jsx` Capabilities**:
   - Functions `detectArtifactType(content)` classify into:
     - `html` (renders sandboxed iframe with Tailwind CDN)
     - `table` (renders markdown table into styled DOM table)
     - `code` (renders syntax-highlighted code block with copy action)
   - Tab bar switches between `🌐 Preview`, `</> Code`, and `📋 Table`.

---

### 2.3. Integration of 8D Incident Studio as an Interactive Artifact Panel

#### The Structural Gap
Currently, when an artifact contains complex structured incident data, `ArtifactPanel.jsx` only handles raw HTML strings or raw code/tables.
To fulfill **R3** ("Interactive 8D Report Artifact Studio rendering the full Eight Disciplines structure with dynamic interactive charts, citation drill-downs, and print-ready compliance styling"), the panel needs dedicated support for 8D Incident Reports.

#### Architectural Design: `EightDIncidentStudio` Component
An 8D Studio component can be placed at `frontend/src/components/EightDStudio/EightDIncidentStudio.jsx` (or `frontend/src/components/EightDStudio.jsx`), seamlessly integrated into `ArtifactPanel.jsx`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        8D Incident Studio Header                       │
│  [D1-D8 Shield Icon] Incident: PUMP-A12 Seal Fracture  [CRITICAL]      │
│  Asset Tag: PUMP-A12 | Sector: Primary Cooling Loop Sector 4           │
│  [Export Audit Package] [Close X]                                      │
├────────────────────────────────────────────────────────────────────────┤
│  Tab Navigation:                                                       │
│  [ 📋 Overview ]  [ 🌳 5-Why Tree ]  [ ⏱️ Timeline ]  [ 🛡️ Corrective Actions ] │
├────────────────────────────────────────────────────────────────────────┤
│  TAB CONTENT:                                                          │
│  1. Overview:                                                          │
│     - 8D Discipline Matrix (D1 through D8 summary cards)               │
│     - 5W2H Problem Definition Grid                                     │
│     - Executive Containment & RCA Summary with Citation Pills          │
│                                                                        │
│  2. 5-Why Tree & Fishbone:                                             │
│     - Causal Flowchart: Symptom → Why 1 → Why 2 → Why 3 → Root Cause   │
│     - Grounding status badge per step (Grounded vs Assumption Flag)    │
│     - Ishikawa 6M Fishbone toggle (Machine, Method, Material, etc.)    │
│                                                                        │
│  3. Timeline:                                                          │
│     - Chronological Event Rail (Pre-incident → Anomaly → Trip → Fix)  │
│     - Telemetry Callouts (Vibration 5.8 mm/s vs 5.0 mm/s envelope)     │
│     - Clickable Citations opening SourceViewerModal                    │
│                                                                        │
│  4. Corrective Actions:                                                │
│     - Action Tracker Table: Containment (D3), Permanent (D5), Preven.  │
│     - Owner, Due Date, Verification Metric & Status                    │
│     - Historical Match Cross-Reference (Near_Miss_Report_2023 link)    │
└────────────────────────────────────────────────────────────────────────┘
```

#### How `ArtifactPanel.jsx` Detects the 8D Studio
In `ArtifactPanel.jsx`:
```javascript
function isEightDArtifact(artifact) {
  if (!artifact) return false;
  if (artifact.type === '8d') return true;
  if (artifact.title && /8d|incident|root cause|rca/i.test(artifact.title)) return true;
  if (typeof artifact.content === 'object' && artifact.content.disciplines) return true;
  if (typeof artifact.content === 'string' && (
      artifact.content.includes('"d1_team"') || 
      artifact.content.includes('"eight_disciplines"') ||
      artifact.content.includes('8D Incident Studio') ||
      artifact.content.includes('D1: Team Formation')
  )) return true;
  return false;
}
```
If `isEightDArtifact(artifact)` is true:
- Render `<EightDIncidentStudio artifact={artifact} onSourceClick={onSourceClick} onClose={onClose} />`!
- Pass `onSourceClick` from `App.jsx` to `ArtifactPanel` so clicking any citation immediately triggers the existing `SourceViewerModal`.

#### Direct Access from Sidebar
In addition to opening via chat artifact buttons, `Sidebar.jsx` (under the "Data Sources" or visualizer section near "Data Graph" and "Asset Topology") can provide an **"8D Incident Studio"** button (`Target` or `ShieldAlert` icon). Clicking this button sets an initial or active incident report in `activeArtifact`, allowing operators to inspect incident analyses immediately.

---

### 2.4. Visualization & Charting Libraries Analysis

#### Available Libraries in `package.json`
| Library | Version | Strengths | Ideal Use Case |
|---|---|---|---|
| `mermaid` | `^11.13.0` | Already installed. Native flowcharts (`graph TD/LR`), timelines, state diagrams. | Automated text-to-diagram rendering. |
| `react-force-graph-2d` | `^1.29.1` | Already installed. Canvas force-directed graph. | Semantic knowledge graph, free-form network clustering. |
| `d3-force` | `^3.0.0` | Already installed. Tree layout calculations (used in `MindMap.jsx`). | Algorithmic hierarchical tree layout calculation. |
| `framer-motion` | `^11.5.0` | Already installed. Declarative physics-based animations. | Smooth tab transitions, expanding cards, node hover effects. |
| `lucide-react` | `^0.360.0` | Already installed. 1000+ vector SVG icons. | Industrial telemetry icons, severity markers, discipline badges. |

#### Evaluation for 5-Why Tree, Ishikawa Fishbone, and Timeline

1. **5-Why Tree Visualization**:
   - **Recommended Approach: Native React + SVG Flow Cards (Hybrid)**:
     - A clean horizontal/vertical tree rendered with React DOM cards connected by SVG bezier curves (`M x1 y1 C ... x2 y2`).
     - **Why this beats Canvas or External Plugins**:
       - 100% Vector Quality in Print/PDF: Canvas renders become blurry or disappear when exported to PDF. Pure SVG/DOM retains crisp vector lines and text.
       - Interactive DOM: Each node can host interactive badges ("Verified in Doc A12", "Flagged Assumption"), copy buttons, and drill-down citation clicks.
       - Accessibility & Responsiveness: Adapts to screen resize without canvas coordinate recalibration.
   - **Alternative (Mermaid Flowchart)**: Mermaid can render `graph TD` diagrams via `mermaid.render()`. However, styling custom citation buttons inside Mermaid SVG nodes is brittle compared to native React SVG.

2. **Ishikawa (Fishbone) Diagram**:
   - **Recommended Approach: Structured React SVG Fishbone Canvas**:
     - Central horizontal spine running to the Incident Effect (e.g., "Pump Seal Shatter & Leak").
     - 6 standard industrial 45-degree angled ribs:
       - **Machinery** (Vibration > 5.5 mm/s, Seal tolerances)
       - **Methods** (Alert response protocols, shutdown criteria)
       - **Materials** (Ceramic seal hardness, coolant chemical specs)
       - **Manpower** (Operator threshold misconceptions, training gaps)
       - **Measurement** (Vibration sensor calibration, alarm limits)
       - **Environment** (High operating pressure, thermal cycling)
     - Sub-branches listing specific findings with grounding status.
     - Fully scalable vector SVG that prints with razor sharpness.

3. **Chronological Timeline**:
   - **Recommended Approach: Tailwind Step-Rail Component**:
     - Chronological timeline rail with vertical gradient connector line (`before:bg-indigo-200`).
     - Event nodes color-coded by severity: Normal (slate), Pre-warning (amber), Critical Trip (rose), Containment (indigo), Resolution (emerald).
     - Each card displays: `Timestamp`, `Event Title`, `Telemetry Tag` (e.g., `5.8 mm/s vibration`), `Action Taken`, and `Verifiable Citation Pill`.

---

### 2.5. Implementation Strategy: Export Audit Package (Print-Ready Compliance Document)

#### Acceptance Criterion Review
"The 'Export Audit Package' produces a timestamped, print-ready compliance document formatted for regulatory and quality audits."

#### Limitations of the Current Implementation
In `ChatInterface.jsx:96-176`:
- `handleDownloadReport` creates a hidden `iframe`, inserts basic HTML, and calls `window.print()`.
- **Critical Flaw**: Line 101 explicitly wipes out all artifacts:
  `const cleanContent = msg.content.replace(/\[ARTIFACT:.*?\][\s\S]*?\[\/ARTIFACT\]/g, '').trim();`
- Plain chat text is printed, losing the rich structured disciplines, diagrams, and verification matrices.

#### Proposed Architecture: Certified 8D Audit Package Generator
Create an export utility (e.g., `frontend/src/utils/exportAuditPackage.js` or directly inside the studio) that generates a complete, certified, ISO 9001:2015 / IATF 16949 compliant industrial document.

#### Key Compliance Document Sections
1. **Header & Authentication Seal**:
   - Organization: `INDUSTRIAL MIND OS - QUALITY INTELLIGENCE & RELIABILITY SYSTEM`
   - Document Title: `CERTIFIED 8D ROOT CAUSE ANALYSIS & INCIDENT AUDIT PACKAGE`
   - Audit Metadata: Report ID (`RCA-2026-PUMP-A12-001`), Incident Timestamp, Report Generation Timestamp (UTC), Verification Authority (`System Autonomous Agent + Plant Engineering Oversight`).
   - Security Classification: `CONFIDENTIAL - REGULATORY COMPLIANCE RECORD`.
2. **Section D1: Team & Scope**:
   - Asset ID, System Loop, Plant Location, Assigned Lead Engineer, Cross-Functional Team.
3. **Section D2: Problem Definition (5W2H Framework)**:
   - What, Where, When, Who, Why, How, How Much (Downtime: 2.5 hrs, Spill: 12L coolant).
4. **Section D3: Interim Containment Action (ICA)**:
   - Containment procedures, implementation time, effectiveness verification.
5. **Section D4: Root Cause Determination (RCA)**:
   - Verifiable 5-Why progression table (Step, Observation, Grounded Document Evidence, Status).
   - Ishikawa 6M causal summary table.
   - Escape Point explanation (why monitoring failed to catch early).
6. **Chronological Event Timeline**:
   - Authoritative minute-by-minute log with sensor telemetry and operator actions.
7. **Section D5 & D6: Permanent Corrective Actions (PCA) & Validation**:
   - Technical action, responsible party, target deadline, validation metrics.
8. **Section D7: Systemic Preventative Measures & Historical Matching**:
   - Cross-reference with historical incidents (e.g., `Near_Miss_Report_2023.txt`).
   - OEM operating limit updates (maximum allowable vibration strictly 5.0 mm/s).
9. **Section D8: Team Sign-Off & Verification Stamp**:
   - Digital auditor approval block, verification cryptographic hash / checksum, ISO 9001 audit statement.
10. **Evidence & Citation Appendix**:
    - Comprehensive list of cited internal manuals, maintenance logs, and sensor streams with exact snippet quotes.

#### Print Styling Specifications (`@media print`)
- **Page Constraints**: `@page { size: A4 portrait; margin: 15mm; }`
- **Pagination & Page Breaks**: `break-inside: avoid;` on table rows, cards, and signature blocks.
- **Color Fidelity**: Force `print-color-adjust: exact; -webkit-print-color-adjust: exact;` so headers, badges, and status colors print accurately.
- **Dual Export Mode**:
  - `Print to PDF / Laser Printer` via hidden iframe with auto-print.
  - `Download Offline Evidence Bundle (.html)` allowing plant teams to archive the self-contained audit package directly into their Document Management System (DMS).

---

## 3. Data Contract: Structured 8D Report Schema

To ensure seamless coordination between backend LangGraph generators and the frontend studio, the 8D report data model should conform to the following JSON schema:

```json
{
  "report_id": "RCA-8D-2026-0042",
  "incident_title": "Primary Cooling Loop Pump-A12 Seal Failure & Leak",
  "generated_at": "2026-10-05T13:30:00Z",
  "asset": {
    "tag": "Pump-A12",
    "name": "Primary Coolant Circulation Pump",
    "location": "Primary Cooling Loop, Sector 4",
    "severity": "CRITICAL",
    "downtime_hours": 2.5
  },
  "d1_team": {
    "leader": "Reliability Engineering Lead",
    "members": ["Operations Specialist", "Mechanical Technician", "Safety Auditor"]
  },
  "d2_problem": {
    "statement": "Catastrophic inboard ceramic seal fracture resulting in coolant leak during routine operation.",
    "what": "Mechanical seal fracture",
    "where": "Sector 4, Pump-A12",
    "when": "Operating window under sustained 5.8 mm/s vibration",
    "how_much": "15 min emergency containment, 12L fluid spill"
  },
  "d3_containment": [
    {
      "action": "Immediate loop isolation and emergency spill barrier deployment",
      "implemented_at": "2026-10-04T08:15:00Z",
      "effectiveness": "100% contained within 15 minutes",
      "status": "VERIFIED"
    }
  ],
  "d4_root_cause": {
    "five_whys": [
      { "level": 1, "why": "Why did the coolant spill occur?", "cause": "Inboard ceramic seal shattered", "grounded": true, "citation_id": "cite-01" },
      { "level": 2, "why": "Why did the inboard seal shatter?", "cause": "Sustained high-frequency mechanical vibration fatigue", "grounded": true, "citation_id": "cite-01" },
      { "level": 3, "why": "Why was the pump operating under high vibration?", "cause": "Vibration levels reached 5.8 mm/s for 48 hours without shutdown", "grounded": true, "citation_id": "cite-02" },
      { "level": 4, "why": "Why was the pump not shut down at 5.8 mm/s?", "cause": "Operators believed warning threshold was 6.5 mm/s rather than OEM limit", "grounded": true, "citation_id": "cite-02" },
      { "level": 5, "why": "Why did operators misinterpret the vibration threshold?", "cause": "Generic plant guideline was consulted instead of OEM equipment-specific operating envelope (5.0 mm/s limit)", "grounded": true, "citation_id": "cite-03" }
    ],
    "fishbone": {
      "machinery": ["Vibration exceeded 5.0 mm/s OEM limit", "Ceramic seal fatigue fracture"],
      "methods": ["Generic shutdown guidelines used instead of asset-specific envelope"],
      "materials": ["Standard coolant fluid within chemical specs"],
      "manpower": ["Operators lacked training on A-series specific limits"],
      "measurement": ["Sensors correctly logged 5.8 mm/s; alert logic lacked interlock"],
      "environment": ["High continuous duty cycle in Sector 4"]
    },
    "root_cause_summary": "Failure to enforce asset-specific OEM vibration thresholds (5.0 mm/s limit) leading to prolonged operation at 5.8 mm/s and ceramic seal fatigue fracture.",
    "escape_point": "Automated alarm system lacked hard shutdown trip logic at 5.5 mm/s, allowing manual discretion."
  },
  "timeline": [
    { "timestamp": "T - 48h", "event": "Vibration elevated to 5.2 mm/s", "category": "Telemetry", "severity": "Warning", "citation": "Telemetry Log B" },
    { "timestamp": "T - 24h", "event": "Vibration sustained at 5.8 mm/s; operator acknowledged alert without shutdown", "category": "Operator Action", "severity": "Elevated", "citation": "Operations Shift Log" },
    { "timestamp": "T - 0h", "event": "Inboard seal catastrophic fracture; coolant leak triggered floor sensor", "category": "Failure", "severity": "Critical", "citation": "Near_Miss_Report_2023.txt" },
    { "timestamp": "T + 15m", "event": "Emergency containment barriers deployed; drainage valve isolated", "category": "Containment", "severity": "Info", "citation": "Incident Report 2023-11-04" }
  ],
  "d5_d6_corrective_actions": [
    {
      "id": "PCA-01",
      "discipline": "D5",
      "action": "Implement automated PLC hard trip interlock on Pump-A12 at 5.5 mm/s vibration",
      "owner": "Controls Team",
      "target_date": "2026-10-15",
      "status": "In Progress"
    },
    {
      "id": "PCA-02",
      "discipline": "D5",
      "action": "Replace shattered ceramic seal with OEM reinforced silicon-carbide seal",
      "owner": "Maintenance Lead",
      "target_date": "2026-10-06",
      "status": "Implemented"
    }
  ],
  "d7_preventative_controls": [
    {
      "control": "Asset Operating Envelope Alignment: Re-tune supervisory alarms for all A-series pumps to 5.0 mm/s warning / 5.5 mm/s trip",
      "historical_match": "Direct correlation to Near_Miss_Report_2023.txt (Pump-A12 ceramic seal failure under 5.8 mm/s)",
      "status": "Active"
    },
    {
      "control": "Mandatory technician re-training on equipment-specific OEM tolerance limits",
      "status": "Scheduled"
    }
  ],
  "d8_closure": {
    "sign_off_status": "APPROVED",
    "quality_engineer": "Senior Industrial Reliability Auditor",
    "iso_standard": "ISO 9001:2015 §10.2 / IATF 16949:2016"
  },
  "citations": [
    { "id": "cite-01", "source": "Near_Miss_Report_2023.txt", "snippet": "During routine operations, Pump A12 experienced a catastrophic mechanical seal failure." },
    { "id": "cite-02", "source": "Near_Miss_Report_2023.txt", "snippet": "Post-incident analysis revealed that the pump had been operating with a severe vibration level of 5.8 mm/s for 48 hours prior to the failure." },
    { "id": "cite-03", "source": "Pump_A12_OEM_Manual.pdf", "snippet": "The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s as per the OEM manual." }
  ]
}
```

---

## 4. Recommendations for Implementation Phase

1. **Create `EightDIncidentStudio` Component**:
   - Implement `frontend/src/components/EightDStudio/EightDIncidentStudio.jsx`.
   - Implement subcomponents:
     - `OverviewTab.jsx`
     - `FiveWhyTreeTab.jsx` (with 5-Why progression and Ishikawa Fishbone toggle)
     - `TimelineTab.jsx`
     - `CorrectiveActionsTab.jsx`
2. **Wire into `ArtifactPanel.jsx` & `App.jsx`**:
   - Detect 8D format in `ArtifactPanel.jsx` and render `<EightDIncidentStudio>`.
   - Forward `onSourceClick` prop from `App.jsx` through `ArtifactPanel` to the studio so citations trigger `SourceViewerModal`.
3. **Implement Export Utility (`exportAuditPackage.js`)**:
   - Build a clean HTML document generator formatted with ISO 9001/IATF 16949 compliant styling and `@media print` rules.
   - Inject into a hidden iframe and trigger `iframe.contentWindow.print()`.
   - Add a secondary button for downloading the raw HTML/JSON evidence package.
4. **Fix Existing `ChatInterface.jsx` Artifact Strip Bug**:
   - Ensure the message export button in `ChatInterface.jsx` does not strip the 8D artifact when an incident report is present.
5. **Verify Build**:
   - Re-run `npm run build` after adding components to guarantee 100% clean compilation.
