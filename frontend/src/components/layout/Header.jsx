import React from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { useAuth } from '../../context/AuthContext';

export const Header = () => {
  const {
    activeNav,
    rulesTab,
    selectedProfileName,
  } = useScreening();
  const { user } = useAuth();

  const getPageTitle = () => {
    switch (activeNav) {
      case 'rules':
        if (rulesTab === 'profiles') {
          return 'Profiles & version history';
        }
        return 'Screening Rules · Rules & constraints';
      default:
        return 'Equity Screener';
    }
  };

  return (
    <header className="h-16 bg-[#f3f6f9] px-8 flex items-center justify-between border-b border-slate-200/80 shrink-0">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-serif font-bold text-[#14233c] tracking-tight">
          {getPageTitle()}
        </h1>
      </div>

      {/* Top Right Cluster */}
      <div className="flex items-center space-x-3">
        {/* User Status Badge */}
        {user && (
          <div className="flex items-center space-x-1.5 px-3 py-1 bg-white border border-slate-200 text-xs text-slate-700 font-medium rounded-full shadow-2xs">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span className="font-semibold text-slate-800">{user.full_name || user.email?.split('@')[0]}</span>
          </div>
        )}

        {/* Profile Version Tag */}
        {selectedProfileName && (
          <div className="px-3 py-1 bg-white border border-slate-200 text-xs text-slate-700 font-medium rounded-full shadow-2xs">
            {selectedProfileName}
          </div>
        )}
      </div>
    </header>
  );
};
