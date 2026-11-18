import React from 'react';

export default function KpiCard({
  title,
  value,
  subtext,
  icon: Icon,
  accent = "blue",
  trend,
  className = ""
}) {
  const accentColors = {
    orange: 'border-l-orange-500 text-orange-400 bg-orange-500/10',
    blue: 'border-l-sky-500 text-sky-400 bg-sky-500/10',
    emerald: 'border-l-emerald-500 text-emerald-400 bg-emerald-500/10',
    amber: 'border-l-amber-500 text-amber-400 bg-amber-500/10',
    rose: 'border-l-rose-500 text-rose-400 bg-rose-500/10',
  };

  const activeAccent = accentColors[accent] || accentColors.blue;

  return (
    <div className={`bg-control-card border border-control-border rounded-lg p-4 border-l-4 ${activeAccent.split(' ')[0]} shadow-md hover:border-slate-500 transition-all ${className}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">{title}</span>
        {Icon && (
          <div className={`p-2 rounded-md ${activeAccent.split(' ').slice(1).join(' ')}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-white">{value}</span>
        {trend && (
          <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
            {trend}
          </span>
        )}
      </div>
      {subtext && (
        <p className="mt-1 text-xs text-slate-400 truncate font-normal">
          {subtext}
        </p>
      )}
    </div>
  );
}
