import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const FunnelPipeline = () => {
  const { funnelState } = useScreening();

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 px-4 py-3 flex flex-wrap items-center justify-between gap-4 text-xs shadow-2xs">
      {/* Funnel Pipeline Stages */}
      <div className="flex items-center space-x-2 text-slate-700 flex-wrap">
        <span className="font-semibold text-slate-400 tracking-wider text-[11px] uppercase mr-1">
          Funnel
        </span>
        <span className="font-bold text-slate-800">{funnelState.universe.toLocaleString()}</span>
        <span className="text-slate-500">Universe</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{funnelState.markets.toLocaleString()}</span>
        <span className="text-slate-500">Markets</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{funnelState.floors.toLocaleString()}</span>
        <span className="text-slate-500">Floors</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{funnelState.gates.toLocaleString()}</span>
        <span className="text-slate-500">Gates</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{funnelState.score.toLocaleString()}</span>
        <span className="text-slate-500">Score</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-slate-800">{funnelState.shortlist.toLocaleString()}</span>
        <span className="text-slate-500">Shortlist</span>
        <span className="text-slate-400">›</span>

        <span className="font-bold text-[#146b63]">{funnelState.selected.toLocaleString()}</span>
        <span className="font-semibold text-[#146b63]">Selected</span>
      </div>

      {/* Delta Since Last Run */}
      <div className="flex items-center space-x-3 text-xs pl-4 border-l border-slate-200">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Since Last Run
        </span>
        <div className="flex items-center space-x-2">
          <span className="flex items-center text-[#146b63] font-semibold">
            <span className="mr-0.5">▲</span> {funnelState.sinceLastRun.entered} entered
          </span>
          <span className="flex items-center text-red-600 font-semibold">
            <span className="mr-0.5">▼</span> {funnelState.sinceLastRun.exited} exited
          </span>
          <span className="text-slate-400">({funnelState.sinceLastRun.notes})</span>
        </div>
      </div>
    </div>
  );
};

