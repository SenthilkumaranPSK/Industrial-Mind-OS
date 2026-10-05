# Handoff Report: Frontend Codebase Survey for Automated RCA & 8D Studio

**Agent**: `explorer_survey_frontend`  
**Working Directory**: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_survey_frontend`  
**Parent Agent**: `ef889b9f-7189-4139-bdab-296efd4f52ff`  
**Handoff Type**: Hard (Investigation & Survey Complete)  

---

## 1. Observation

### O1. Build System & Configuration
- **File**: `frontend/package.json` (lines 6-10, 11-30)
  - Scripts: `"build": "vite build"`, `"dev": "vite"`, `"preview": "vite preview"`.
  - Dependencies installed: `react` (^18.2.0), `react-dom` (^18.2.0), `lucide-react` (^0.360.0), `mermaid` (^11.13.0), `framer-motion` (^11.5.0), `react-force-graph-2d` (^1.29.1), `d3-force` (^3.0.0), `react-markdown` (^10.1.0), `remark-gfm` (^4.0.1), `clsx`, `tailwind-merge`.
  - DevDependencies: `@vitejs/plugin-react` (^6.1.0), `tailwindcss` (^3.4.3), `postcss` (^8.4.38), `autoprefixer` (^10.4.19), `vite` (^8.2.2).
- **File**: `frontend/vite.config.js` (lines 1-8): Minimal Vite configuration with React plugin.
- **File**: `frontend/tailwind.config.js` (lines 1-12): Content patterns match `"./index.html"`, `"./src/**/*.{js,ts,jsx,tsx}"`.
- **Command execution**: `npm run build` executed in `C:\000 MINE\My Codzz\Industrial Mind OS\frontend`:
  ```
  vite v8.2.2 building client environment for production...
  ✓ 2766 modules transformed.
  dist/index.html                   0.45 kB │ gzip:   0.32 kB
  dist/assets/index-DsqLlfEf.css   41.83 kB │ gzip:   7.61 kB
  dist/assets/index-B22YsQSE.js   593.56 kB │ gzip: 181.53 kB
  ✓ built in 1.57s
  ```
  Exited with code 0. Zero compiler errors.

### O2. UI Architecture & Artifact Panel Rendering
- **File**: `frontend/src/App.jsx`
  - Line 24: `const [activeArtifact, setActiveArtifact] = useState(null);`
  - Lines 400-412: Right sidebar renders `<ArtifactPanel artifact={activeArtifact} onClose={() => setActiveArtifact(null)} />` when `activeArtifact` is non-null, expanding to `lg:w-1/2 w-full` (replacing the default `lg:w-[360px]` InsightPanel).
- **File**: `frontend/src/components/MarkdownRenderer.jsx`
  - Lines 7-24: `extractArtifacts(content)` runs regex `/\[ARTIFACT:\s*([^\]]+)\]([\s\S]*?)\[\/ARTIFACT\]/gi`.
  - Lines 26-48: `ArtifactInlineButton` displays an inline pill button for each extracted artifact.
  - Lines 118-129: Clicking the inline button calls `onArtifactOpen(artifact)`.
- **File**: `frontend/src/components/ArtifactPanel.jsx`
  - Lines 4-11: `detectArtifactType(content)` tests for `'html'`, `'table'`, `'code'`.
  - Lines 58-157: `HtmlView` renders content in an iframe with Tailwind CDN.
  - Lines 159-202: `TableView` parses markdown tables into a styled HTML table.
  - Lines 23-56: `CodeView` renders syntax-highlighted code.
  - Lines 261-276: Universal Tab Bar switches between `preview`, `code`, and `table`.
- **File**: `frontend/src/components/SourceViewerModal.jsx` (lines 1-60):
  - Displays modal for exact cited text snippets with document context. Triggered via `setActiveSource` in `App.jsx:27`.

### O3. Existing Print / Audit Export Logic
- **File**: `frontend/src/components/ChatInterface.jsx`
  - Lines 96-176 (`handleDownloadReport`):
    - Line 101: `const cleanContent = msg.content.replace(/\[ARTIFACT:.*?\][\s\S]*?\[\/ARTIFACT\]/g, '').trim();`
    - Creates an offscreen `iframe`, writes HTML with CSS styles, and calls `iframe.contentWindow.print()`.
    - Note: Artifact content is currently explicitly removed from the export in line 101.

### O4. Available Visualization Tools
- **Files**:
  - `package.json:16`: `"mermaid": "^11.13.0"` is installed.
  - `package.json:19`: `"react-force-graph-2d": "^1.29.1"` is installed.
  - `package.json:13`: `"d3-force": "^3.0.0"` is installed.
  - `package.json:14`: `"framer-motion": "^11.5.0"` is installed.
  - `frontend/src/components/MindMap.jsx`: Implements custom tree coordinate projection (`calculateTreeLayout` lines 74-130) and canvas bezier S-curves (`ForceGraph2D` lines 285-380).

---

## 2. Logic Chain

1. **Build Reliability**:
   - From O1, `npm run build` compiles 2766 modules cleanly in 1.57s without any compilation failure. Adding new standard React components will not conflict with Vite or PostCSS/Tailwind configurations.
2. **Artifact Integration Point**:
   - From O2, `App.jsx` already contains a two-state layout: `activeArtifact === null` shows `InsightPanel`, while `activeArtifact !== null` expands the right panel to 50% screen width and renders `ArtifactPanel`.
   - Furthermore, `MarkdownRenderer.jsx` extracts `[ARTIFACT: Title] ... [/ARTIFACT]` tags and triggers `onArtifactOpen`.
   - Therefore, the 8D Incident Studio does NOT require changing the core layout of `App.jsx`; it can be rendered as a dedicated sub-view in `ArtifactPanel.jsx` when the artifact represents an 8D report (`isEightDArtifact(artifact)`).
3. **Citation Drill-Down Wiring**:
   - From O2, `App.jsx` has `const [activeSource, setActiveSource] = useState(null)` and conditionally mounts `SourceViewerModal`.
   - `ChatInterface.jsx` passes `onSourceClick={setActiveSource}`.
   - Therefore, passing `onSourceClick` into `ArtifactPanel` will allow citation pills within the 8D report (e.g. `[Source: Near_Miss_Report_2023.txt]`) to open `SourceViewerModal` with exact verified evidence snippets.
4. **Visualization Selection**:
   - From O4, `mermaid`, `d3-force`, and `framer-motion` are installed.
   - However, for print fidelity and PDF compliance, canvas-based graphs rasterize and often fail to print or appear pixelated.
   - Pure React + SVG + Tailwind components for the 5-Why tree, Ishikawa fishbone, and Timeline provide:
     - 100% vector sharpness during browser print-to-PDF.
     - Direct DOM event listeners on individual nodes (for citation clicks and tooltip inspection).
     - Zero additional bundle overhead.
5. **Print-Ready Audit Package Export**:
   - From O3, the iframe print method in `ChatInterface.jsx` works reliably across Chrome/Firefox/Edge.
   - However, line 101 currently strips artifacts.
   - To deliver Acceptance Criterion 3 ("Export Audit Package produces a timestamped, print-ready compliance document"), the 8D Studio must feature its own `Export Audit Package` button that generates a dedicated ISO 9001/IATF 16949 compliant document with:
     - Report header, plant metadata, asset tag, severity rating.
     - Disciplines D1 through D8.
     - 5-Why tabular causal progression.
     - Event timeline log with telemetry callouts.
     - Corrective and preventative action matrix.
     - Verification checklist and digital auditor signature block.
     - Using `@media print` with `@page { size: A4; margin: 15mm; }` and `break-inside: avoid;`.

---

## 3. Caveats

- **No automated frontend test runner**: `package.json` contains no `test` or `jest`/`vitest` script. Automated frontend verification relies on `npm run build` syntax and bundle checking.
- **Backend LLM generation format**: The backend synthesizer prompt must be configured to output valid JSON or structured tags for the 8D report within the `[ARTIFACT: 8D Incident Report - ...] <data> [/ARTIFACT]` block so the frontend can parse all 8 disciplines cleanly.
- **Iframe CSS containment in print**: When printing via hidden iframe, styles must either include inline CSS or inject Tailwind styles so that print previews render identical to the screen.

---

## 4. Conclusion

1. **Build System**: Clean React 18 + Vite 8.2.2 pipeline (`npm run build` succeeds in 1.57s).
2. **Integration Architecture**:
   - Add `frontend/src/components/EightDStudio/EightDIncidentStudio.jsx` with 4 tabs: `Overview`, `5-Why Tree`, `Timeline`, `Corrective Actions`.
   - Update `ArtifactPanel.jsx` to recognize 8D artifacts and mount `EightDIncidentStudio`.
   - Pass `onSourceClick` from `App.jsx` to `ArtifactPanel` to enable citation drill-downs.
   - Add a direct launch button for the 8D Incident Studio in `Sidebar.jsx`.
3. **Visualization Approach**: Pure React + SVG and Tailwind for the 5-Why tree, Ishikawa fishbone diagram, and timeline rail for maximum vector print sharpness and interactive citation integration.
4. **Export Audit Package**: Implement a dedicated iframe print utility and HTML evidence package downloader that renders certified ISO 9001 / IATF 16949 audit documents with UTC timestamps, full 8D sections, and digital auditor signatures.

---

## 5. Verification Method

To independently verify these findings:
1. **Frontend Build Verification**:
   ```bash
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\frontend"
   npm run build
   ```
   *Expected outcome*: Exit code 0, completes in under 3 seconds, `dist/` directory generated.
2. **Inspect Existing Artifact Wiring**:
   - Inspect `frontend/src/App.jsx:400-412` to verify `activeArtifact` conditionally mounts `ArtifactPanel`.
   - Inspect `frontend/src/components/MarkdownRenderer.jsx:7-24` to verify `extractArtifacts()` regex pattern.
   - Inspect `frontend/src/components/ArtifactPanel.jsx:205-285` to verify current tab and preview mechanisms.
3. **Inspect Print Implementation**:
   - Inspect `frontend/src/components/ChatInterface.jsx:96-176` to verify hidden iframe print technique and observe line 101 artifact removal.
4. **Invalidation Conditions**:
   - Any modification to `package.json` removing Vite or Tailwind.
   - Changes to `App.jsx` that remove `activeArtifact` state.
