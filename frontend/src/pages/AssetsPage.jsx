import React, { useState, useEffect } from 'react';
import {
  Boxes,
  Filter,
  Search,
  RefreshCw,
  AlertTriangle,
  Thermometer,
  Activity,
} from 'lucide-react';
import { api } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

export default function AssetsPage() {
  const [assets, setAssets] = useState([]);
  const [assetType, setAssetType] = useState('');
  const [conditionRating, setConditionRating] = useState('');
  const [searchIdent, setSearchIdent] = useState('');
  const [maxHealth, setMaxHealth] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAssets();
  }, [assetType, conditionRating, maxHealth]);

  const loadAssets = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (assetType) params.asset_type = assetType;
      if (conditionRating) params.condition_rating = conditionRating;
      if (maxHealth) params.max_health_index = maxHealth;
      if (searchIdent) params.identifier = searchIdent;
      params.limit = 100;
      const data = await api.getAssets(params);
      setAssets(data);
    } catch (err) {
      setError(err.message || 'Failed to retrieve asset registry.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadAssets();
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white uppercase tracking-wider flex items-center gap-2.5">
            <Boxes className="w-5 h-5 text-orange-500" />
            Grid Asset Registry &amp; Health Monitoring
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Condition-based health indexing, thermal telemetry, and historical failure records across distribution lines and transformers.
          </p>
        </div>
        <button
          onClick={loadAssets}
          className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Registry
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-control-panel border border-control-border rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-xs">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search Identifier (e.g. F4-S14, DT-14)..."
              value={searchIdent}
              onChange={(e) => setSearchIdent(e.target.value)}
              className="w-full bg-control-card border border-control-border text-white text-xs rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-orange-500"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-semibold transition border border-slate-700"
          >
            Filter
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3">
          {/* Asset Type Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Type:</span>
            <select
              value={assetType}
              onChange={(e) => setAssetType(e.target.value)}
              className="bg-control-card border border-control-border text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-orange-500"
            >
              <option value="">All Types</option>
              <option value="SECTION">Feeder Section</option>
              <option value="TRANSFORMER">Transformer</option>
              <option value="BREAKER">Circuit Breaker</option>
              <option value="CABLE">Underground Cable</option>
            </select>
          </div>

          {/* Condition Rating Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Rating:</span>
            <select
              value={conditionRating}
              onChange={(e) => setConditionRating(e.target.value)}
              className="bg-control-card border border-control-border text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-orange-500"
            >
              <option value="">All Ratings</option>
              <option value="GOOD">Good</option>
              <option value="FAIR">Fair</option>
              <option value="POOR">Poor</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>

          {/* Max Health Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Max Health:</span>
            <select
              value={maxHealth}
              onChange={(e) => setMaxHealth(e.target.value)}
              className="bg-control-card border border-control-border text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-orange-500"
            >
              <option value="">Any</option>
              <option value="70">&le; 70 (Vulnerable)</option>
              <option value="50">&le; 50 (High Risk)</option>
            </select>
          </div>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadAssets} />}

      {/* Assets Table */}
      {loading ? (
        <LoadingSpinner message="Querying asset condition database..." />
      ) : (
        <div className="bg-control-panel border border-control-border rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider border-b border-control-border">
                <tr>
                  <th className="py-3 px-4">Identifier</th>
                  <th className="py-3 px-4">Asset Type</th>
                  <th className="py-3 px-4">Health Index</th>
                  <th className="py-3 px-4">Condition</th>
                  <th className="py-3 px-4">Failures</th>
                  <th className="py-3 px-4">Operating Temp</th>
                  <th className="py-3 px-4">DGA Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-control-border/50 text-slate-300 font-medium">
                {assets.map((asset) => {
                  const h = asset.health_index;
                  const healthColor = h >= 80 ? 'bg-emerald-500' : (h >= 65 ? 'bg-amber-500' : 'bg-rose-500');
                  return (
                    <tr key={asset.id} className="hover:bg-control-card/50 transition">
                      <td className="py-3 px-4 font-mono font-bold text-white">{asset.asset_identifier}</td>
                      <td className="py-3 px-4 text-slate-300">{asset.asset_type}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
                            <div className={`h-full ${healthColor}`} style={{ width: `${Math.min(100, Math.max(0, h))}%` }} />
                          </div>
                          <span className="font-mono font-bold text-white text-[11px]">{h.toFixed(1)}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={asset.condition_rating} />
                      </td>
                      <td className="py-3 px-4">
                        <span className={`font-semibold ${asset.failure_history_count > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                          {asset.failure_history_count}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {asset.operating_temperature_c ? (
                          <span className={asset.operating_temperature_c > 65 ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                            {asset.operating_temperature_c.toFixed(1)}°C
                          </span>
                        ) : (
                          <span className="text-slate-500">N/A</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {asset.dga_status || 'NORMAL'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
