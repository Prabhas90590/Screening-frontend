import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const FunnelPipeline = () => {
  const { funnelState, setResultsTab } = useScreening();

  const entered = funnelState?.sinceLastRun?.entered || 3;
  const exited = funnelState?.sinceLastRun?.exited || 2;
  const retained = funnelState?.sinceLastRun?.retained || 18;
  const notes = funnelState?.sinceLastRun?.notes || 'Forward P/E tightened, +1 country (India)';

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 px-4 py-3 flex flex-wrap items-center justify-between gap-4 text-xs shadow-2xs">
      {/* Funnel Pipeline Stages */}
      <div className="flex items-center space-x-2 text-slate-700 flex-wrap">
        <span className="font-semibold text-slate-400 tracking-wider text-[11px] uppercase mr-1">
          Funnel
        </span>
        <span className="font-bold text-slate-800">{(funnelState?.universe || 10240).toLocaleString()}</span>
        <span className="text-slate-500">Universe</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{(funnelState?.markets || 4500).toLocaleString()}</span>
        <span className="text-slate-500">Markets</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{(funnelState?.floors || 2200).toLocaleString()}</span>
        <span className="text-slate-500">Floors</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{(funnelState?.gates || 350).toLocaleString()}</span>
        <span className="text-slate-500">Gates</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{(funnelState?.score || 350).toLocaleString()}</span>
        <span className="text-slate-500">Score</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{(funnelState?.shortlist || 50).toLocaleString()}</span>
        <span className="text-slate-500">Shortlist</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-[#147b73]">{(funnelState?.selected || 20).toLocaleString()}</span>
        <span className="font-semibold text-[#147b73]">Selected</span>
      </div>

      {/* Delta Since Last Run with Clickable Shortcuts to Filter */}
      <div className="flex items-center space-x-3 text-xs pl-4 border-l border-slate-200 flex-wrap gap-y-1">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Turnover
        </span>
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setResultsTab && setResultsTab('entered')}
            className="flex items-center text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded text-[11px] font-semibold hover:bg-emerald-100 transition-colors cursor-pointer"
            title="Click to view entered stocks"
          >
            <span className="mr-0.5">▲</span> {entered} entered
          </button>
          <button
            type="button"
            onClick={() => setResultsTab && setResultsTab('exited')}
            className="flex items-center text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded text-[11px] font-semibold hover:bg-rose-100 transition-colors cursor-pointer"
            title="Click to view exited stocks"
          >
            <span className="mr-0.5">▼</span> {exited} exited
          </button>
          <span className="text-slate-500 text-[11px] font-medium hidden sm:inline">
            {retained} retained
          </span>
          <span className="text-slate-400 hidden md:inline">({notes})</span>
        </div>
      </div>
    </div>
  );
};
