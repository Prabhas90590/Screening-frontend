import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const Header = () => {
  const {
    activeNav,
    rulesTab,
    selectedProfileName,
  } = useScreening();

  const getPageTitle = () => {
    switch (activeNav) {
    
      
      case 'rules':
        if (rulesTab === 'profiles') {
          return 'Profiles & version history';
        }
        return 'Screening Rules · Rules & constraints';
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
        {/* Sample Data Pill */}
        

        {/* Profile Version Tag */}
        <div className="px-3 py-1 bg-white border border-slate-200 text-xs text-slate-700 font-medium rounded-full shadow-2xs">
          {selectedProfileName}
        </div>

        

      </div>
    </header>
  );
};
