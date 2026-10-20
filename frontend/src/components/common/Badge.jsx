import React from 'react';

export const Badge = ({ children, variant = 'default', size = 'sm', className = '' }) => {
  const variantStyles = {
    green: 'bg-emerald-50 text-emerald-700 border border-emerald-200/80',
    amber: 'bg-amber-50 text-amber-700 border border-amber-200/80',
    red: 'bg-rose-50 text-rose-700 border border-rose-200/80',
    teal: 'bg-[#e6f4f2] text-[#0d6e66] border border-[#b2ded9]',
    darkTeal: 'bg-[#146b63] text-white',
    gray: 'bg-slate-100 text-slate-600 border border-slate-200',
    blue: 'bg-sky-50 text-sky-700 border border-sky-200',
    default: 'bg-slate-100 text-slate-700',
  };

  const sizeStyles = {
    xs: 'px-1.5 py-0.5 text-[10px]',
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
  };

  return (
    <span
      className={`inline-flex items-center font-semibold rounded-full tracking-wide ${variantStyles[variant] || variantStyles.default} ${sizeStyles[size] || sizeStyles.sm} ${className}`}
    >
      {children}
    </span>
  );
};

