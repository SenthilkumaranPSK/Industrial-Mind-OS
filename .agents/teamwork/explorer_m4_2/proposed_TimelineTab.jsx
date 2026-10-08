import React, { useState, useMemo } from 'react';
import {
  Clock,
  Activity,
  AlertTriangle,
  UserCheck,
  Flame,
  Wrench,
  PowerOff,
  ShieldCheck,
  FileText,
  ExternalLink,
  Search,
  Filter,
  ArrowUpDown,
  Tag,
  Gauge,
  Info,
  Calendar,
  Layers,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

/**
 * TimelineTab.jsx
 * Interactive Chronological Timeline Rail for Root Cause Analysis (Milestone 4):
 * 1. Chronological vertical rail of failure events with relative T+ offsets and timestamps.
 * 2. Event type classification & industrial color-coding (TELEMETRY_ALARM, OPERATOR_ACTION,
 *    SYSTEM_FAILURE, MAINTENANCE_LOG, EMERGENCY_SHUTDOWN, etc.).
 * 3. Equipment tag, description, and telemetry excursion value callout meters.
 * 4. Verifiable citation badges wired to onSourceClick(citation) -> SourceViewerModal.
 * 5. Mini horizontal scrubber, search query filtering, and event type filtering.
 */

// Configuration of Event Types
const EVENT_TYPE_CONFIG = {
  SYSTEM_FAILURE: {
    label: 'System Failure',
    icon: Flame,
    color: '#f43f5e', // rose-500
    badgeClass: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    dotClass: 'bg-rose-500 shadow-rose-500/50'
  },
  TELEMETRY_ALARM: {
    label: 'Telemetry Alarm',
    icon: Activity,
    color: '#f59e0b', // amber-500
    badgeClass: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    dotClass: 'bg-amber-500 shadow-amber-500/50'
  },
  THRESHOLD_EXCEEDED: {
    label: 'Threshold Exceeded',
    icon: Gauge,
    color: '#fb923c', // orange-500
    badgeClass: 'bg-orange-500/10 text-orange-300 border-orange-500/30',
    dotClass: 'bg-orange-500 shadow-orange-500/50'
  },
  OPERATOR_ACTION: {
    label: 'Operator Action',
    icon: UserCheck,
    color: '#38bdf8', // sky-400
    badgeClass: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
    dotClass: 'bg-sky-400 shadow-sky-400/50'
  },
  MAINTENANCE_LOG: {
    label: 'Maintenance Log',
    icon: Wrench,
    color: '#10b981', // emerald-500
    badgeClass: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    dotClass: 'bg-emerald-500 shadow-emerald-500/50'
  },
  EMERGENCY_SHUTDOWN: {
    label: 'Emergency Shutdown',
    icon: PowerOff,
    color: '#a855f7', // purple-500
    badgeClass: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    dotClass: 'bg-purple-500 shadow-purple-500/50'
  },
  CONTAINMENT_INITIATED: {
    label: 'Containment Initiated',
    icon: ShieldCheck,
    color: '#14b8a6', // teal-500
    badgeClass: 'bg-teal-500/10 text-teal-300 border-teal-500/30',
    dotClass: 'bg-teal-500 shadow-teal-500/50'
  },
  DEFAULT: {
    label: 'Operational Event',
    icon: Clock,
    color: '#64748b', // slate-500
    badgeClass: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
    dotClass: 'bg-slate-400 shadow-slate-400/50'
  }
};

export default function TimelineTab({ report, onSourceClick }) {
  // --- STATE ---
  const [filterType, setFilterType] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortAscending, setSortAscending] = useState(true);
  const [expandedEvents, setExpandedEvents] = useState({});

  // --- DATA EXTRACTION ---
  const rawTimeline = useMemo(() => {
    return report?.timeline || [];
  }, [report]);

  const citationsList = useMemo(() => {
    return report?.citations || [];
  }, [report]);

  // Helper to resolve citation object
  const resolveCitation = (citationId) => {
    const found = citationsList.find((c) => c.citation_id === citationId);
    if (found) {
      return {
        source: found.source_doc || found.title || citationId,
        snippet: found.excerpt,
        title: found.title,
        section: found.section,
        page_or_line: found.page_or_line,
        confidence: found.confidence,
        citation_id: citationId
      };
    }
    return {
      source: citationId,
      snippet: `Referenced citation ${citationId} in incident timeline.`,
      citation_id: citationId
    };
  };

  // Base timestamp (T0 anchor)
  const anchorTime = useMemo(() => {
    if (!rawTimeline.length) return 0;
    const timestamps = rawTimeline
      .map((e) => new Date(e.timestamp).getTime())
      .filter((t) => !isNaN(t));
    return timestamps.length ? Math.min(...timestamps) : 0;
  }, [rawTimeline]);

  // Format relative T+ time
  const formatOffset = (isoTimestamp) => {
    if (!anchorTime) return '+00:00:00';
    const current = new Date(isoTimestamp).getTime();
    if (isNaN(current)) return '+00:00:00';
    const diffSec = Math.max(0, Math.floor((current - anchorTime) / 1000));
    const hours = Math.floor(diffSec / 3600);
    const minutes = Math.floor((diffSec % 3600) / 60);
    const seconds = diffSec % 60;
    return `T+${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  // Format absolute ISO timestamp
  const formatDateTime = (isoTimestamp) => {
    try {
      const dt = new Date(isoTimestamp);
      return dt.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    } catch {
      return isoTimestamp;
    }
  };

  // Toggle card expansion
  const toggleExpand = (eventId) => {
    setExpandedEvents((prev) => ({
      ...prev,
      [eventId]: !prev[eventId]
    }));
  };

  // --- FILTERED & SORTED EVENTS ---
  const processedEvents = useMemo(() => {
    let list = [...rawTimeline];

    // Filter by type
    if (filterType !== 'ALL') {
      list = list.filter((e) => e.event_type?.toUpperCase() === filterType.toUpperCase());
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (e) =>
          e.description?.toLowerCase().includes(q) ||
          e.equipment_tag?.toLowerCase().includes(q) ||
          e.event_id?.toLowerCase().includes(q) ||
          e.event_type?.toLowerCase().includes(q) ||
          Object.keys(e.parameters || {}).some((k) => k.toLowerCase().includes(q))
      );
    }

    // Sort chronologically
    list.sort((a, b) => {
      const ta = new Date(a.timestamp).getTime() || 0;
      const tb = new Date(b.timestamp).getTime() || 0;
      return sortAscending ? ta - tb : tb - ta;
    });

    return list;
  }, [rawTimeline, filterType, searchQuery, sortAscending]);

  // Statistics
  const stats = useMemo(() => {
    const total = rawTimeline.length;
    const alarms = rawTimeline.filter((e) =>
      ['TELEMETRY_ALARM', 'THRESHOLD_EXCEEDED'].includes(e.event_type)
    ).length;
    const failures = rawTimeline.filter((e) => e.event_type === 'SYSTEM_FAILURE').length;
    const actions = rawTimeline.filter((e) => e.event_type === 'OPERATOR_ACTION').length;
    const ungrounded = rawTimeline.filter((e) => e.is_unsubstantiated || !e.citation_ids?.length).length;
    return { total, alarms, failures, actions, ungrounded };
  }, [rawTimeline]);

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* ── Top Header & Stats Summary ── */}
      <div className="px-6 py-4 bg-slate-900 border-b border-slate-800 flex-shrink-0 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                Incident Chronology & Telemetry Rail
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  ISO 9001 §10.2
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Authoritative sequence of events, sensor excursions, and operator interventions
              </p>
            </div>
          </div>

          {/* Quick Stats Pill Row */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
              <span className="text-slate-400">Total: </span>
              <span className="font-bold text-white font-mono">{stats.total}</span>
            </div>
            <div className="px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs">
              <span className="text-amber-400">Alarms: </span>
              <span className="font-bold text-amber-300 font-mono">{stats.alarms}</span>
            </div>
            <div className="px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs">
              <span className="text-rose-400">Failures: </span>
              <span className="font-bold text-rose-300 font-mono">{stats.failures}</span>
            </div>
            <div className="px-2.5 py-1 rounded-lg bg-sky-500/10 border border-sky-500/30 text-xs">
              <span className="text-sky-400">Actions: </span>
              <span className="font-bold text-sky-300 font-mono">{stats.actions}</span>
            </div>
            {stats.ungrounded > 0 && (
              <div className="px-2.5 py-1 rounded-lg bg-amber-500/20 border border-amber-500/40 text-xs text-amber-300 flex items-center gap-1 font-bold">
                <AlertTriangle className="w-3 h-3 text-amber-400" />
                <span>{stats.ungrounded} Ungrounded</span>
              </div>
            )}
          </div>
        </div>

        {/* ── Filter & Search Controls ── */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/80">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs text-slate-400 flex items-center gap-1 mr-1">
              <Filter className="w-3.5 h-3.5" /> Type:
            </span>
            {[
              { key: 'ALL', label: 'All Events' },
              { key: 'TELEMETRY_ALARM', label: 'Alarms' },
              { key: 'OPERATOR_ACTION', label: 'Actions' },
              { key: 'SYSTEM_FAILURE', label: 'Failures' },
              { key: 'MAINTENANCE_LOG', label: 'Maintenance' }
            ].map((btn) => (
              <button
                key={btn.key}
                onClick={() => setFilterType(btn.key)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  filterType === btn.key
                    ? 'bg-indigo-600 text-white font-bold shadow-sm'
                    : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700/80'
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search events, tags, telemetry..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-56"
              />
            </div>

            {/* Sort Toggle */}
            <button
              onClick={() => setSortAscending(!sortAscending)}
              className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
              title="Toggle Chronological Direction"
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
              <span>{sortAscending ? 'Oldest First' : 'Newest First'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Mini Horizontal Scrubber Rail (Overview) ── */}
      {rawTimeline.length > 0 && (
        <div className="px-6 py-2.5 bg-slate-900/60 border-b border-slate-800/80 flex items-center gap-3 overflow-x-auto flex-shrink-0">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider flex-shrink-0">
            Timeline Rail:
          </span>
          <div className="flex items-center gap-2 flex-1 min-w-[600px] relative py-2">
            <div className="absolute left-0 right-0 top-1/2 h-0.5 bg-slate-800 -translate-y-1/2"></div>
            {rawTimeline.map((evt, idx) => {
              const cfg = EVENT_TYPE_CONFIG[evt.event_type] || EVENT_TYPE_CONFIG.DEFAULT;
              return (
                <div
                  key={evt.event_id || idx}
                  className="group relative flex flex-col items-center cursor-pointer z-10"
                  onClick={() => {
                    const el = document.getElementById(`timeline-event-${evt.event_id}`);
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  }}
                >
                  <div
                    className={`w-3 h-3 rounded-full border-2 border-slate-950 ${cfg.dotClass} group-hover:scale-125 transition-transform`}
                  ></div>
                  <span className="text-[8px] text-slate-500 mt-1 font-mono">
                    {formatOffset(evt.timestamp).split(':')[1]}m
                  </span>
                  {/* Tooltip on Hover */}
                  <div className="absolute bottom-6 hidden group-hover:flex flex-col items-center bg-slate-900 border border-slate-700 text-slate-200 text-[10px] px-2 py-1 rounded-md shadow-xl whitespace-nowrap pointer-events-none">
                    <span className="font-bold">{cfg.label}</span>
                    <span className="text-slate-400">{evt.equipment_tag}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Main Chronological Vertical Rail ── */}
      <div className="flex-1 overflow-y-auto p-6">
        {processedEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Clock className="w-12 h-12 text-slate-700 mb-3" />
            <h4 className="text-sm font-semibold text-slate-400">No Timeline Events Match Filters</h4>
            <p className="text-xs text-slate-500 mt-1">Try resetting the type filter or search query.</p>
          </div>
        ) : (
          <div className="relative max-w-4xl mx-auto">
            {/* Continuous Vertical Spine Line */}
            <div className="absolute left-6 top-4 bottom-4 w-0.5 bg-slate-800"></div>

            {/* Event Cards */}
            <div className="space-y-6">
              {processedEvents.map((evt, index) => {
                const cfg = EVENT_TYPE_CONFIG[evt.event_type] || EVENT_TYPE_CONFIG.DEFAULT;
                const IconComponent = cfg.icon;
                const isExpanded = expandedEvents[evt.event_id];
                const hasParameters = evt.parameters && Object.keys(evt.parameters).length > 0;
                const isUnsubstantiated = evt.is_unsubstantiated || !evt.citation_ids?.length;

                return (
                  <div
                    id={`timeline-event-${evt.event_id}`}
                    key={evt.event_id || index}
                    className="relative pl-14 group"
                  >
                    {/* Node Dot on Spine */}
                    <div
                      className={`absolute left-4 top-4 -translate-x-1/2 w-5 h-5 rounded-full border-4 border-slate-950 flex items-center justify-center ${cfg.dotClass} shadow-lg`}
                    ></div>

                    {/* Event Card Container */}
                    <div className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-2xl p-4 shadow-xl transition-all duration-200">
                      
                      {/* Top Header Row: T+ Offset, Event Type, Equipment Tag, Timestamp */}
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                        <div className="flex items-center gap-2">
                          {/* Relative Offset Pill */}
                          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-slate-800 text-sky-400 border border-slate-700">
                            {formatOffset(evt.timestamp)}
                          </span>

                          {/* Event Type Badge */}
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${cfg.badgeClass}`}
                          >
                            <IconComponent className="w-3 h-3" />
                            {cfg.label}
                          </span>

                          {/* Equipment Tag Badge */}
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-950/60 text-indigo-300 border border-indigo-800/50 text-[10px] font-mono">
                            <Tag className="w-2.5 h-2.5" />
                            {evt.equipment_tag || 'Pump-A12'}
                          </span>
                        </div>

                        {/* Timestamp & Event ID */}
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          <span className="font-mono text-[11px]">
                            {formatDateTime(evt.timestamp)}
                          </span>
                          <span className="text-[10px] text-slate-600 font-mono">
                            #{evt.event_id}
                          </span>
                        </div>
                      </div>

                      {/* Description Narrative */}
                      <div className="py-2.5">
                        <p className="text-sm text-slate-200 font-medium leading-relaxed">
                          {evt.description}
                        </p>
                      </div>

                      {/* Sensor Telemetry Callout & Excursion Bar (if available) */}
                      {hasParameters && (
                        <div className="my-2 p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-2">
                          <div className="flex items-center justify-between text-xs text-slate-400">
                            <span className="font-semibold flex items-center gap-1.5 text-slate-300">
                              <Activity className="w-3.5 h-3.5 text-indigo-400" />
                              Telemetry Telemetry Parameters:
                            </span>
                            {evt.parameters.deviation_pct !== undefined && (
                              <span
                                className={`font-mono font-bold text-xs px-2 py-0.5 rounded ${
                                  evt.parameters.is_exceeded
                                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                }`}
                              >
                                {evt.parameters.deviation_pct > 0 ? '+' : ''}
                                {evt.parameters.deviation_pct}% Deviation
                              </span>
                            )}
                          </div>

                          {/* Parameter Metric Badges */}
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs font-mono">
                            {Object.entries(evt.parameters).map(([key, val]) => {
                              if (typeof val === 'boolean') return null;
                              return (
                                <div
                                  key={key}
                                  className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 flex flex-col"
                                >
                                  <span className="text-[10px] text-slate-500 uppercase truncate">
                                    {key.replace(/_/g, ' ')}
                                  </span>
                                  <span className="text-xs font-bold text-slate-200 mt-0.5 truncate">
                                    {String(val)}
                                  </span>
                                </div>
                              );
                            })}
                          </div>

                          {/* Visual Vibration / Excursion Progress Gauge (Pump-A12 baseline) */}
                          {evt.parameters.vibration_mm_s !== undefined && (
                            <div className="pt-2 border-t border-slate-800/60">
                              <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                                <span>Envelope Nominal: 5.0 mm/s</span>
                                <span className="font-bold text-rose-400">
                                  Actual: {evt.parameters.vibration_mm_s} mm/s (Trip: 5.5 mm/s)
                                </span>
                              </div>
                              <div className="w-full bg-slate-900 rounded-full h-2 relative overflow-hidden border border-slate-800">
                                {/* Safe zone marker */}
                                <div
                                  className="absolute left-0 top-0 bottom-0 bg-emerald-500/50"
                                  style={{ width: '70%' }}
                                ></div>
                                {/* Warning / Trip marker */}
                                <div
                                  className="absolute left-[70%] top-0 bottom-0 bg-amber-500/50"
                                  style={{ width: '15%' }}
                                ></div>
                                {/* Trip Exceeded marker */}
                                <div
                                  className="absolute left-[85%] top-0 bottom-0 bg-rose-500"
                                  style={{ width: '15%' }}
                                ></div>
                                {/* Actual Value Pointer */}
                                <div
                                  className="absolute top-0 bottom-0 w-1 bg-white shadow-lg animate-pulse"
                                  style={{
                                    left: `${Math.min(
                                      98,
                                      Math.max(
                                        5,
                                        (evt.parameters.vibration_mm_s / 6.0) * 100
                                      )
                                    )}%`
                                  }}
                                ></div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Card Footer: Citations, Grounding Verification, Drill-Down */}
                      <div className="flex flex-wrap items-center justify-between pt-2.5 border-t border-slate-800/80 gap-2">
                        {/* Citation Badges */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {evt.citation_ids && evt.citation_ids.length > 0 ? (
                            evt.citation_ids.map((cid) => (
                              <button
                                key={cid}
                                onClick={() => {
                                  if (onSourceClick) onSourceClick(resolveCitation(cid));
                                }}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-950/80 text-indigo-300 hover:bg-indigo-900 hover:text-white border border-indigo-700/60 text-xs font-mono transition-colors"
                                title={`Inspect source document evidence for ${cid}`}
                              >
                                <FileText className="w-3 h-3 text-indigo-400" />
                                {cid}
                                <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                              </button>
                            ))
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-950/60 text-amber-300 border border-amber-800/50 text-xs">
                              <AlertTriangle className="w-3 h-3 text-amber-400" />
                              Ungrounded Event (No Citation Document)
                            </span>
                          )}
                        </div>

                        {/* Details Toggle */}
                        <button
                          onClick={() => toggleExpand(evt.event_id)}
                          className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1"
                        >
                          {isExpanded ? (
                            <>
                              Less <ChevronUp className="w-3 h-3" />
                            </>
                          ) : (
                            <>
                              More Details <ChevronDown className="w-3 h-3" />
                            </>
                          )}
                        </button>
                      </div>

                      {/* Collapsible Extended Raw Payload */}
                      {isExpanded && (
                        <div className="mt-3 p-3 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto animate-in fade-in duration-200">
                          <pre>{JSON.stringify(evt, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
