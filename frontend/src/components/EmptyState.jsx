import React from 'react';
import { Database } from 'lucide-react';

export default function EmptyState({
  title = "No Data Found",
  description = "No records match the active criteria or network partition.",
  actionText,
  onAction,
  icon: Icon = Database,
}) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-control-panel/50 border border-control-border/60 rounded-xl">
      <div className="p-3 bg-slate-800/80 rounded-full text-slate-400 mb-3 border border-slate-700">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-white tracking-wide">{title}</h3>
      <p className="mt-1 text-xs text-slate-400 max-w-sm">{description}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded text-xs font-semibold transition-all shadow-sm"
        >
          {actionText}
        </button>
      )}
    </div>
  );
}
