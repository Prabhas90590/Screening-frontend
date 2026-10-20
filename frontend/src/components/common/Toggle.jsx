import React from 'react';

export const Toggle = ({ enabled, onChange, label, className = '' }) => {
  return (
    <label className={`inline-flex items-center cursor-pointer select-none ${className}`}>
      <div className="relative">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />
        <div
          className={`w-9 h-5 rounded-full transition-colors ${
            enabled ? 'bg-[#146b63]' : 'bg-slate-300'
          }`}
        />
        <div
          className={`absolute left-0.5 top-0.5 bg-white w-4 h-4 rounded-full transition-transform shadow-xs ${
            enabled ? 'transform translate-x-4' : ''
          }`}
        />
      </div>
      {label && <span className="ml-2 text-xs text-slate-700 font-medium">{label}</span>}
    </label>
  );
};

