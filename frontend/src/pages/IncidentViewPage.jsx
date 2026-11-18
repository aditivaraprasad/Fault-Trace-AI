import React, { useState, useEffect } from 'react';
import {
  AlertOctagon,
  TrendingUp,
  TrendingDown,
  Layers,
  Zap,
  Building2,
  Users,
  ShieldCheck,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Clock,
  RotateCcw,
} from 'lucide-react';
import {
  BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine
} from 'recharts';
import { api } from '../services/api';
import AdvisoryBanner from '../components/AdvisoryBanner';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

export default function IncidentViewPage({ initialIncidentId, onNavigateToRestoration }) {
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(initialIncidentId || null);
  const [incidentDetail, setIncidentDetail] = useState(null);
  const [explanationData, setExplanationData] = useState(null);
  const [assetData, setAssetData] = useState(null);
  const [restorationData, setRestorationData] = useState(null);
  const [selectedRank, setSelectedRank] = useState(1);

  const [loading, setLoading] = useState(true);
  const [localizing, setLocalizing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadIncidentsList();
  }, []);

  useEffect(() => {
    if (selectedIncidentId) {
      loadIncidentFullData(selectedIncidentId);
    }
  }, [selectedIncidentId]);

  const loadIncidentsList = async () => {
    try {
      const list = await api.getIncidents({ limit: 30 });
      setIncidents(list);
      if (list.length > 0 && !selectedIncidentId) {
        // Prefer Hero scenario or latest incident
        const hero = list.find(i => i.scenario_id.includes('HERO'));
        setSelectedIncidentId(hero ? hero.id : list[0].id);
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch incident directory.');
    }
  };

  const loadIncidentFullData = async (id) => {
    try {
      setLoading(true);
      setError(null);
      // Run localization endpoint to guarantee candidate ranking and SHAP persistence
      const [detail, explanation, assets, restoration] = await Promise.all([
        api.getIncident(id),
        api.getIncidentExplanation(id),
        api.getIncidentAssets(id),
        api.getIncidentRestoration(id),
      ]);
      setIncidentDetail(detail);
      setExplanationData(explanation);
      setAssetData(assets);
      setRestorationData(restoration);
      setSelectedRank(1);
    } catch (err) {
      setError(err.message || 'Failed to retrieve detailed diagnostic models.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunLocalization = async () => {
    if (!selectedIncidentId) return;
    try {
      setLocalizing(true);
      await api.localizeIncident(selectedIncidentId);
      await loadIncidentFullData(selectedIncidentId);
    } catch (err) {
      setError(err.message || 'Localization execution failed.');
    } finally {
      setLocalizing(false);
    }
  };

  if (loading && !incidentDetail) return <LoadingSpinner message="Calculating Tree SHAP attributions..." fullPage />;

  const candidates = explanationData?.candidates || [];
  const activeCandidate = candidates.find(c => c.rank === selectedRank) || candidates[0];

  // Prepare SHAP Bar Chart Data for Active Candidate
  const shapChartData = [];
  if (activeCandidate) {
    const pos = (activeCandidate.top_positive_features || []).map(f => ({
      feature: f.feature,
      shap: f.shap_contribution,
      impact: 'Increases Risk',
      color: '#EA580C',
    }));
    const neg = (activeCandidate.top_negative_features || []).map(f => ({
      feature: f.feature,
      shap: f.shap_contribution,
      impact: 'Decreases Risk',
      color: '#0284C7',
    }));
    shapChartData.push(...pos, ...neg);
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Advisory Banner */}
      <AdvisoryBanner />

      {/* Incident Switcher Bar */}
      <div className="bg-control-panel border border-control-border rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <AlertOctagon className="w-5 h-5 text-orange-500" />
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Incident Diagnostics &amp; Explainability
            </h2>
            <p className="text-xs text-slate-400">
              Scenario: <span className="font-mono text-sky-400">{incidentDetail?.scenario_id}</span> &bull; Feeder: <span className="font-semibold text-white">{incidentDetail?.feeder_code}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedIncidentId || ''}
            onChange={(e) => setSelectedIncidentId(parseInt(e.target.value))}
            className="bg-control-card border border-control-border text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-orange-500 font-medium"
          >
            {incidents.map((inc) => (
              <option key={inc.id} value={inc.id}>
                {inc.scenario_id} ({inc.feeder_code}) - {inc.status}
              </option>
            ))}
          </select>

          <button
            onClick={handleRunLocalization}
            disabled={localizing}
            className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 disabled:bg-slate-700 text-white rounded text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
          >
            {localizing ? 'Localizing...' : 'Re-Run Localization'}
          </button>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={() => loadIncidentFullData(selectedIncidentId)} />}

      {/* Main 2-Column Diagnostic Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (1 col): Ranked Topology Candidates */}
        <div className="bg-control-panel border border-control-border rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-control-border">
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Topology-Consistent Candidates
              </h3>
              <p className="text-[11px] text-slate-400">Pruned NetworkX candidates ranked by XGBoost</p>
            </div>
            <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700 font-mono">
              {candidates.length} Identified
            </span>
          </div>

          <div className="space-y-2.5">
            {candidates.map((cand) => {
              const isSelected = cand.rank === selectedRank;
              return (
                <div
                  key={`cand-${cand.rank}`}
                  onClick={() => setSelectedRank(cand.rank)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-orange-500/10 border-orange-500/50 shadow-md ring-1 ring-orange-500/30'
                      : 'bg-control-card border-control-border hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold ${
                        cand.rank === 1 ? 'bg-orange-600 text-white' : 'bg-slate-800 text-slate-300'
                      }`}>
                        #{cand.rank}
                      </span>
                      <span className="font-mono font-bold text-white text-xs">{cand.section_code}</span>
                    </div>
                    <span className="text-[11px] text-slate-400">{cand.feeder_code}</span>
                  </div>

                  {/* Strictly compliant score vs calibrated probability labels */}
                  <div className="mt-2.5 grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800/80">
                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase">Model Score</span>
                      <strong className="text-white font-mono text-xs">{cand.model_score.toFixed(4)}</strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase">Calibrated Prob.</span>
                      <strong className="text-orange-400 font-mono text-xs">{(cand.calibrated_probability * 100).toFixed(1)}%</strong>
                    </div>
                  </div>

                  <div className="mt-1 text-[10px] text-slate-400 truncate">
                    {cand.probability_label}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column (2 cols): Candidate Detail, SHAP Attributions, Narrative & Assets */}
        <div className="lg:col-span-2 space-y-6">
          {activeCandidate && (
            <>
              {/* Candidate Diagnostic Card */}
              <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-control-border">
                  <div className="flex items-center gap-2.5">
                    <span className="px-2 py-0.5 bg-orange-600 text-white text-xs font-bold rounded">
                      Rank #{activeCandidate.rank}
                    </span>
                    <h3 className="text-base font-mono font-bold text-white">
                      Section {activeCandidate.section_code}
                    </h3>
                    <span className="text-xs bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded">
                      {activeCandidate.candidate_designation}
                    </span>
                  </div>
                  <div className="text-xs text-orange-400 font-bold bg-orange-500/10 border border-orange-500/30 px-2.5 py-1 rounded">
                    Calibrated Probability: {(activeCandidate.calibrated_probability * 100).toFixed(1)}%
                  </div>
                </div>

                {/* Engineering Narrative Panel */}
                <div className="bg-control-card border border-control-border rounded-lg p-3.5 space-y-1.5">
                  <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-orange-400" />
                    Engineering Diagnostic Narrative:
                  </span>
                  <p className="text-xs text-slate-200 leading-relaxed font-medium">
                    {activeCandidate.narrative}
                  </p>
                </div>

                {/* Comparative Explanation for Rank > 1 */}
                {activeCandidate.rank > 1 && activeCandidate.comparative_rank_reason && (
                  <div className="bg-slate-900/90 border border-slate-700/80 rounded-lg p-3 text-xs space-y-1">
                    <span className="text-[10px] font-bold text-sky-400 uppercase tracking-wider">
                      Comparative Analysis (Why Ranked Below #1):
                    </span>
                    <p className="text-slate-300 text-xs italic">
                      {activeCandidate.comparative_rank_reason}
                    </p>
                  </div>
                )}

                {/* SHAP Attribution Waterfall / Bar Chart */}
                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Tree SHAP Feature Attribution Analysis
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Contributions relative to base expected value
                    </span>
                  </div>
                  <div className="h-56 bg-control-card/50 border border-control-border rounded-lg p-3">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart layout="vertical" data={shapChartData} margin={{ left: 80, right: 20, top: 10, bottom: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" horizontal={false} />
                        <XAxis type="number" stroke="#64748B" fontSize={10} />
                        <YAxis dataKey="feature" type="category" stroke="#94A3B8" fontSize={10} width={120} tickLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                        />
                        <ReferenceLine x={0} stroke="#475569" strokeWidth={1.5} />
                        <Bar dataKey="shap" radius={[0, 4, 4, 0]}>
                          {shapChartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Affected Assets & Critical Facility Card */}
              {assetData && (
                <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-2 border-b border-control-border">
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Downstream Affected Assets &amp; Grid Impact
                    </h3>
                    <StatusBadge status={assetData.severity_level} />
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="bg-control-card p-3 rounded-lg border border-control-border">
                      <span className="text-slate-400 text-[10px] uppercase block">Customers Affected</span>
                      <strong className="text-white text-base font-bold">{assetData.estimated_consumers_affected}</strong>
                    </div>
                    <div className="bg-control-card p-3 rounded-lg border border-control-border">
                      <span className="text-slate-400 text-[10px] uppercase block">Interrupted Load</span>
                      <strong className="text-amber-400 text-base font-bold">{assetData.total_interrupted_kva} kVA</strong>
                    </div>
                    <div className="bg-control-card p-3 rounded-lg border border-control-border">
                      <span className="text-slate-400 text-[10px] uppercase block">Offline Transformers</span>
                      <strong className="text-sky-400 text-base font-bold">{assetData.total_downstream_dts_count} DTs</strong>
                    </div>
                    <div className="bg-control-card p-3 rounded-lg border border-control-border">
                      <span className="text-slate-400 text-[10px] uppercase block">Est. Repair Duration</span>
                      <strong className="text-rose-400 text-base font-bold">{assetData.estimated_duration_minutes} Mins</strong>
                    </div>
                  </div>

                  {/* Critical Facility Callout */}
                  {assetData.critical_facilities?.length > 0 && (
                    <div className="bg-rose-950/30 border border-rose-500/40 rounded-lg p-3 text-xs flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className="text-lg">🚨</span>
                        <div>
                          <strong className="text-rose-300 font-bold">
                            Critical Load De-Energized: {assetData.critical_facilities[0].facility_name}
                          </strong>
                          <p className="text-[11px] text-rose-200">
                            Type: {assetData.critical_facilities[0].facility_type} &bull; Priority Tier: {assetData.critical_facilities[0].priority_tier}
                          </p>
                        </div>
                      </div>
                      <span className="text-[10px] font-bold uppercase bg-rose-500/20 text-rose-300 px-2 py-1 rounded border border-rose-500/30">
                        Priority Dispatch
                      </span>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
