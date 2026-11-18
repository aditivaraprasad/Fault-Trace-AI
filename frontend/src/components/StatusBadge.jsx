import React from 'react';

const STATUS_CONFIGS = {
  // Incident Status
  INVESTIGATING: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30', dot: 'bg-amber-400' },
  CONFIRMED: { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-400' },
  RESTORING: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30', dot: 'bg-blue-400' },
  RESOLVED: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },

  // Severity
  CRITICAL: { bg: 'bg-red-600/20', text: 'text-red-400', border: 'border-red-600/50', dot: 'bg-red-500 animate-pulse' },
  HIGH: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/40', dot: 'bg-orange-400' },
  MEDIUM: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30', dot: 'bg-amber-400' },
  LOW: { bg: 'bg-slate-500/15', text: 'text-slate-400', border: 'border-slate-500/30', dot: 'bg-slate-400' },

  // Health / Rating
  GOOD: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  FAIR: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30', dot: 'bg-amber-400' },
  POOR: { bg: 'bg-rose-500/20', text: 'text-rose-400', border: 'border-rose-500/40', dot: 'bg-rose-400' },

  // Grid Section Status
  ENERGIZED: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  DE_ENERGIZED: { bg: 'bg-rose-500/20', text: 'text-rose-400', border: 'border-rose-500/40', dot: 'bg-rose-400' },
  ISOLATED: { bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30', dot: 'bg-purple-400' },
};

export default function StatusBadge({ status, className = "" }) {
  const norm = String(status || 'LOW').toUpperCase();
  const config = STATUS_CONFIGS[norm] || STATUS_CONFIGS.LOW;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${config.bg} ${config.text} ${config.border} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {norm}
    </span>
  );
}
