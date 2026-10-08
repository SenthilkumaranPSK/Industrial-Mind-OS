import React, { useState } from 'react';
import {
  Wrench,
  Shield,
  CheckCircle2,
  Layers,
  AlertTriangle,
  Sliders,
  History,
  ExternalLink,
  FileText,
  TrendingUp,
  Percent,
  Check,
  Calendar,
  User,
  Activity,
  ArrowRight
} from 'lucide-react';

/**
 * CorrectiveActionsTab.jsx
 * Milestone 4: Corrective Actions & Controls for 8D Incident Studio
 * - Action matrices comparing D3 Containment vs D5 Permanent Corrective Actions vs D7 Preventative Controls
 * - OEM Operating Envelope Deviation bars with percentage excursions & threshold limits
 * - Historical Near-Miss Similarity Match cards with symptom alignment & recurrence risk
 */
export default function CorrectiveActionsTab({ report, onSourceClick, onCitationClick }) {
  const [activeMatrixTab, setActiveMatrixTab] = useState('ALL'); // 'ALL' | 'D3' | 'D5' | 'D7'

  const handleCitation = (citationId) => {
    if (onCitationClick) {
      onCitationClick(citationId);
    } else if (onSourceClick) {
      const cite = report?.citations?.find(c => c.citation_id === citationId);
      onSourceClick({
        source: cite?.source_doc || citationId,
        snippet: cite?.excerpt || `Citation ${citationId} referenced in corrective actions.`,
        title: cite?.title,
        section: cite?.section,
        citation_id: citationId
      });
    }
  };

  const d3Actions = report?.d3_containment || [];
  const d5Actions = report?.d5_permanent_actions || [];
  const d7Controls = report?.d7_preventative_controls || {
    sop_updates: [],
    pm_updates: [],
    oem_deviations: [],
    historical_matches: [],
    horizontal_assets: []
  };

  const oemDeviations = d7Controls.oem_deviations || [];
  const historicalMatches = d7Controls.historical_matches || [];

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      {/* ── SECTION 1: TRI-DISCIPLINE ACTION MATRICES (D3 vs D5 vs D7) ── */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        {/* Header & Filter Controls */}
        <div className="px-6 py-4 bg-slate-800/60 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Wrench className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                Tri-Discipline Action Matrix
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  D3 · D5 · D7
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Interim Containment (D3) vs Permanent Elimination (D5) vs Systemic Prevention (D7)
              </p>
            </div>
          </div>

          {/* Matrix view switcher */}
          <div className="flex items-center bg-slate-800 p-1 rounded-xl border border-slate-700/60 text-xs">
            {['ALL', 'D3', 'D5', 'D7'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveMatrixTab(tab)}
                className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                  activeMatrixTab === tab
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                {tab === 'ALL' ? 'Tri-View' : tab === 'D3' ? 'D3 Containment' : tab === 'D5' ? 'D5 Permanent' : 'D7 Preventative'}
              </button>
            ))}
          </div>
        </div>

        {/* Matrix Grid */}
        <div className="p-6">
          <div className={`grid gap-6 ${
            activeMatrixTab === 'ALL'
              ? 'grid-cols-1 lg:grid-cols-3'
              : 'grid-cols-1'
          }`}>
            
            {/* COLUMN 1: D3 INTERIM CONTAINMENT ACTIONS */}
            {(activeMatrixTab === 'ALL' || activeMatrixTab === 'D3') && (
              <div className="space-y-4 flex flex-col bg-slate-950/40 p-4 rounded-xl border border-slate-800/80">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-bold text-slate-200">D3: Interim Containment</span>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                    Immediate Isolation
                  </span>
                </div>

                <div className="space-y-3.5 flex-1">
                  {d3Actions.length === 0 ? (
                    <p className="text-xs text-slate-500 italic p-3 text-center">No containment actions recorded.</p>
                  ) : (
                    d3Actions.map((act, idx) => (
                      <div
                        key={act.action_id || idx}
                        className="p-3.5 rounded-xl bg-slate-900 border border-slate-800/90 hover:border-slate-700 space-y-2.5 transition-all shadow-md"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-mono font-bold text-amber-400">{act.action_id || `ICA-0${idx + 1}`}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            act.status === 'IMPLEMENTED' || act.status === 'VERIFIED'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}>
                            {act.status || 'IMPLEMENTED'}
                          </span>
                        </div>

                        <p className="text-xs text-slate-200 font-medium leading-relaxed">
                          {act.action}
                        </p>

                        {/* Effectiveness Meter */}
                        {act.effectiveness_pct !== undefined && (
                          <div className="space-y-1 pt-1 border-t border-slate-800/60">
                            <div className="flex justify-between text-[10px] text-slate-400">
                              <span>Verified Effectiveness:</span>
                              <span className="font-bold text-emerald-400 font-mono">{act.effectiveness_pct}%</span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="bg-emerald-500 h-full rounded-full"
                                style={{ width: `${act.effectiveness_pct}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {act.verification_method && (
                          <div className="text-[11px] text-slate-400 bg-slate-950/50 p-2 rounded border border-slate-800/80">
                            <span className="text-[9px] uppercase font-bold text-slate-500 block">Verification Method:</span>
                            {act.verification_method}
                          </div>
                        )}

                        <div className="flex flex-wrap items-center justify-between pt-1 text-[10px] text-slate-400 gap-1">
                          <span className="flex items-center gap-1"><User className="w-3 h-3 text-slate-500" /> {act.owner}</span>
                          {act.citation_ids && act.citation_ids.length > 0 && (
                            <div className="flex items-center gap-1">
                              {act.citation_ids.map(cid => (
                                <button
                                  key={cid}
                                  onClick={() => handleCitation(cid)}
                                  className="text-indigo-400 hover:text-indigo-300 underline font-mono flex items-center gap-0.5"
                                  title="Inspect citation"
                                >
                                  <FileText className="w-2.5 h-2.5" />
                                  {cid}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* COLUMN 2: D5 PERMANENT CORRECTIVE ACTIONS */}
            {(activeMatrixTab === 'ALL' || activeMatrixTab === 'D5') && (
              <div className="space-y-4 flex flex-col bg-slate-950/40 p-4 rounded-xl border border-slate-800/80">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-bold text-slate-200">D5: Permanent Corrective</span>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                    Root Cause Elimination
                  </span>
                </div>

                <div className="space-y-3.5 flex-1">
                  {d5Actions.length === 0 ? (
                    <p className="text-xs text-slate-500 italic p-3 text-center">No permanent corrective actions recorded.</p>
                  ) : (
                    d5Actions.map((pca, idx) => (
                      <div
                        key={pca.pca_id || idx}
                        className="p-3.5 rounded-xl bg-slate-900 border border-slate-800/90 hover:border-slate-700 space-y-2.5 transition-all shadow-md"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-mono font-bold text-emerald-400">{pca.pca_id || `PCA-0${idx + 1}`}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            pca.status === 'IMPLEMENTED'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                          }`}>
                            {pca.status || 'IN_PROGRESS'}
                          </span>
                        </div>

                        <p className="text-xs text-slate-200 font-medium leading-relaxed">
                          {pca.action}
                        </p>

                        {pca.target_cause_id && (
                          <div className="text-[10px] text-slate-400 flex items-center gap-1.5">
                            <span className="text-slate-500 uppercase font-semibold">Target Cause:</span>
                            <span className="font-mono font-bold text-indigo-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                              {pca.target_cause_id}
                            </span>
                          </div>
                        )}

                        {pca.validation_plan && (
                          <div className="text-[11px] text-slate-400 bg-slate-950/50 p-2 rounded border border-slate-800/80">
                            <span className="text-[9px] uppercase font-bold text-slate-500 block">Validation Protocol:</span>
                            {pca.validation_plan}
                          </div>
                        )}

                        <div className="flex flex-wrap items-center justify-between pt-1 text-[10px] text-slate-400 gap-1 border-t border-slate-800/60">
                          <span className="flex items-center gap-1"><User className="w-3 h-3 text-slate-500" /> {pca.owner}</span>
                          <span className="font-mono">{pca.target_date ? new Date(pca.target_date).toLocaleDateString() : 'Target: Q4'}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* COLUMN 3: D7 PREVENTATIVE CONTROLS */}
            {(activeMatrixTab === 'ALL' || activeMatrixTab === 'D7') && (
              <div className="space-y-4 flex flex-col bg-slate-950/40 p-4 rounded-xl border border-slate-800/80">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-purple-400" />
                    <span className="text-xs font-bold text-slate-200">D7: Preventative Controls</span>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30">
                    Systemic Read-Across
                  </span>
                </div>

                <div className="space-y-3.5 flex-1">
                  {/* SOP Updates */}
                  <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800/90 space-y-2 shadow-md">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 block">
                      Standard Operating Procedure Updates
                    </span>
                    <ul className="space-y-1.5 text-xs text-slate-200">
                      {(d7Controls.sop_updates || []).map((sop, idx) => (
                        <li key={idx} className="flex items-start gap-1.5 leading-snug">
                          <Check className="w-3.5 h-3.5 text-purple-400 flex-shrink-0 mt-0.5" />
                          <span>{sop}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Preventative Maintenance Updates */}
                  <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800/90 space-y-2 shadow-md">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400 block">
                      Preventative Maintenance Schedule (PM)
                    </span>
                    <ul className="space-y-1.5 text-xs text-slate-200">
                      {(d7Controls.pm_updates || []).map((pm, idx) => (
                        <li key={idx} className="flex items-start gap-1.5 leading-snug">
                          <Check className="w-3.5 h-3.5 text-sky-400 flex-shrink-0 mt-0.5" />
                          <span>{pm}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Horizontal Sister Asset Read-Across */}
                  {d7Controls.horizontal_assets && d7Controls.horizontal_assets.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800/90 space-y-2 shadow-md">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 block">
                        Horizontal Asset Read-Across Deployed
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {d7Controls.horizontal_assets.map((asset, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                          >
                            {asset}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

          </div>
        </div>
      </div>

      {/* ── SECTION 2: OEM OPERATING ENVELOPE DEVIATION BARS ── */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-4 bg-slate-800/60 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                OEM Operating Envelope Excursion Analysis
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-300 border border-rose-500/20">
                  Telemetry Excursion
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Observed incident telemetry vs manufacturer design boundaries
              </p>
            </div>
          </div>
          <span className="text-xs font-mono font-bold text-rose-300 bg-rose-950/60 px-2.5 py-1 rounded-md border border-rose-800/60">
            {oemDeviations.filter(d => d.is_exceeded).length} Design Limits Exceeded
          </span>
        </div>

        <div className="p-6 space-y-5">
          {oemDeviations.length === 0 ? (
            <p className="text-xs text-slate-500 italic p-4 text-center">No OEM envelope deviations recorded.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {oemDeviations.map((dev, idx) => {
                const isCrit = dev.severity_level === 'CRITICAL' || Math.abs(dev.deviation_percent) > 15;
                const devSign = dev.deviation_percent > 0 ? '+' : '';

                return (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/90 space-y-3 shadow-lg"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white truncate max-w-[200px]" title={dev.parameter_name}>
                        {dev.parameter_name}
                      </span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                        isCrit
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      }`}>
                        {devSign}{dev.deviation_percent}% Excursion
                      </span>
                    </div>

                    {/* Numeric comparison */}
                    <div className="flex items-center justify-between text-xs font-mono pt-1">
                      <div>
                        <span className="text-[10px] text-slate-500 block uppercase">OEM Boundary</span>
                        <span className="text-slate-300 font-bold">{dev.oem_envelope_limit} {dev.unit}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-rose-400 block uppercase">Incident Peak</span>
                        <span className="text-rose-300 font-bold">{dev.actual_incident_value} {dev.unit}</span>
                      </div>
                    </div>

                    {/* Visual Excursion Progress Bar */}
                    <div className="space-y-1">
                      <div className="w-full bg-slate-800 rounded-full h-2.5 relative overflow-hidden border border-slate-700/80">
                        {/* Nominal threshold baseline (70% marks limit) */}
                        <div className="absolute left-0 top-0 bottom-0 bg-emerald-500/60" style={{ width: '70%' }} />
                        {/* Excursion over limit */}
                        <div className="absolute left-[70%] top-0 bottom-0 bg-rose-500 animate-pulse" style={{ width: '30%' }} />
                        {/* 100% OEM limit line marker */}
                        <div className="absolute top-0 bottom-0 left-[70%] w-0.5 bg-white z-10" title="100% OEM Limit" />
                      </div>
                      <div className="flex justify-between text-[9px] text-slate-500 font-mono">
                        <span>0%</span>
                        <span className="text-slate-400">OEM Limit (100%)</span>
                        <span className="text-rose-400">Peak Excursion</span>
                      </div>
                    </div>

                    {/* Recommended action */}
                    {dev.recommended_action && (
                      <div className="text-[11px] text-slate-300 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 leading-snug">
                        <span className="text-[9px] font-bold uppercase text-slate-500 block mb-0.5">Threshold Action:</span>
                        {dev.recommended_action}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── SECTION 3: HISTORICAL NEAR-MISS SIMILARITY MATCHES ── */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-4 bg-slate-800/60 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <History className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                Historical Near-Miss Similarity Matching
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  Institutional Memory
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Cross-referenced against Near-Miss Database (`Near_Miss_Report_2023.txt`)
              </p>
            </div>
          </div>
          <span className="text-xs font-mono font-bold text-sky-300 bg-sky-950/60 px-2.5 py-1 rounded-md border border-sky-800/60">
            {historicalMatches.length} Matches Identified
          </span>
        </div>

        <div className="p-6 space-y-4">
          {historicalMatches.length === 0 ? (
            <p className="text-xs text-slate-500 italic p-4 text-center">No historical near-miss matches found.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {historicalMatches.map((m, idx) => {
                const simPct = Math.round((m.similarity_score || 0.8) * 100);
                const isHighSim = simPct >= 85;

                return (
                  <div
                    key={m.matched_report_id || idx}
                    className="p-5 rounded-xl bg-slate-950/60 border border-slate-800/90 space-y-3.5 shadow-lg flex flex-col justify-between"
                  >
                    <div>
                      {/* Top match header */}
                      <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
                        <span className="font-mono text-xs font-bold text-sky-400">{m.matched_report_id}</span>
                        <div className="flex items-center gap-1.5">
                          <span className={`text-xs font-mono font-black px-2.5 py-0.5 rounded-full ${
                            isHighSim
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          }`}>
                            {simPct}% Similarity
                          </span>
                        </div>
                      </div>

                      {/* Incident Title */}
                      <h4 className="text-sm font-bold text-white mt-2.5 leading-snug">
                        {m.title}
                      </h4>
                      {m.equipment_family && (
                        <p className="text-[11px] text-slate-400 mt-0.5">Family: {m.equipment_family}</p>
                      )}

                      {/* Matching symptoms */}
                      {m.matching_symptoms && m.matching_symptoms.length > 0 && (
                        <div className="mt-3 space-y-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                            Shared Failure Symptoms:
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {m.matching_symptoms.map((sym, sIdx) => (
                              <span
                                key={sIdx}
                                className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800"
                              >
                                {sym}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Preventative Recommendations */}
                      {m.preventative_recommendations && m.preventative_recommendations.length > 0 && (
                        <div className="mt-3 space-y-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                            Historical Recommendations:
                          </span>
                          <ul className="text-xs text-slate-300 space-y-1">
                            {m.preventative_recommendations.map((rec, rIdx) => (
                              <li key={rIdx} className="flex items-start gap-1.5 leading-relaxed">
                                <ArrowRight className="w-3 h-3 text-sky-400 flex-shrink-0 mt-0.5" />
                                <span>{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Recurrence risk warning */}
                      {m.recurring_risk_assessment && (
                        <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 flex items-start gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                          <span>{m.recurring_risk_assessment}</span>
                        </div>
                      )}
                    </div>

                    {/* Drill-down button */}
                    <div className="pt-2 border-t border-slate-800/80 flex justify-end">
                      <button
                        onClick={() => handleCitation(m.matched_report_id)}
                        className="inline-flex items-center gap-1.5 text-xs text-sky-400 hover:text-white px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-colors"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        <span>Inspect Archive Evidence</span>
                        <ExternalLink className="w-3 h-3 opacity-60" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
