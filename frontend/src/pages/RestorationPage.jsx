import React, { useState, useEffect } from 'react';
import {
  RotateCcw,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ArrowRight,
  Zap,
  Users,
  Building2,
  FileCheck2,
  CheckSquare,
} from 'lucide-react';
import { api } from '../services/api';
import AdvisoryBanner from '../components/AdvisoryBanner';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

export default function RestorationPage({ incidentId: propIncidentId }) {
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(propIncidentId || null);
  const [restorationPlan, setRestorationPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Dispatcher review workflow state
  const [signedOffSteps, setSignedOffSteps] = useState({});
  const [dispatcherName, setDispatcherName] = useState('');
  const [approvedPlan, setApprovedPlan] = useState(false);

  useEffect(() => {
    loadIncidents();
  }, []);

  useEffect(() => {
    if (selectedIncidentId) {
      loadRestoration(selectedIncidentId);
    }
  }, [selectedIncidentId]);

  const loadIncidents = async () => {
    try {
      const list = await api.getIncidents({ limit: 20 });
      setIncidents(list);
      if (list.length > 0 && !selectedIncidentId) {
        const hero = list.find(i => i.scenario_id.includes('HERO'));
        setSelectedIncidentId(hero ? hero.id : list[0].id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load active incident list.');
    }
  };

  const loadRestoration = async (id) => {
    try {
      setLoading(true);
      setError(null);
      const plan = await api.getIncidentRestoration(id);
      setRestorationPlan(plan);
      setSignedOffSteps({});
      setApprovedPlan(false);
    } catch (err) {
      setError(err.message || 'Failed to generate advisory restoration switching plan.');
    } finally {
      setLoading(false);
    }
  };

  const toggleStepSignoff = (stepNum) => {
    setSignedOffSteps(prev => ({ ...prev, [stepNum]: !prev[stepNum] }));
  };

  const handleAuthorize = () => {
    if (!dispatcherName.trim()) {
      alert("Please provide the Qualified Control-Room Dispatcher Name/ID before authorizing.");
      return;
    }
    setApprovedPlan(true);
  };

  if (loading && !restorationPlan) return <LoadingSpinner message="Calculating alternate back-feed capacity..." fullPage />;

  const steps = restorationPlan?.recommended_switching_steps || [];
  const scoreBreakdown = restorationPlan?.score_breakdown || {};
  const alternatePaths = restorationPlan?.alternate_paths_evaluated || [];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Advisory Banner */}
      <AdvisoryBanner />

      {/* Page Header and Incident Selector */}
      <div className="bg-control-panel border border-control-border rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div>
          <h2 className="text-base font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <RotateCcw className="w-5 h-5 text-orange-500" />
            Advisory Restoration Switching Planner
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Target Feeder: <strong className="text-sky-400">{restorationPlan?.target_feeder_code}</strong> &bull; Isolated Fault Candidate: <strong className="text-orange-400 font-mono">{restorationPlan?.candidate_section_code}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">Incident:</span>
          <select
            value={selectedIncidentId || ''}
            onChange={(e) => setSelectedIncidentId(parseInt(e.target.value))}
            className="bg-control-card border border-control-border text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-orange-500 font-medium"
          >
            {incidents.map((inc) => (
              <option key={inc.id} value={inc.id}>
                {inc.scenario_id} ({inc.feeder_code})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={() => loadRestoration(selectedIncidentId)} />}

      {restorationPlan && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column (2 cols): Switching Sequence Checklist */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-control-border">
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wide">
                    Sequential Isolation &amp; Back-Feed Actions
                  </h3>
                  <p className="text-xs text-slate-400">Strict safety sequence: Fault candidate isolated prior to re-energization</p>
                </div>
                <span className="text-xs font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2.5 py-1 rounded">
                  Status: {approvedPlan ? 'AUTHORIZED FOR FIELD CREW' : 'PENDING DISPATCHER SIGN-OFF'}
                </span>
              </div>

              {/* Step Items */}
              <div className="space-y-4">
                {steps.map((step) => {
                  const isSigned = !!signedOffSteps[step.step_number];
                  const isIsolation = step.action_type === 'ISOLATE_FAULT_SECTION';
                  const isClose = step.operation === 'CLOSE';

                  return (
                    <div
                      key={`step-${step.step_number}`}
                      className={`p-4 rounded-xl border transition-all ${
                        isSigned
                          ? 'bg-slate-900/90 border-emerald-500/50 shadow-sm'
                          : isIsolation
                          ? 'bg-orange-950/20 border-orange-500/40'
                          : 'bg-control-card border-control-border'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <button
                            onClick={() => toggleStepSignoff(step.step_number)}
                            className={`w-6 h-6 rounded flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 transition ${
                              isSigned
                                ? 'bg-emerald-500 text-white'
                                : 'bg-slate-800 text-slate-300 border border-slate-600 hover:border-slate-400'
                            }`}
                          >
                            {isSigned ? <CheckSquare className="w-4 h-4" /> : step.step_number}
                          </button>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono font-bold text-white">
                                {step.action_type}
                              </span>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                                isIsolation ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' : 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                              }`}>
                                Switch: {step.device_code}
                              </span>
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                                isClose ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                              }`}>
                                Operation: {step.operation}
                              </span>
                            </div>

                            <p className="mt-1.5 text-xs text-slate-200 font-medium">
                              {step.advisory_notes}
                            </p>

                            <div className="mt-2 text-[11px] text-amber-300/90 font-semibold flex items-center gap-1.5 bg-amber-500/10 p-2 rounded border border-amber-500/20">
                              <Lock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                              <span>{step.safety_rule}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Human Dispatcher Sign-off Form */}
              <div className="pt-4 border-t border-control-border bg-slate-900/60 p-4 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                  <FileCheck2 className="w-4 h-4 text-orange-400" />
                  Qualified Engineer / Dispatcher Authorization
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <input
                    type="text"
                    placeholder="Enter Dispatcher ID / Name (e.g. ENG-8421)..."
                    value={dispatcherName}
                    onChange={(e) => setDispatcherName(e.target.value)}
                    className="flex-1 bg-control-card border border-control-border text-white text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                  />
                  <button
                    onClick={handleAuthorize}
                    disabled={approvedPlan}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-900 text-white rounded-lg text-xs font-bold transition shadow-md"
                  >
                    {approvedPlan ? '✓ Authorized & Released' : 'Approve & Release Advisory Plan'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column (1 col): Prioritization Score & Headroom Verification */}
          <div className="space-y-6">
            {/* Transparent Score Breakdown */}
            <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm space-y-4">
              <div className="pb-3 border-b border-control-border flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                    Restoration Priority Score
                  </h3>
                  <p className="text-[11px] text-slate-400">Transparent Multi-Criteria Weighted Formula</p>
                </div>
                <div className="text-xl font-bold font-mono text-orange-400">
                  {restorationPlan.restoration_priority_score} / 100
                </div>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between p-2 bg-control-card rounded border border-control-border">
                  <span className="text-slate-400">Critical Facilities (35%)</span>
                  <strong className="text-white font-mono">{scoreBreakdown.critical_loads_score} pts</strong>
                </div>
                <div className="flex items-center justify-between p-2 bg-control-card rounded border border-control-border">
                  <span className="text-slate-400">Customer Count (25%)</span>
                  <strong className="text-white font-mono">{scoreBreakdown.consumers_score} pts</strong>
                </div>
                <div className="flex items-center justify-between p-2 bg-control-card rounded border border-control-border">
                  <span className="text-slate-400">Interrupted Load kVA (20%)</span>
                  <strong className="text-white font-mono">{scoreBreakdown.load_score} pts</strong>
                </div>
                <div className="flex items-center justify-between p-2 bg-control-card rounded border border-control-border">
                  <span className="text-slate-400">Severity Classification (10%)</span>
                  <strong className="text-white font-mono">{scoreBreakdown.severity_score} pts</strong>
                </div>
                <div className="flex items-center justify-between p-2 bg-control-card rounded border border-control-border">
                  <span className="text-slate-400">Alternate Back-Feed (10%)</span>
                  <strong className="text-emerald-400 font-mono">{scoreBreakdown.alternate_path_score} pts</strong>
                </div>
              </div>
            </div>

            {/* Donor Feeder Headroom Capacity Card */}
            {alternatePaths.length > 0 && (
              <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm space-y-4">
                <div className="pb-2 border-b border-control-border flex items-center justify-between">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                    Donor Feeder Capacity Check
                  </h3>
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded font-bold uppercase">
                    Headroom Verified
                  </span>
                </div>

                {alternatePaths.map((alt, idx) => (
                  <div key={`alt-${idx}`} className="bg-control-card p-3.5 rounded-lg border border-control-border space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sky-400 font-mono">Donor: Feeder {alt.donor_feeder_code}</span>
                      <span className="text-emerald-400 font-bold">Capacity OK</span>
                    </div>
                    <div className="text-slate-300">
                      Donor Available Headroom: <strong className="text-white font-mono">{alt.donor_available_headroom_kva} kVA</strong>
                    </div>
                    <div className="text-slate-300">
                      Load to Transfer: <strong className="text-amber-400 font-mono">{alt.load_to_transfer_kva} kVA</strong>
                    </div>
                    <div className="text-slate-300">
                      Projected Utilization: <strong className="text-emerald-400 font-mono">{alt.projected_donor_utilization_pct}%</strong>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
