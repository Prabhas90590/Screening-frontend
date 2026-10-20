import React from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { RuleCatalog } from './rulecatalog';
import { LimitsUniverseDiversification } from './Limits-universe-diversification';
import { ProfilesVersionHistory, VersionSaveActions } from './Profiles-version-history';
import { MarketUniverseSelector } from './MarketUniverseSelector';

export const ScreeningRulesView = () => {
  const { rulesTab, setRulesTab } = useScreening();

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4 font-sans text-slate-700">
      <div className="flex flex-wrap gap-x-6 gap-y-2 border-b border-slate-200">
        {[
          ['profiles', 'Profiles & version history'],
          ['configuration', 'Rules & constraints'],
        ].map(([tab, label]) => (
          <button
            key={tab}
            onClick={() => setRulesTab(tab)}
            className={`pb-2.5 text-sm font-semibold tracking-tight transition-colors border-b-2 -mb-[1px] ${
              rulesTab === tab
                ? 'border-[#146b63] text-black'
                : 'border-transparent text-slate-500 hover:text-black'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {(rulesTab === 'catalog' || rulesTab === 'limits' || rulesTab === 'configuration') && (
        <div className="space-y-4">
          <MarketUniverseSelector />
          <RuleCatalog />
          <LimitsUniverseDiversification />
          <div className="border-t border-slate-200 pt-3">
            <VersionSaveActions />
          </div>
        </div>
      )}
      {rulesTab === 'profiles' && <ProfilesVersionHistory />}
    </div>
  );
};
