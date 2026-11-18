import React from 'react';
import { Loader2 } from 'lucide-react';

export default function LoadingSpinner({ message = "Loading grid data...", fullPage = false }) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-3 p-8">
      <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
      <span className="text-sm text-slate-400 font-medium tracking-wide">{message}</span>
    </div>
  );

  if (fullPage) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        {content}
      </div>
    );
  }

  return content;
}
