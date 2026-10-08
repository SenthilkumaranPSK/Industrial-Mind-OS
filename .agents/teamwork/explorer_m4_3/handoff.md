# Milestone 4 — Compliance Print Styling, Export Integration & Frontend Build Verification
**Agent**: `explorer_m4_3`  
**Working Directory**: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_3`  
**Date**: 2026-10-07T10:35:00Z  
**Type**: Hard Handoff (Investigation & Architecture Specification)

---

## 1. Observation

### 1.1 Frontend Configuration & Environment
- **`frontend/package.json`**:
  - React version: `^18.2.0`, React DOM: `^18.2.0`
  - Build tool: `vite` v8.2.2 with `@vitejs/plugin-react` v6.1.0
  - Styling: `tailwindcss` v3.4.3, `postcss` v8.4.38, `autoprefixer` v10.4.19
  - Utility libraries: `clsx` v2.1.0, `tailwind-merge` v2.2.0, `lucide-react` v0.360.0
  - Scripts: `"build": "vite build"`, `"dev": "vite"`, `"preview": "vite preview"`
- **`frontend/src/api.js`** (lines 1-4):
  ```javascript
  // Single source of truth for the backend origin.
  // Override at build time with VITE_API_URL (e.g. VITE_API_URL=https://api.example.com).
  export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  ```
- **`frontend/src/index.css`** (lines 1-9):
  Contains standard Tailwind directives: `@tailwind base; @tailwind components; @tailwind utilities;` with base body styles (`@apply bg-gray-50 text-gray-900 antialiased;`).
- **`frontend/src/App.jsx`** (lines 368, 385, 400):
  ```jsx
  <div className="flex h-screen bg-[#0f172a] overflow-hidden font-sans text-slate-800">
  ```
  The application shell enforces `h-screen overflow-hidden` on the outer layout container. In standard browser printing, this causes multi-page clipping unless explicitly reset in `@media print`.

### 1.2 Backend Export-Evidence API & Schemas
- **`backend/api/rca_schemas.py`** (lines 619-653):
  - Request Model:
    ```python
    class ExportEvidenceRequest(BaseModel):
        report_id: str = Field(..., description="8D report ID e.g. 8D-2023-PUMP-A12-001")
        format: str = Field(default="html", description="Export format: 'html' or 'json'")
    ```
  - Response Model:
    ```python
    class ExportEvidenceResponse(BaseModel):
        content: str = Field(..., description="Rendered HTML string or JSON string")
        sha256_checksum: str = Field(..., description="Cryptographic SHA-256 digest")
        filename: str = Field(..., description="Suggested filename e.g. 8D-2023-PUMP-A12-001_Audit_Package.html")
    ```
- **`backend/api/rca_router.py`** (lines 230-276):
  Endpoint `POST /api/v1/rca/export-evidence` is implemented and verified. It fetches the report from `report_store`, calls `generate_compliance_package(report, format=fmt)`, and returns `ExportEvidenceResponse`.
- **`backend/services/compliance_package.py`** (lines 438-600, 885-920):
  Generates compliance packages conforming to:
  - ISO 9001:2015 Clause 10.2 (Nonconformity and Corrective Action)
  - IATF 16949:2016 Section 10.2.3 (Problem Solving)
  - AIAG 8D Standard & AIAG-VDA FMEA Alignment
  The generated HTML already specifies:
  - `@page { size: letter portrait; margin: 15mm 18mm; }`
  - `.page-break { page-break-after: always; break-after: page; }`
  - `.avoid-break { page-break-inside: avoid; break-inside: avoid; }`
  - Canonical SHA-256 seal container with monospace fingerprint
  - Dual signature lines: Quality Assurance Manager and Plant Operations Director.

### 1.3 Frontend Build Diagnostic
Executed via PowerShell:
```powershell
npm run build
```
Result:
- **Exit code**: `0` (Success)
- **Time**: 27.40s
- **Transformed**: 2,766 modules
- **Output Artifacts**:
  - `dist/index.html` (0.45 kB)
  - `dist/assets/index-DsqLlfEf.css` (41.83 kB)
  - `dist/assets/index-B22YsQSE.js` (593.56 kB)
- **Diagnostics**:
  - Zero syntax or compilation errors.
  - Informational warning: `index-B22YsQSE.js` exceeds 500 kB chunk threshold due to vendor graph libraries (`mermaid`, `d3-force`, `lucide-react`).
  - Baseline frontend is healthy and ready for Milestone 4 component additions.

---

## 2. Logic Chain

1. **Outer Viewport Unclipping**:
   - *Observation*: `App.jsx:368` sets `h-screen overflow-hidden` on `#root` wrapper.
   - *Deduction*: Without print resets, `window.print()` will freeze layout at viewport height (~800px), clipping pages 2+ of the 8D incident report.
   - *Resolution*: `@media print` must force `height: auto !important; min-height: 100% !important; overflow: visible !important; position: static !important;` across `html`, `body`, `#root`, and all scrollable parent containers.

2. **UI Chrome Suppression**:
   - *Observation*: The application includes `Sidebar`, `ChatInterface`, floating action buttons, modals, tabs, and dark-theme headers.
   - *Deduction*: An ISO 9001 / IATF 16949 auditor will reject documents containing chat prompts, buttons, or dark application backgrounds.
   - *Resolution*: Apply `.no-print { display: none !important; }` and target `nav, aside, header.no-print, button:not(.print-keep), input, textarea` in `@media print`.

3. **Dual Representation Strategy (Screen vs. Print Dossier)**:
   - *Observation*: On screen, users require an interactive 4-tab interface (Overview, 5-Why Tree, Timeline, Corrective Actions) with zoomable SVGs and clickable citation badges (`explorer_m4_1`, `explorer_m4_2`).
   - *Deduction*: If users print while on Tab 1, printing only Tab 1 violates IATF 16949 §10.2.3, which demands complete D1–D8 records, containment verification, 5-Why root cause chain, and sign-offs in one audit package.
   - *Resolution*: Embed a dedicated `<EightDAuditPrintDossier report={report} />` inside `EightDIncidentStudio.jsx` marked with `className="hidden print:block"`, while wrapping interactive screen tabs in `className="no-print"`. This ensures 100% complete D1–D8 printing on any browser `print` invocation, regardless of which screen tab is active.

4. **Pagination Control & Break Rules**:
   - *Observation*: Multi-page printouts often slice tables, diagram nodes, or signature boxes in half across page edges.
   - *Resolution*:
     - Enforce `@page { size: letter portrait; margin: 15mm 18mm; }`.
     - Set `.avoid-break { page-break-inside: avoid !important; break-inside: avoid !important; }` on tables, cards, 5-Why nodes, and the D8 sign-off block.
     - Set `.page-break { page-break-after: always !important; break-after: page !important; }` to logically separate major sections.
     - Add `thead { display: table-header-group; }` and `tr { page-break-inside: avoid; }` so table headers cleanly repeat on subsequent pages.

5. **Certified Export Action Wiring**:
   - *Observation*: Backend `/api/v1/rca/export-evidence` is tested and operational for both HTML and JSON formats with canonical SHA-256 checksums (`rca_router.py:236`).
   - *Resolution*: Provide a multi-action "Export Audit Package" button in `EightDIncidentStudio`:
     - **Quick Print / PDF**: Triggers `window.print()` (leveraging `printStyles.css`).
     - **Download Certified HTML**: Calls `POST /api/v1/rca/export-evidence` (`format: 'html'`), saves blob as `.html` with SHA-256 seal.
     - **Download JSON Evidence**: Calls `POST /api/v1/rca/export-evidence` (`format: 'json'`), saves blob as `.json` with SHA-256 seal.

---

## 3. Caveats

1. **Browser Default Headers/Footers**:
   Browser print dialogs (Chrome/Edge/Firefox) often append automatic browser headers (date, URL) and footers (page title). For pristine regulatory audit submissions, users should ensure "Headers and footers" is disabled in their print dialog so that the ISO 9001:2015 CSS running headers and page numbers take precedence.
2. **Background Graphics Setting**:
   Certain badge tints and table borders rely on `-webkit-print-color-adjust: exact;` and `print-color-adjust: exact;`. While supported in all modern browsers, users whose printer drivers force pure monochrome will see high-contrast grayscale borders instead of colored badges. The CSS design includes solid border fallbacks specifically for this case.
3. **Offline / Standalone Fallback**:
   If the backend server is unreachable (network timeout or offline mode), the export helper must fall back gracefully to client-side `window.print()` or client-side JSON serialization, ensuring users are never blocked from retrieving their report.

---

## 4. Conclusion & Concrete Design Specifications

### 4.1 Specification: `frontend/src/components/EightDStudio/printStyles.css`

Workers must create `frontend/src/components/EightDStudio/printStyles.css` with the following production-grade rules:

```css
/* ==========================================================================
   Industrial Mind OS - ISO 9001:2015 & IATF 16949 Compliance Print Stylesheet
   Location: frontend/src/components/EightDStudio/printStyles.css
   Standards:
     - ISO 9001:2015 Clause 10.2 (Nonconformity and Corrective Action)
     - IATF 16949:2016 Section 10.2.3 (Problem Solving)
     - AIAG 8D Standard & AIAG-VDA FMEA Alignment
   ========================================================================== */

@page {
  size: letter portrait;
  margin: 15mm 18mm;
}

@media print {
  /* 1. Global Viewport & Container Unclipping */
  html,
  body,
  #root,
  #app,
  .h-screen,
  .overflow-hidden,
  .overflow-auto,
  .overflow-y-auto {
    height: auto !important;
    min-height: 100% !important;
    overflow: visible !important;
    position: static !important;
    background: #ffffff !important;
    color: #0f172a !important;
    margin: 0 !important;
    padding: 0 !important;
    box-shadow: none !important;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    font-size: 11pt !important;
    line-height: 1.4 !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  /* 2. Interactive UI Chrome Hiding */
  .no-print,
  aside,
  nav,
  header.app-header,
  .chat-interface,
  .studio-tabs-bar,
  .studio-action-bar,
  .modal-backdrop,
  .backdrop-blur-sm,
  button:not(.print-keep),
  input,
  textarea,
  [data-sidebar],
  [data-testid="sidebar"] {
    display: none !important;
  }

  /* 3. Studio Print Dossier Display */
  .eight-d-print-dossier,
  .audit-container {
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    background: #ffffff !important;
    border: none !important;
    box-shadow: none !important;
  }

  /* 4. Page Break Controls */
  .page-break {
    page-break-after: always !important;
    break-after: page !important;
  }

  .page-break-before {
    page-break-before: always !important;
    break-before: page !important;
  }

  .avoid-break {
    page-break-inside: avoid !important;
    break-inside: avoid !important;
  }

  /* 5. Tables & Grids */
  table.audit-table {
    width: 100% !important;
    border-collapse: collapse !important;
    font-size: 9.5pt !important;
    margin-bottom: 12pt !important;
    page-break-inside: auto !important;
  }

  table.audit-table thead {
    display: table-header-group !important;
  }

  table.audit-table tr {
    page-break-inside: avoid !important;
    break-inside: avoid !important;
  }

  table.audit-table th {
    background-color: #f1f5f9 !important;
    color: #1e293b !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    font-size: 8pt !important;
    letter-spacing: 0.5px !important;
    padding: 6pt 8pt !important;
    border: 1px solid #94a3b8 !important;
  }

  table.audit-table td {
    padding: 6pt 8pt !important;
    border: 1px solid #cbd5e1 !important;
    vertical-align: top !important;
    color: #0f172a !important;
  }

  table.audit-table tr:nth-child(even) td {
    background-color: #f8fafc !important;
  }

  /* 6. Formal Audit Header */
  .audit-header {
    border: 2px solid #1e3a8a !important;
    border-left: 8px solid #1e3a8a !important;
    border-radius: 4px !important;
    padding: 12pt 16pt !important;
    margin-bottom: 16pt !important;
    background-color: #f8fafc !important;
    page-break-inside: avoid !important;
  }

  .audit-header h1 {
    font-size: 15pt !important;
    color: #1e3a8a !important;
    margin: 0 0 4pt 0 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    font-weight: 800 !important;
  }

  .audit-subtitle {
    font-size: 8.5pt !important;
    color: #475569 !important;
    margin: 0 0 8pt 0 !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
  }

  .sha-seal {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    font-size: 8pt !important;
    background-color: #f1f5f9 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 4px !important;
    padding: 4pt 8pt !important;
    color: #0f172a !important;
    word-break: break-all !important;
    margin: 6pt 0 0 0 !important;
  }

  .meta-grid {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 8pt !important;
    margin-top: 10pt !important;
    padding-top: 8pt !important;
    border-top: 1px solid #cbd5e1 !important;
    font-size: 8.5pt !important;
  }

  .meta-item strong {
    display: block !important;
    color: #64748b !important;
    font-size: 7.5pt !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
  }

  /* 7. Discipline Section Headings */
  h2.discipline-heading {
    font-size: 11pt !important;
    color: #1e3a8a !important;
    border-bottom: 1.5px solid #1e3a8a !important;
    padding-bottom: 4pt !important;
    margin-top: 14pt !important;
    margin-bottom: 8pt !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
    page-break-after: avoid !important;
    break-after: avoid !important;
  }

  /* 8. Badges */
  .badge {
    display: inline-block !important;
    padding: 1.5pt 5pt !important;
    border-radius: 3px !important;
    font-size: 7.5pt !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
  }

  .badge-critical {
    background-color: #fee2e2 !important;
    color: #991b1b !important;
    border: 1px solid #f87171 !important;
  }

  .badge-warning {
    background-color: #fef3c7 !important;
    color: #92400e !important;
    border: 1px solid #fcd34d !important;
  }

  .badge-success {
    background-color: #d1fae5 !important;
    color: #065f46 !important;
    border: 1px solid #34d399 !important;
  }

  .badge-info {
    background-color: #e0f2fe !important;
    color: #075985 !important;
    border: 1px solid #38bdf8 !important;
  }

  /* 9. 5-Why Tree & Fishbone Print Styling */
  .why-tree {
    background-color: #f8fafc !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 4px !important;
    padding: 10pt !important;
    margin-bottom: 12pt !important;
  }

  .why-node {
    padding: 5pt 8pt !important;
    margin-bottom: 6pt !important;
    background-color: #ffffff !important;
    border-left: 3px solid #2563eb !important;
    border-radius: 0 3px 3px 0 !important;
    font-size: 8.5pt !important;
    box-shadow: none !important;
    border-top: 1px solid #f1f5f9 !important;
    border-right: 1px solid #f1f5f9 !important;
    border-bottom: 1px solid #f1f5f9 !important;
  }

  .why-node.root-cause {
    border-left-color: #dc2626 !important;
    background-color: #fef2f2 !important;
    font-weight: 700 !important;
  }

  .why-node.unsubstantiated {
    border-left-color: #d97706 !important;
    background-color: #fffbeb !important;
  }

  /* 10. D8 Sign-Off Block & Signature Lines */
  .signoff-card {
    border: 2px solid #059669 !important;
    border-radius: 4px !important;
    padding: 12pt !important;
    background-color: #f0fdf4 !important;
    margin-top: 16pt !important;
    page-break-inside: avoid !important;
  }

  .signoff-grid {
    display: grid !important;
    grid-template-columns: 2fr 1fr 1fr !important;
    gap: 10pt !important;
    font-size: 8.5pt !important;
    margin-top: 8pt !important;
  }

  .signature-row {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 20pt !important;
    margin-top: 24pt !important;
  }

  .sign-line {
    border-top: 1.5px dashed #475569 !important;
    padding-top: 4pt !important;
    font-size: 8pt !important;
    color: #475569 !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
  }

  /* 11. Links & Citations */
  a {
    color: #0f172a !important;
    text-decoration: none !important;
  }
}
```

---

### 4.2 Specification: Export Evidence API Client (`frontend/src/api.js`)

Add export utility functions to `frontend/src/api.js`:

```javascript
// --- RCA & 8D Compliance Export Utilities ---
export async function exportRCAEvidence(reportId, format = 'html', token = null) {
  const url = `${API_URL}/api/v1/rca/export-evidence`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({ report_id: reportId, format })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Export request failed' }));
    throw new Error(errorData.detail || `Export failed with status ${response.status}`);
  }

  return await response.json(); // { content: string, sha256_checksum: string, filename: string }
}

export function downloadBlobFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
```

---

### 4.3 Specification: Export Action UI in `EightDIncidentStudio.jsx`

In `EightDIncidentStudio.jsx`, provide an Export Action Menu with three distinct modes:

```jsx
import React, { useState } from 'react';
import { Printer, Download, FileCode, ShieldCheck, Loader2, ChevronDown } from 'lucide-react';
import { exportRCAEvidence, downloadBlobFile } from '../../api';
import './printStyles.css';

export function ExportAuditPackageButton({ report, token }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  const handlePrint = () => {
    setIsOpen(false);
    window.print();
  };

  const handleDownload = async (format) => {
    setIsOpen(false);
    setIsExporting(true);
    setStatusMsg(`Generating certified ${format.toUpperCase()}...`);
    try {
      const data = await exportRCAEvidence(report.report_id, format, token);
      const mime = format === 'json' ? 'application/json' : 'text/html';
      downloadBlobFile(data.content, data.filename, mime);
      setStatusMsg(`Exported! SHA-256: ${data.sha256_checksum.slice(0, 8)}...`);
      setTimeout(() => setStatusMsg(null), 4000);
    } catch (err) {
      console.error('Export failed:', err);
      // Fallback for offline mode:
      if (format === 'json') {
        downloadBlobFile(JSON.stringify(report, null, 2), `${report.report_id}.json`, 'application/json');
      } else {
        window.print();
      }
      setStatusMsg('API unavailable; used fallback');
      setTimeout(() => setStatusMsg(null), 4000);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="relative inline-block text-left no-print">
      <div className="flex items-center gap-1">
        <button
          onClick={handlePrint}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-l-lg transition-colors shadow-sm"
          title="Print or Save as PDF (ISO 9001/IATF 16949)"
        >
          <Printer className="w-3.5 h-3.5" />
          <span>Export Audit Package</span>
        </button>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="px-2 py-1.5 text-xs font-bold text-white bg-indigo-700 hover:bg-indigo-600 rounded-r-lg transition-colors border-l border-indigo-500"
          title="Export options"
        >
          <ChevronDown className="w-3.5 h-3.5" />
        </button>
      </div>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 rounded-xl bg-white shadow-xl border border-slate-200 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-1.5 border-b border-slate-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Compliance Formats</span>
          </div>
          <button
            onClick={handlePrint}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors text-left"
          >
            <Printer className="w-4 h-4 text-indigo-600" />
            <div>
              <div className="font-semibold">Print / Save as PDF</div>
              <div className="text-[10px] text-slate-400">Formatted for ISO 9001:2015 audit package</div>
            </div>
          </button>
          <button
            onClick={() => handleDownload('html')}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors text-left"
          >
            <Download className="w-4 h-4 text-emerald-600" />
            <div>
              <div className="font-semibold">Download Standalone HTML</div>
              <div className="text-[10px] text-slate-400">Self-contained dossier with SHA-256 seal</div>
            </div>
          </button>
          <button
            onClick={() => handleDownload('json')}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors text-left"
          >
            <FileCode className="w-4 h-4 text-amber-600" />
            <div>
              <div className="font-semibold">Download JSON Evidence</div>
              <div className="text-[10px] text-slate-400">Canonical machine-readable format</div>
            </div>
          </button>
        </div>
      )}

      {statusMsg && (
        <span className="ml-2 text-[11px] text-slate-500 font-medium">
          {statusMsg}
        </span>
      )}
    </div>
  );
}
```

---

### 4.4 Specification: `<EightDAuditPrintDossier />` (Complete D1–D8 Print View)

Rendered inside `EightDIncidentStudio.jsx`:
```jsx
{/* Screen View (Interactive Tabs) */}
<div className="no-print flex-1 flex flex-col overflow-hidden">
  <div className="studio-tabs-bar ...">...</div>
  <div className="flex-1 overflow-y-auto">
    {activeTab === 'overview' && <OverviewTab report={report} />}
    {activeTab === '5why' && <FiveWhyFishboneTab report={report} onSourceClick={onSourceClick} />}
    {activeTab === 'timeline' && <TimelineTab report={report} onSourceClick={onSourceClick} />}
    {activeTab === 'actions' && <CorrectiveActionsTab report={report} />}
  </div>
</div>

{/* Print-Only View: Formatted ISO 9001 / IATF 16949 Audit Package */}
<div className="hidden print:block eight-d-print-dossier">
  <EightDAuditPrintDossier report={report} />
</div>
```

The print dossier renders:
1. **Audit Header** with report ID, asset tag, created timestamp, RPN calculation (`S x O x D = RPN`), and SHA-256 seal badge.
2. **D1 Team Formation** table.
3. **D2 Problem Description (5W2H Framework)** table.
4. **Chronological Timeline** table with event types, descriptions, and citation links.
5. **D3 Containment Actions** table with efficacy percentages and statuses.
6. **D4 Root Cause Analysis**: 5-Why Causal Tree (with root cause and unsubstantiated assumption badges) and Ishikawa 6M classification table.
7. **D5 Permanent Corrective Actions** table with target causes and owners.
8. **D6 Validation Plan** table with metrics and validation status.
9. **D7 Preventative Controls**: OEM envelope deviations, SOP updates, PM schedule updates, and Sister Asset read-across alerts.
10. **Citation Evidence Registry** table with citation IDs, source documents, confidence scores, and verbatim excerpts.
11. **D8 Sign-Off & Official Audit Certification**: Authorized signatory, sign-off status, digital seal hash, and dual physical signature lines.

---

## 5. Verification Method

### 5.1 Independent Commands
1. **Frontend Clean Build**:
   ```powershell
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\frontend"
   npm run build
   ```
   *Expected outcome*: Exit code 0, dist/ generated with 0 errors.

2. **Backend Export Evidence Endpoint Verification**:
   ```powershell
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\backend"
   pytest tests/test_rca_api.py -k "export_evidence" -v
   ```
   *Expected outcome*: All export evidence tests pass with 100% success rate.

### 5.2 File Inspection Checklist
- `frontend/src/components/EightDStudio/printStyles.css`: Verify `@page`, `.no-print`, `.page-break`, `.avoid-break`, `.audit-table`, and `.signoff-card` rules.
- `frontend/src/api.js`: Verify `exportRCAEvidence` and `downloadBlobFile` are exported.
- `frontend/src/components/EightDStudio/EightDIncidentStudio.jsx`: Verify inclusion of `ExportAuditPackageButton` and `<EightDAuditPrintDossier />`.

### 5.3 Invalidation Conditions
- If `npm run build` fails with CSS syntax or Vite module resolution errors.
- If `window.print()` outputs a blank page, single-page clipped document, or displays interactive chrome (buttons, sidebars).
- If `POST /api/v1/rca/export-evidence` fails to return `sha256_checksum` or if downloaded HTML is missing ISO 9001 / IATF 16949 audit headers or signature blocks.
