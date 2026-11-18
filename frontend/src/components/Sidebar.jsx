import React from 'react';
import {
  LayoutDashboard,
  MapPin,
  PlaySquare,
  AlertOctagon,
  Boxes,
  RotateCcw,
  History,
  Cpu,
  ChevronRight,
} from 'lucide-react';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: null },
  { id: 'map', label: 'Network Map', icon: MapPin, badge: 'GIS' },
  { id: 'simulate', label: 'Simulation & Ingestion', icon: PlaySquare, badge: 'Hero' },
  { id: 'incident', label: 'Incident View', icon: AlertOctagon, badge: 'SHAP' },
  { id: 'assets', label: 'Grid Assets', icon: Boxes, badge: null },
  { id: 'restoration', label: 'Restoration Planner', icon: RotateCcw, badge: 'Advisory' },
  { id: 'history', label: 'Incident History', icon: History, badge: null },
  { id: 'model', label: 'ML & Reliability', icon: Cpu, badge: 'ECE' },
];

export default function Sidebar({ activePage, setActivePage }) {
  return (
    <aside className="w-64 bg-control-panel border-r border-control-border flex flex-col shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 border-b border-control-border/60">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Distribution Operations
        </span>
      </div>

      <nav className="p-3 space-y-1 flex-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-orange-500/15 text-orange-400 border border-orange-500/30 shadow-sm'
                  : 'text-slate-300 hover:bg-control-hover hover:text-white border border-transparent'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-orange-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {item.badge && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                      isActive
                        ? 'bg-orange-500/20 text-orange-300'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
                <ChevronRight className={`w-3.5 h-3.5 text-slate-500 ${isActive ? 'opacity-100 text-orange-400' : 'opacity-40'}`} />
              </div>
            </button>
          );
        })}
      </nav>

      {/* Safety Notice in Sidebar Footer */}
      <div className="p-4 border-t border-control-border/60 bg-control-card/40 m-3 rounded-lg">
        <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          Safety Disclaimer
        </div>
        <p className="mt-1 text-[11px] text-slate-400 leading-normal">
          All switching sequences require physical dispatcher authorization and field LOTO verification.
        </p>
      </div>
    </aside>
  );
}
