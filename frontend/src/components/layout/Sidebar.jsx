import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const Sidebar = () => {
  const { activeNav, setActiveNav } = useScreening();

  const navItems = [
    { id: 'rules', label: 'Screening Rules' },
    { id: 'results', label: 'Results' },
    { id: 'schedule', label: 'Schedule' },
  ];

  return (
    <aside className="w-[173px] bg-[#0d1c31] text-slate-300 flex flex-col h-screen select-none shrink-0 font-sans border-r border-[#718098]">
      {/* Brand Header */}
      <div className="pt-4 px-4 pb-0 flex items-center space-x-2">
        {/* Solid Gold Rounded Logo Mark */}
        <div className="w-[20px] h-[21px] rounded-[5px] bg-[#e5a420] shrink-0" />
        <div className="leading-[1.08]">
          <div className="text-white text-[14px] font-serif font-bold tracking-tight">Portfolio</div>
          <div className="text-white text-[14px] font-serif font-bold tracking-tight">Research</div>
        </div>
      </div>

      {/* Nav Section Header */}
      <div className="px-4 pt-7 pb-1">
        <span className="text-[9px] font-bold tracking-[0.12em] text-[#5b7495] uppercase">
          Equity Screener
        </span>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 space-y-0.5">
        {navItems.map((item) => {
          const isActive = activeNav === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveNav(item.id)}
              className={`w-full flex items-center px-4 py-2 text-[12px] text-left transition-colors relative ${
                isActive
                  ? 'bg-[#1b3153] text-white font-bold border-l-2 border-[#e5a420]'
                  : 'text-[#91a3bc] hover:text-white hover:bg-[#122641] font-medium border-l-2 border-transparent'
              }`}
            >
              {/* Square marker: Solid gold when active, solid steel-blue when inactive */}
              <span
                className={`w-2 h-2 mr-2 shrink-0 rounded-[1px] transition-colors ${
                  isActive ? 'bg-[#e5a420]' : 'bg-[#365275]'
                }`}
              />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer: User status */}
      <div className="px-4 pb-4 pt-4 text-[10px] text-[#7186a2] flex items-center space-x-2 mt-auto">
        <span className="w-2 h-2 bg-[#365275] rounded-[1px] inline-block shrink-0" />
        <span className="font-normal">Signed in as PM</span>
      </div>
    </aside>
  );
};
