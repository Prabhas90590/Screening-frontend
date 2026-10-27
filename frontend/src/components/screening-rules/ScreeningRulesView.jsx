import React from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { RuleCatalog } from './rulecatalog';
import { LimitsUniverseDiversification } from './Limits-universe-diversification';
import { ProfilesVersionHistory, VersionSaveActions } from './Profiles-version-history';
import { MarketUniverseSelector } from './MarketUniverseSelector';

export const ScreeningRulesView = () => {
  const { rulesTab, setRulesTab, editingVersion, discardChanges } = useScreening();

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
          {editingVersion ? (
            <div className="flex items-center justify-between rounded-lg border border-[#238c83]/40 bg-[#f1faf8] p-3 shadow-xs">
              <div className="flex items-center gap-2.5">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#147b73] text-white text-xs font-bold">
                  ✎
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-900">
                    Editing Profile: <span className="font-bold text-[#147b73]">{editingVersion.name}</span> (Version {editingVersion.versionNumber})
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Showing rules loaded for this profile. Make adjustments below and click Save or Cancel Edit.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={discardChanges}
                className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel Edit
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50/80 p-3 text-xs text-slate-600">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-slate-600 text-xs font-bold">
                  ℹ
                </span>
                <span>
                  All rules are currently <strong>Off</strong> by default. Click <strong>Edit</strong> on a profile in the Profiles tab to load its configured rules, or customize rules below to create a new profile.
                </span>
              </div>
              <button
                type="button"
                onClick={() => setRulesTab('profiles')}
                className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
              >
                Go to Profiles
              </button>
            </div>
          )}
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
