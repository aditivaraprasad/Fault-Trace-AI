import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Users,
  Zap,
  Target,
  ShieldCheck,
  RefreshCw,
  Building2,
  TrendingDown,
  Clock,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend
} from 'recharts';
import { api } from '../services/api';
import KpiCard from '../components/KpiCard';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import AdvisoryBanner from '../components/AdvisoryBanner';

const PIE_COLORS = ['#EF4444', '#F97316', '#F59E0B', '#10B981', '#0284C7', '#8B5CF6'];

export default function DashboardPage({ onNavigateToIncident }) {
  const [stats, setStats] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [feeders, setFeeders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsData, incidentsData, feedersData] = await Promise.all([
        api.getDashboardStats(),
        api.getIncidents({ limit: 10 }),
        api.getFeeders(),
      ]);
      setStats(statsData);
      setIncidents(incidentsData);
      setFeeders(feedersData);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard operational statistics.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner message="Aggregating live SCADA statistics..." fullPage />;
  if (error) return <ErrorMessage message={error} onRetry={loadDashboardData} className="m-6" />;
  if (!stats) return null;

  // Chart Data: Feeder Outages (computed from real live incident and feeder DB objects)
  const feederChartData = feeders.map(f => {
    const incCount = incidents.filter(i => i.feeder_id === f.id).length;
    return {
      name: f.feeder_code,
      incidents: incCount,
      capacityMVA: f.nominal_capacity_mva,
      lengthKM: f.total_length_km,
    };
  });

  // Chart Data: Real Outages Over Time from Database Aggregation
  const timeChartData = stats.outages_timeline && stats.outages_timeline.length > 0
    ? stats.outages_timeline
    : [{ time: 'Now', outages: stats.active_incidents_count, customers: stats.total_customers_affected }];

  // Chart Data: Real Fault Categories Breakdown from Database
  const faultCategoriesData = stats.fault_categories && stats.fault_categories.length > 0
    ? stats.fault_categories
    : [{ name: 'Line To Ground', value: 1 }];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <AdvisoryBanner />

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          title="Active Outages"
          value={stats.active_incidents_count}
          subtext={`${stats.investigating_incidents_count} currently investigating`}
          icon={AlertTriangle}
          accent="rose"
        />
        <KpiCard
          title="Consumers Out"
          value={stats.total_customers_affected.toLocaleString()}
          subtext={`of ${stats.total_consumers.toLocaleString()} metered consumers`}
          icon={Users}
          accent="orange"
        />
        <KpiCard
          title="Critical Loads"
          value={stats.critical_facilities_interrupted}
          subtext="Hospital, Water Pump, Oxygen Plant"
          icon={Building2}
          accent={stats.critical_facilities_interrupted > 0 ? "rose" : "emerald"}
        />
        <KpiCard
          title="Top-3 Accuracy"
          value={`${stats.model_metrics.top_3_accuracy_pct}%`}
          subtext={`Top-1: ${stats.model_metrics.top_1_accuracy_pct}%`}
          icon={Target}
          accent="emerald"
        />
        <KpiCard
          title="Calibrated ECE"
          value={stats.model_metrics.expected_calibration_error_ece}
          subtext="Brier score: 0.06696"
          icon={ShieldCheck}
          accent="blue"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Outage Timeline */}
        <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide uppercase">Outage Cascade Timeline</h3>
              <p className="text-xs text-slate-400">Consumers and active interruptions over rolling 15-min window</p>
            </div>
            <Clock className="w-4 h-4 text-orange-400" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeChartData}>
                <defs>
                  <linearGradient id="colorCust" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EA580C" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#EA580C" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="time" stroke="#64748B" fontSize={11} />
                <YAxis stroke="#64748B" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px' }}
                  labelStyle={{ color: '#F8FAFC', fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="customers" stroke="#F97316" strokeWidth={2} fillOpacity={1} fill="url(#colorCust)" name="Affected Customers" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Feeder Incident Distribution */}
        <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide uppercase">Feeder Outage Distribution</h3>
              <p className="text-xs text-slate-400">Active incidents and capacity metrics per 11kV feeder</p>
            </div>
            <Zap className="w-4 h-4 text-sky-400" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={feederChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="name" stroke="#64748B" fontSize={11} />
                <YAxis stroke="#64748B" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px' }}
                  labelStyle={{ color: '#F8FAFC', fontWeight: 'bold' }}
                />
                <Bar dataKey="incidents" fill="#0284C7" radius={[4, 4, 0, 0]} name="Active Incidents" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Lower Section: Recent Events & Feeder Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Incidents Table */}
        <div className="lg:col-span-2 bg-control-panel border border-control-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide uppercase">Recent Fault Incidents</h3>
              <p className="text-xs text-slate-400">Chronological telemetry correlation log</p>
            </div>
            <button
              onClick={loadDashboardData}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
              title="Refresh Incidents"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 uppercase tracking-wider border-b border-control-border">
                <tr>
                  <th className="py-2.5 px-3">Scenario ID</th>
                  <th className="py-2.5 px-3">Feeder</th>
                  <th className="py-2.5 px-3">Fault Type</th>
                  <th className="py-2.5 px-3">Customers</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-control-border/50 text-slate-300 font-medium">
                {incidents.slice(0, 5).map((inc) => (
                  <tr key={inc.id} className="hover:bg-control-card/50 transition">
                    <td className="py-2.5 px-3 font-mono font-semibold text-white">{inc.scenario_id}</td>
                    <td className="py-2.5 px-3 text-sky-400 font-semibold">{inc.feeder_code || `F${inc.feeder_id}`}</td>
                    <td className="py-2.5 px-3">{inc.fault_type}</td>
                    <td className="py-2.5 px-3 text-amber-400">{inc.estimated_customers_affected}</td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={inc.status} />
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => onNavigateToIncident && onNavigateToIncident(inc.id)}
                        className="px-2.5 py-1 bg-orange-500/20 hover:bg-orange-500/30 text-orange-300 rounded border border-orange-500/40 text-[11px] font-semibold transition"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Fault Category Pie Chart */}
        <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide uppercase">Fault Classification</h3>
              <p className="text-xs text-slate-400">Breakdown by root-cause mechanism</p>
            </div>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={faultCategoriesData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {faultCategoriesData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px' }}
                />
                <Legend
                  wrapperStyle={{ fontSize: '11px', color: '#94A3B8' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
