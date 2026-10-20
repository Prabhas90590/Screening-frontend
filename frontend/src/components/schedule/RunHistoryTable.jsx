import React from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { Badge } from '../common/Badge';

export const RunHistoryTable = () => {
  const { runHistory, setActiveNav } = useScreening();

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Succeeded':
        return <Badge variant="teal">Succeeded</Badge>;
      case 'Warnings':
        return <Badge variant="amber">Warnings</Badge>;
      case 'Failed (provider)':
        return <Badge variant="red">Failed (provider)</Badge>;
      default:
        return <Badge variant="gray">{status}</Badge>;
    }
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs space-y-4">
      <h2 className="text-base font-bold text-slate-800">Run history</h2>

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
            {runHistory.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="py-3 px-3 font-mono font-medium text-slate-800">{item.run}</td>
                <td className="py-3 px-3 font-mono text-slate-600">{item.started}</td>
                <td className="py-3 px-3 text-slate-600">{item.rules}</td>
                <td className="py-3 px-3 font-mono text-slate-700">{item.screened.toLocaleString()}</td>
                <td className="py-3 px-3 font-mono text-slate-700">{item.selected}</td>
                <td className="py-3 px-3">{getStatusBadge(item.status)}</td>
                <td className="py-3 px-3 font-mono text-slate-600">{item.duration}</td>
                <td className="py-3 px-3 text-right">
                  <button
                    onClick={() => setActiveNav('results')}
                    className="px-3 py-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded shadow-2xs transition-colors"
                  >
                    Open
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

