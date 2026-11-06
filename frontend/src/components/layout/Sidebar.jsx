import React from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { useAuth } from '../../context/AuthContext';
import { LogOut } from 'lucide-react';

function getInitials(nameOrEmail) {
  if (!nameOrEmail) return 'A';
  const clean = nameOrEmail.trim();
  if (clean.includes(' ')) {
    const parts = clean.split(' ').filter(Boolean);
    return (parts[0][0] + (parts[1] ? parts[1][0] : '')).toUpperCase();
  }
  return clean.substring(0, 2).toUpperCase();
}

export const Sidebar = () => {
  const { activeNav, setActiveNav } = useScreening();
  const { user, logout } = useAuth();

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
        <div className="w-[22px] h-[22px] rounded-[5px] bg-[#e5a420] shrink-0 flex items-center justify-center text-[#0d1c31] font-bold text-[11px] shadow-xs">Z</div>
        <div className="leading-[1.08]">
          <div className="text-white text-[13px] font-bold tracking-tight">Zenius</div>
          <div className="text-[#e5a420] text-[13px] font-bold tracking-tight">ScreenPro</div>
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

      {/* Footer: User Profile Widget & Logout (Phase 8) */}
      <div className="p-3 border-t border-[#1b3153] mt-auto bg-[#0a1626]">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 min-w-0">
            {/* Initials Avatar */}
            <div className="w-6 h-6 rounded-full bg-[#1b3153] border border-[#e5a420]/40 flex items-center justify-center text-[10px] font-bold text-[#e5a420] shrink-0">
              {getInitials(user?.full_name || user?.email)}
            </div>
            {/* User details */}
            <div className="truncate">
              <div className="text-[11px] font-semibold text-white truncate" title={user?.full_name || user?.email}>
                {user?.full_name || user?.email?.split('@')[0] || 'Analyst'}
              </div>
              <div className="text-[9px] text-[#7186a2] truncate" title={user?.email}>
                {user?.email || 'analyst@portal'}
              </div>
            </div>
          </div>

          {/* Logout Button */}
          <button
            type="button"
            onClick={() => logout()}
            title="Log Out of Session"
            className="p-1 rounded text-[#7186a2] hover:text-rose-400 hover:bg-rose-500/10 transition cursor-pointer shrink-0 ml-1"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
};
