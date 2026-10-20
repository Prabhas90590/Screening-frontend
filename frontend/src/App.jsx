import React from 'react';
import { ScreeningProvider, useScreening } from './context/ScreeningContext';
import { AppLayout } from './components/layout/AppLayout';
import { ResultsView } from './components/results/ResultsView';
import { ScheduleView } from './components/schedule/ScheduleView';
import { ScreeningRulesView } from './components/screening-rules/ScreeningRulesView';

const MainViewRouter = () => {
  const { activeNav } = useScreening();

  switch (activeNav) {
    case 'results':
      return <ResultsView />;
    case 'schedule':
      return <ScheduleView />;
    case 'rules':
      return <ScreeningRulesView />;
    default:
      return <ResultsView />;
  }
};

export default function App() {
  return (
    <ScreeningProvider>
      <AppLayout>
        <MainViewRouter />
      </AppLayout>
    </ScreeningProvider>
  );
}
