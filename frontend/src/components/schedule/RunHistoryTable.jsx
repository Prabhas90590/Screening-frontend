import React from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { Badge } from '../common/Badge';

export const RunHistoryTable = () => {
  const { runHistory, setActiveNav, setSelectedRunId, loadRunHistory, selectedRunId } = useScreening();

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Running':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-pulse"></span>
            <span>Running</span>
          </span>
        );
      case 'Succeeded':
        return <Badge variant="teal">Succeeded</Badge>;
      case 'Warnings':
        return <Badge variant="amber">Warnings</Badge>;
      case 'Failed':
      case 'Failed (provider)':
        return <Badge variant="red">Failed</Badge>;
      default:
        return <Badge variant="gray">{status}</Badge>;
    }
  };

  const handleOpenRun = (runId) => {
    if (setSelectedRunId) {
      setSelectedRunId(runId);
    }
    setActiveNav('results');
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-800">Run history</h2>
        <button
          type="button"
          onClick={loadRunHistory}
          className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 text-xs font-semibold rounded shadow-2xs transition-colors cursor-pointer"
          title="Reload historical runs from database"
        >
          <span>↻</span>
          <span>Refresh</span>
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <th className="py-2.5 px-3">Run</th>
              <th className="py-2.5 px-3">Started</th>
              <th className="py-2.5 px-3">Rules</th>
              <th className="py-2.5 px-3">Screened</th>
              <th className="py-2.5 px-3">Selected</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Duration</th>
              <th className="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {runHistory.length === 0 ? (
              <tr>
                <td colSpan="8" className="py-8 text-center text-slate-400">
                  No screening executions recorded yet. Select a profile above and click{' '}
                  <span className="font-semibold text-slate-600">"Run now"</span> to execute a screening run.
                </td>
              </tr>
            ) : (
              runHistory.map((item) => {
                const isSelected = item.id === selectedRunId;
                const isRunning = item.status === 'Running';

                return (
                  <tr
                    key={item.id}
                    className={`transition-colors ${
                      isSelected ? 'bg-teal-50/40 hover:bg-teal-50/60' : 'hover:bg-slate-50/70'
                    }`}
                  >
                    <td className="py-3 px-3 font-mono font-medium text-slate-800">
                      <div className="flex items-center space-x-1.5">
                        <span className="truncate max-w-[170px]" title={item.run}>
                          {item.run}
                        </span>
                        {isSelected && !isRunning && (
                          <span className="px-1.5 py-0.2 bg-teal-100 text-teal-800 rounded text-[9px] font-semibold">
                            Viewing
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-600">{item.started}</td>
                    <td className="py-3 px-3 text-slate-600">{item.rules}</td>
                    <td className="py-3 px-3 font-mono text-slate-700">
                      {isRunning ? (
                        <span className="flex items-center space-x-1 text-blue-600 font-semibold">
                          <svg className="animate-spin h-3 w-3 text-blue-600" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span>Evaluating...</span>
                        </span>
                      ) : (
                        typeof item.screened === 'number' ? item.screened.toLocaleString() : item.screened
                      )}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-700">
                      {isRunning ? (
                        <span className="text-slate-400">—</span>
                      ) : (
                        <span className="font-bold text-teal-700">{item.selected}</span>
                      )}
                    </td>
                    <td className="py-3 px-3">{getStatusBadge(item.status)}</td>
                    <td className="py-3 px-3 font-mono text-slate-600">{item.duration}</td>
                    <td className="py-3 px-3 text-right">
                      {isRunning ? (
                        <button
                          disabled
                          className="px-3 py-1 bg-slate-100 text-slate-400 border border-slate-200 text-xs font-semibold rounded cursor-not-allowed"
                        >
                          Running...
                        </button>
                      ) : (
                        <button
                          onClick={() => handleOpenRun(item.id)}
                          className={`px-3 py-1 text-xs font-semibold rounded shadow-2xs transition-colors cursor-pointer ${
                            isSelected
                              ? 'bg-[#146b63] text-white hover:bg-[#0f5750]'
                              : 'bg-white border border-slate-300 hover:bg-slate-50 text-slate-700'
                          }`}
                        >
                          {isSelected ? 'Current' : 'Open'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
