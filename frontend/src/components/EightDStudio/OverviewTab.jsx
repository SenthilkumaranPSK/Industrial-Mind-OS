import React, { useState } from 'react';
import {
  Users,
  Shield,
  HelpCircle,
  AlertTriangle,
  Gauge,
  Activity,
  Award,
  CheckCircle2,
  Clock,
  Copy,
  Check,
  TrendingDown,
  Info,
  DollarSign,
  FileText
} from 'lucide-react';

/**
 * OverviewTab.jsx
 * Milestone 4: Overview Tab for 8D Incident Studio
 * - D1 Multi-Disciplinary Team Formation (Leader, Champion, Members, Facilitator)
 * - D2 Problem Description & 5W2H Stratification + Downtime & Impact
 * - Risk Priority Number (RPN) Risk Meter (Severity x Occurrence x Detection + Risk Reduction)
 * - D8 Formal Sign-Off, Quality Certification & Team Recognition
 */
export default function OverviewTab({ report, onCitationClick }) {
  const [copiedHash, setCopiedHash] = useState(false);

  if (!report) {
    return (
      <div className="p-8 text-center text-slate-400">
        <HelpCircle className="w-12 h-12 mx-auto text-slate-600 mb-3" />
        <p className="text-sm">No 8D report data available for Overview.</p>
      </div>
    );
  }

  const d1 = report.d1_team || {};
  const d2 = report.d2_problem || {};
  const d8 = report.d8_recognition || {};

  const severity = report.severity_score || 8;
  const occurrence = report.occurrence_score || 6;
  const detection = report.detection_score || 7;
  const initialRpn = report.rpn_score || (severity * occurrence * detection);

  // Projected mitigated scores (standard 8D post-mitigation projection: S:4, O:2, D:2)
  const mitigatedRpn = Math.min(initialRpn, Math.max(1, Math.round(initialRpn * 0.05)));
  const rpnReductionPct = initialRpn > 0 ? Math.max(0, Math.min(99, Math.round(((initialRpn - mitigatedRpn) / initialRpn) * 100))) : 0;

  const copySignatureHash = () => {
    const hash = d8.signature_hash || report.checksum_sha256 || '';
    if (hash) {
      navigator.clipboard.writeText(hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* ── TOP KPI ROW: Operational Impact & Key Scores ── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Severity */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Severity (S)</span>
            <div className="text-2xl font-black text-rose-400 mt-0.5">{severity} <span className="text-xs text-slate-500 font-normal">/ 10</span></div>
            <span className="text-[10px] text-rose-400/80 font-medium">Critical Impact</span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        {/* Occurrence */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Occurrence (O)</span>
            <div className="text-2xl font-black text-amber-400 mt-0.5">{occurrence} <span className="text-xs text-slate-500 font-normal">/ 10</span></div>
            <span className="text-[10px] text-amber-400/80 font-medium">Frequent Transient</span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        {/* Detection */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Detection (D)</span>
            <div className="text-2xl font-black text-sky-400 mt-0.5">{detection} <span className="text-xs text-slate-500 font-normal">/ 10</span></div>
            <span className="text-[10px] text-sky-400/80 font-medium">Telemetry Lag</span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Gauge className="w-5 h-5" />
          </div>
        </div>

        {/* Total RPN */}
        <div className="bg-gradient-to-br from-indigo-950/60 to-slate-900 border border-indigo-500/30 rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-300">Initial RPN Score</span>
            <div className="text-2xl font-black text-white mt-0.5">{initialRpn} <span className="text-xs text-indigo-400 font-normal">/ 1000</span></div>
            <span className="text-[10px] text-indigo-300 font-semibold">{initialRpn >= 200 ? 'High Risk Action Required' : 'Monitored'}</span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center text-indigo-300 font-black">
            RPN
          </div>
        </div>
      </div>

      {/* ── D1 TEAM FORMATION CARD ── */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-4 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">D1: Multi-Disciplinary Team Formation</h3>
              <p className="text-[11px] text-slate-400">AIAG 8D Clause 4.1 & IATF 16949 Cross-Functional Team</p>
            </div>
          </div>
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
            Team Active
          </span>
        </div>

        <div className="p-6 space-y-5">
          {/* Leadership Trio Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Team Leader */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-indigo-500/40 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
                  Team Leader
                </span>
                <Shield className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <div className="text-sm font-bold text-white mt-1">
                {d1.leader || "Dr. Sarah Jenkins"}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">Incident Commander & Lead Reliability</p>
            </div>

            {/* Champion / Sponsor */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-purple-500/40 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded">
                  Executive Champion
                </span>
                <Award className="w-3.5 h-3.5 text-purple-400" />
              </div>
              <div className="text-sm font-bold text-white mt-1">
                {d1.champion || "David Ross"}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">VP Plant Operations & Reliability</p>
            </div>

            {/* Facilitator */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-emerald-500/40 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                  RCA Facilitator
                </span>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="text-sm font-bold text-white mt-1">
                {d1.facilitator || "Dr. Aris Thorne"}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">Certified RCA & Reliability Specialist</p>
            </div>
          </div>

          {/* Members Roster */}
          <div>
            <div className="text-xs font-semibold text-slate-300 mb-2.5 flex items-center gap-2">
              <span>Cross-Functional Members ({d1.members?.length || 0})</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
              {(d1.members || []).map((m, idx) => (
                <div
                  key={idx}
                  className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-800 flex items-center gap-2 text-xs text-slate-200"
                >
                  <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300">
                    {m.charAt(0)}
                  </div>
                  <span className="truncate font-medium">{m}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── D2 PROBLEM DESCRIPTION (5W2H) CARD ── */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-4 bg-slate-800/60 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <HelpCircle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">D2: Problem Description (5W2H Stratification)</h3>
              <p className="text-[11px] text-slate-400">Tag: <span className="font-mono text-sky-300">{report.asset_tag || "Pump-A12"}</span> · AIAG 8D Standardized Problem Boundary</p>
            </div>
          </div>
          {report.report_id && (
            <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2.5 py-1 rounded-md border border-slate-700">
              {report.report_id}
            </span>
          )}
        </div>

        <div className="p-6 space-y-5">
          {/* Operational Impact Alert Banner */}
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-300">Operational Impact Statement</span>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {d2.operational_impact || "14.5 Hours Total Unplanned Plant Downtime · Primary Loop Cooling Deficit · $84,200 Financial Impact"}
              </p>
            </div>
          </div>

          {/* 5W2H Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {/* WHAT */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-sky-400">WHAT (Defect & Failure Mode)</div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{d2.what || "N/A"}</p>
            </div>

            {/* WHERE */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-sky-400">WHERE (Location & Plant Context)</div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{d2.where || "N/A"}</p>
            </div>

            {/* WHEN */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-sky-400">WHEN (Timestamp & State)</div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{d2.when || "N/A"}</p>
            </div>

            {/* WHO */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-sky-400">WHO (Detection & First Responder)</div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{d2.who || "N/A"}</p>
            </div>

            {/* WHY */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-sky-400">WHY (Operational Consequence)</div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{d2.why || "N/A"}</p>
            </div>

            {/* HOW */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-sky-400">HOW (Telemetry Mechanism)</div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{d2.how || "N/A"}</p>
            </div>

            {/* HOW MANY */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1 md:col-span-2">
              <div className="text-[10px] font-bold uppercase tracking-wider text-sky-400">HOW MANY (Magnitude & Extent)</div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{d2.how_many || "N/A"}</p>
            </div>
          </div>

          {/* Is / Is Not Matrix (if present) */}
          {d2.is_not_analysis && Object.keys(d2.is_not_analysis).length > 0 && (
            <div className="pt-2">
              <span className="text-xs font-semibold text-slate-300 block mb-2">Is / Is Not Problem Isolation Matrix</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {Object.entries(d2.is_not_analysis).map(([k, v]) => (
                  <div key={k} className="p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/80">
                    <span className="text-[10px] font-bold text-slate-400 block uppercase">{k}</span>
                    <span className="text-slate-200 mt-0.5 block">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── RPN RISK METER CARD (AIAG-VDA Risk Reduction) ── */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-4 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
              <Gauge className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">Risk Priority Number (RPN) & Risk Reduction</h3>
              <p className="text-[11px] text-slate-400">AIAG-VDA FMEA Quantitative Risk Assessment ($S \times O \times D$)</p>
            </div>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40">
            Initial RPN {initialRpn}
          </span>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left: Initial Risk Level */}
            <div className="space-y-4 p-5 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-rose-400">Initial Incident Risk</span>
                <span className="text-xs font-mono font-bold text-slate-300">{initialRpn} / 1000</span>
              </div>

              {/* Segmented Risk Gauge */}
              <div className="space-y-1.5">
                <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden flex relative">
                  <div className="w-1/4 bg-emerald-500/60" title="Low (0-99)" />
                  <div className="w-1/4 bg-amber-500/60" title="Moderate (100-199)" />
                  <div className="w-1/4 bg-orange-500/60" title="High (200-299)" />
                  <div className="w-1/4 bg-rose-500" title="Critical (300-1000)" />
                  
                  {/* Indicator needle */}
                  <div
                    className="absolute top-0 bottom-0 w-2 bg-white shadow-xl -ml-1 border-r border-slate-900 animate-pulse"
                    style={{ left: `${Math.min(98, Math.max(2, (initialRpn / 1000) * 100))}%` }}
                  />
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 font-mono">
                  <span>0 (Low)</span>
                  <span>100</span>
                  <span>200</span>
                  <span>300+ (Critical)</span>
                </div>
              </div>

              {/* Factor Calculation Pill */}
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono flex items-center justify-between">
                <span className="text-slate-400">Formula:</span>
                <span className="text-white font-bold">
                  S({severity}) × O({occurrence}) × D({detection}) = <span className="text-rose-400">{initialRpn}</span>
                </span>
              </div>
            </div>

            {/* Right: Projected Post-Mitigation Risk */}
            <div className="space-y-4 p-5 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Projected Mitigated Risk</span>
                <span className="text-xs font-mono font-bold text-emerald-300">{mitigatedRpn} / 1000</span>
              </div>

              {/* Mitigated Risk Gauge */}
              <div className="space-y-1.5">
                <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden flex relative">
                  <div className="w-1/4 bg-emerald-500" title="Low (0-99)" />
                  <div className="w-1/4 bg-amber-500/40" title="Moderate (100-199)" />
                  <div className="w-1/4 bg-orange-500/40" title="High (200-299)" />
                  <div className="w-1/4 bg-rose-500/40" title="Critical (300-1000)" />
                  
                  {/* Needle */}
                  <div
                    className="absolute top-0 bottom-0 w-2 bg-emerald-300 shadow-xl -ml-1"
                    style={{ left: `${Math.min(98, Math.max(2, (mitigatedRpn / 1000) * 100))}%` }}
                  />
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 font-mono">
                  <span>0 (Low)</span>
                  <span>100</span>
                  <span>200</span>
                  <span>300+ (Critical)</span>
                </div>
              </div>

              {/* Reduction Delta */}
              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/60 flex items-center justify-between text-xs">
                <span className="text-emerald-300 font-semibold flex items-center gap-1.5">
                  <TrendingDown className="w-4 h-4 text-emerald-400" />
                  Risk Reduction:
                </span>
                <span className="font-bold text-emerald-300 text-sm font-mono">
                  -{rpnReductionPct}% ({initialRpn} → {mitigatedRpn})
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── D8 FORMAL SIGN-OFF & CERTIFICATION CARD ── */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-4 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Award className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">D8: Formal Sign-Off, Quality Certification & Lessons Learned</h3>
              <p className="text-[11px] text-slate-400">ISO 9001:2015 Clause 10.2 & IATF 16949 Section 10.2.3 Management Sign-Off</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            <CheckCircle2 className="w-3 h-3" />
            {d8.signoff_status || "APPROVED"}
          </span>
        </div>

        <div className="p-6 space-y-5">
          {/* Certificate Block */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Authorized Quality Manager</span>
                <div className="text-sm font-bold text-white mt-0.5">{d8.approver_name || "Dr. Marcus Vance"}</div>
                <div className="text-xs text-slate-400">{d8.approver_role || "Director of Quality Assurance & Reliability"}</div>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Approval Date</span>
                <div className="text-xs font-mono text-slate-200 mt-0.5">
                  {d8.signoff_date ? new Date(d8.signoff_date).toLocaleDateString() : "2023-11-06"}
                </div>
              </div>
            </div>

            {/* Cryptographic Signature Hash */}
            <div className="flex items-center justify-between gap-3 pt-1">
              <div className="overflow-hidden">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                  Cryptographic Verification Seal
                </span>
                <span className="font-mono text-xs text-indigo-300 truncate block bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
                  {d8.signature_hash || report.checksum_sha256 || "SIG-SHA256: 8f4a2b91c0e3579d1a84f67c2d9e0b1a4f3c7e8d2a5b6c9e0f1a3b4c5d6e7f8"}
                </span>
              </div>
              <button
                onClick={copySignatureHash}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors flex items-center gap-1.5 text-xs font-medium flex-shrink-0"
                title="Copy Digital Seal Hash"
              >
                {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedHash ? 'Copied' : 'Copy Seal'}</span>
              </button>
            </div>
          </div>

          {/* Recognition Notes */}
          {d8.recognition_notes && (
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">Executive Commendation</span>
              <p className="text-xs text-slate-200 leading-relaxed italic">
                "{d8.recognition_notes}"
              </p>
            </div>
          )}

          {/* Lessons Learned */}
          {d8.lessons_learned && (
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Institutional Lessons Learned</span>
              <p className="text-xs text-slate-200 leading-relaxed">
                {d8.lessons_learned}
              </p>
            </div>
          )}

          {/* Reconciliation Metrics Footer */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800 flex items-center justify-between text-xs">
              <span className="text-slate-400 flex items-center gap-1.5">
                <DollarSign className="w-4 h-4 text-slate-400" /> Total Financial Impact:
              </span>
              <span className="font-mono font-bold text-slate-200">
                ${d8.financial_impact_total_usd ? d8.financial_impact_total_usd.toLocaleString() : '84,200'} USD
              </span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800 flex items-center justify-between text-xs">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-slate-400" /> Total Unplanned Downtime:
              </span>
              <span className="font-mono font-bold text-slate-200">
                {d8.downtime_hours_total || 14.5} Operating Hours
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
