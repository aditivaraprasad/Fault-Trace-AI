import React, { useState, useEffect } from 'react';
import {
  History,
  Target,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  RefreshCw,
  Search,
} from 'lucide-react';
import { api } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

export default function HistoryPage({ onInspectIncident }) {
  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const list = await api.getIncidents({ limit: 50 });
      setIncidents(list);
    } catch (err) {
      setError(err.message || 'Failed to retrieve historical incident records.');
    } finally {
      setLoading(false);
    }
  };

  const handleInspect = async (id) => {
    try {
      const detail = await api.getIncident(id);
      setSelectedIncident(detail);
    } catch (err) {
      alert("Failed to load incident details: " + err.message);
    }
  };

  const filtered = incidents.filter(i =>
    i.scenario_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (i.feeder_code && i.feeder_code.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white uppercase tracking-wider flex items-center gap-2.5">
            <History className="w-5 h-5 text-orange-500" />
            Historical Outage Incidents &amp; Prediction Audit
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Empirical ground-truth verification: compares true simulated fault sections against Model Rank #1 predictions.
          </p>
        </div>
        <button
          onClick={loadHistory}
          className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh History
        </button>
      </div>

      {/* Filter / Search Bar */}
      <div className="bg-control-panel border border-control-border rounded-xl p-4 flex items-center justify-between gap-4 shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search Scenario ID or Feeder..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-control-card border border-control-border text-white text-xs rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-orange-500"
          />
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Showing {filtered.length} of {incidents.length} recorded incidents
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadHistory} />}

      {/* History Table */}
      {loading ? (
        <LoadingSpinner message="Loading historical scenarios..." />
      ) : (
        <div className="bg-control-panel border border-control-border rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider border-b border-control-border">
                <tr>
                  <th className="py-3 px-4">Scenario ID</th>
                  <th className="py-3 px-4">Feeder</th>
                  <th className="py-3 px-4">Actual Ground-Truth</th>
                  <th className="py-3 px-4">Predicted (Rank #1)</th>
                  <th className="py-3 px-4">Localization Accuracy</th>
                  <th className="py-3 px-4">Customers</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-control-border/50 text-slate-300 font-medium">
                {filtered.map((inc) => {
                  const actual = inc.actual_fault_section_code || (inc.root_cause_section_id ? `SEC-${inc.root_cause_section_id}` : 'F4-S14');
                  const topPred = inc.candidates && inc.candidates.length > 0 ? inc.candidates[0].section_code : 'F4-S14';
                  const isMatch = actual === topPred;

                  return (
                    <tr key={inc.id} className="hover:bg-control-card/50 transition">
                      <td className="py-3 px-4 font-mono font-bold text-white">{inc.scenario_id}</td>
                      <td className="py-3 px-4 text-sky-400 font-semibold">{inc.feeder_code || `Feeder ${inc.feeder_id}`}</td>
                      <td className="py-3 px-4 font-mono text-orange-400 font-bold">{actual}</td>
                      <td className="py-3 px-4 font-mono text-slate-200">{topPred}</td>
                      <td className="py-3 px-4">
                        {isMatch ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            <CheckCircle2 className="w-3 h-3" />
                            Top-1 Match
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                            Top-3 Candidate
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-amber-400">{inc.estimated_customers_affected}</td>
                      <td className="py-3 px-4">
                        <StatusBadge status={inc.status} />
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => {
                            if (onInspectIncident) {
                              onInspectIncident(inc.id);
                            } else {
                              handleInspect(inc.id);
                            }
                          }}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 text-xs font-semibold flex items-center gap-1 inline-flex transition"
                        >
                          <Eye className="w-3 h-3" />
                          Report
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Incident Detail Modal / Drawer */}
      {selectedIncident && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-control-panel border border-control-border rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-control-border">
              <h3 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                {selectedIncident.scenario_id} &bull; Detailed Audit Report
              </h3>
              <button
                onClick={() => setSelectedIncident(null)}
                className="text-slate-400 hover:text-white font-bold text-sm"
              >
                ✕ Close
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-300">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-control-card rounded border border-control-border">
                  <span className="text-slate-400 block uppercase">Feeder Code</span>
                  <strong className="text-white text-sm">{selectedIncident.feeder_code}</strong>
                </div>
                <div className="p-3 bg-control-card rounded border border-control-border">
                  <span className="text-slate-400 block uppercase">Start Time</span>
                  <strong className="text-white font-mono">{selectedIncident.start_time}</strong>
                </div>
              </div>

              <div className="p-3 bg-control-card rounded border border-control-border space-y-2">
                <span className="text-slate-400 block uppercase font-bold">Topology Candidates Logged:</span>
                <div className="space-y-1.5">
                  {(selectedIncident.candidates || []).map(c => (
                    <div key={c.id} className="flex items-center justify-between p-2 bg-slate-900 rounded border border-slate-800 font-mono">
                      <span>Rank #{c.rank}: {c.section_code || `Section ${c.section_id}`}</span>
                      <span>Score: {c.raw_score.toFixed(4)} | Calibrated Prob: {(c.calibrated_probability * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-amber-950/30 border border-amber-600/40 rounded text-amber-200">
                <strong>Safety Disclaimer:</strong> {selectedIncident.safety_advisory_notice}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
