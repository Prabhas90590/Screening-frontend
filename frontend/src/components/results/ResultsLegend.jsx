import React from 'react';

export const ResultsLegend = () => {
  return (
    <div className="flex items-center space-x-6 text-xs pt-4 text-slate-500 font-medium">
      <div className="flex items-center space-x-1.5">
        <span className="font-semibold text-[#146b63]">Green</span>
        <span>meets full-credit level</span>
      </div>
      <div className="flex items-center space-x-1.5">
        <span className="font-semibold text-amber-600">Amber</span>
        <span>meets threshold</span>
      </div>
      <div className="flex items-center space-x-1.5">
        <span className="font-semibold text-red-600">Red</span>
        <span>misses threshold</span>
      </div>
    </div>
  ); 
};

