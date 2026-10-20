import React from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export const AppLayout = ({ children }) => {
  const { activeNav } = useScreening();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#f3f6f9]">
      <Sidebar />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {activeNav !== 'rules' && activeNav !== 'results' && activeNav !== 'schedule' && <Header />}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
