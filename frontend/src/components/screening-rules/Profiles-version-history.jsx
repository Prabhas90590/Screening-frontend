import React, { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Pencil, Play, Plus, RotateCcw, Save, Trash2, X } from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';

const conditions = ['>=', '<=', '=', '<', '>', 'discount', 'sector table'];

export const VersionSaveActions = ({ triggerLabel = 'Save profile', showDiscard = true, showRun = true, addProfile = false }) => {
  const {
    profiles,
    ruleMetrics,
    sectorLimits,
    countries,
    exchanges,
    sectors,
    diversification,
    discardChanges,
    saveAsNewVersion,
    saveConfigurationAsNewVersion,
    draftProfileName,
    setDraftProfileName,
    setRulesTab,
    setEditingVersion,
    editingVersion,
  } = useScreening();
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState(draftProfileName || '');
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');

  const saveVersion = (event) => {
    event.preventDefault();
    if (!name.trim()) {
      setError(`Enter a name for this ${addProfile ? 'profile' : 'version'}.`);
      return;
    }
    if (addProfile) {
      const duplicateProfile = profiles.some(
        (profile) => profile.name.trim().toLowerCase() === name.trim().toLowerCase()
      );
      if (duplicateProfile) {
        setWarning('A profile with this name already exists.');
        return;
      }
      discardChanges();
      setDraftProfileName(name.trim());
      setName(name.trim());
      setError('');
      setWarning('');
      setIsOpen(false);
      setEditingVersion(null);
      setRulesTab('configuration');
      return;
    }
    const result = saveAsNewVersion(name);
    if (!result?.saved) {
      setWarning('No changes were made to any metric or rule in the Rule Catalog. Nothing was saved.');
      return;
    }
    setName('');
    setDraftProfileName('');
    setError('');
    setWarning('');
    setIsOpen(false);
    setRulesTab('profiles');
  };

  const saveEditedVersion = () => {
    const configuration = {
      metrics: ruleMetrics.map((metric) => ({ ...metric })),
      sectorLimits: sectorLimits.map((limit) => ({ ...limit })),
      countries: countries.map((country) => ({ ...country })),
      exchanges: exchanges.map((exchange) => ({ ...exchange })),
      sectors: sectors.map((sector) => ({ ...sector })),
      diversification: { ...diversification },
    };

    const result = saveConfigurationAsNewVersion(
      editingVersion.name,
      configuration,
      editingVersion.profileKey,
      editingVersion.versionNumber
    );
    if (!result?.saved) {
      setWarning('No changes were made to any metric or rule in the Rule Catalog. Nothing was saved.');
      return;
    }
    discardChanges();
    setEditingVersion(null);
    setRulesTab('profiles');
  };

  return (
    <>
      <div className="flex items-center justify-end gap-1.5">
        {editingVersion && !addProfile ? (
          <>
            <button type="button" onClick={() => { setEditingVersion(null); discardChanges(); }} className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"><X size={13} aria-hidden="true" />Cancel edit</button>
            <button type="button" onClick={saveEditedVersion} className="inline-flex items-center gap-1.5 rounded-md bg-[#147b73] px-4 py-2 text-xs font-semibold text-white hover:bg-[#0f675f]"><Save size={13} aria-hidden="true" />Save</button>
          </>
        ) : (
          <>
            {showDiscard && <button type="button" onClick={discardChanges} className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"><RotateCcw size={13} aria-hidden="true" />Discard</button>}
            <button type="button" onClick={() => { setName(draftProfileName || ''); setError(''); setWarning(''); setIsOpen(true); }} className="inline-flex items-center gap-1.5 rounded-md bg-[#147b73] px-4 py-2 text-xs font-semibold text-white hover:bg-[#0f675f]"><Plus size={14} aria-hidden="true" />{triggerLabel}</button>
            {showRun && <button type="button" className="inline-flex items-center gap-1.5 rounded-md bg-[#147b73] px-4 py-2 text-xs font-semibold text-white hover:bg-[#0f675f]"><Play size={13} aria-hidden="true" />Save &amp; run</button>}
          </>
        )}
      </div>
      {isOpen && (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-900/30 p-4">
          <form onSubmit={saveVersion} className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-slate-300 bg-white p-5 shadow-xl">
            <h2 className="text-lg font-semibold text-slate-900">{addProfile ? 'Add profile' : 'Save screening version'}</h2>
            <p className="mt-1 text-xs text-slate-500">{addProfile ? 'Enter a profile name to begin configuring its rules.' : 'Name this version and review the rules that will be stored in Profiles &amp; version history.'}</p>
            <label className="mt-4 block text-xs font-semibold text-slate-700">
              {addProfile ? 'Profile name' : 'Version name'}
              <input autoFocus value={name} onChange={(event) => { setName(event.target.value); setError(''); setWarning(''); }} placeholder="e.g. Core value screen" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-normal outline-none focus:border-[#238c83]" />
            </label>
            {error && <p className="mt-1 text-xs font-semibold text-red-600">{error}</p>}
            {warning && <p className="mt-1 text-xs font-semibold text-amber-700">{warning}</p>}
            {!addProfile && <>
              <h3 className="mt-4 text-xs font-bold uppercase tracking-wider text-slate-500">Metrics preview</h3>
              <div className="mt-2 overflow-hidden rounded-md border border-slate-200">
                <div className="grid grid-cols-[1.4fr_1fr_80px_1fr_60px] gap-2 bg-slate-50 px-3 py-2 text-[10px] font-bold uppercase text-slate-500"><span>Metric</span><span>Category</span><span>Mode</span><span>Condition / value</span><span>Weight</span></div>
                {ruleMetrics.map((metric) => <div key={metric.name} className="grid grid-cols-[1.4fr_1fr_80px_1fr_60px] gap-2 border-t border-slate-100 px-3 py-2 text-xs text-slate-700"><span>{metric.name}</span><span>{metric.category}</span><span>{metric.mode}</span><span>{metric.condition || '—'} {metric.value || ''}</span><span>{metric.weight}</span></div>)}
              </div>
              <p className="mt-3 text-xs text-slate-500">Limits: {sectorLimits.filter((item) => item.limit !== '').length} sector limits, {countries.filter((country) => country.selected).length} countries selected, {exchanges.filter((exchange) => exchange.selected).length} exchanges selected, {Object.values(diversification).filter((value) => value !== '').length} diversification rules.</p>
            </>}
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => { setIsOpen(false); setError(''); setWarning(''); }} className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700"><X size={13} aria-hidden="true" />Cancel</button>
              <button type="submit" className="inline-flex items-center gap-1.5 rounded-md bg-[#147b73] px-4 py-2 text-xs font-semibold text-white">{addProfile ? <><ChevronRight size={13} aria-hidden="true" />Continue to rules</> : <><Save size={13} aria-hidden="true" />Save profile</>}</button>
            </div>
          </form>
        </div>
      )}
    </>
  );
};

export const ProfilesVersionHistory = () => {
  const { profiles, versionHistory, restoreVersion, beginVersionEdit, deleteVersion } = useScreening();
  const [selectedProfileKey, setSelectedProfileKey] = useState(null);
  const [expandedVersionId, setExpandedVersionId] = useState(null);
  const [versionToDelete, setVersionToDelete] = useState(null);

  const profileGroups = useMemo(() => {
    const groups = new Map();
    profiles.forEach((profile) => {
      const current = groups.get(profile.profileKey);
      if (!current || (profile.versionNumber || 0) > (current.versionNumber || 0)) {
        groups.set(profile.profileKey, profile);
      }
    });
    return Array.from(groups.values()).map((profile) => {
      const activeVersion = profiles.find(
        (version) => version.profileKey === profile.profileKey && version.badge === 'Active'
      );
      const activeHistoryVersion = versionHistory.find(
        (version) => version.profileKey === profile.profileKey && version.isCurrent
      );
      const activeVersionNumber = activeVersion?.versionNumber || activeHistoryVersion?.versionNumber;

      return {
        ...profile,
        isActive: Boolean(activeVersion || activeHistoryVersion),
        activeVersionNumber,
      };
    });
  }, [profiles, versionHistory]);

  const activeProfileKey =
    selectedProfileKey || profiles.find((profile) => profile.badge === 'Active')?.profileKey || profileGroups[0]?.profileKey;
  const selectedProfile = profileGroups.find((profile) => profile.profileKey === activeProfileKey);
  const selectedHistory = versionHistory.filter((item) => item.profileKey === activeProfileKey);

  return (
    <>
      <div className="space-y-4">
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold tracking-tight text-black">Profiles</h2>
              <p className="mt-1 text-xs text-slate-500">Select a profile to view only its version history.</p>
            </div>
            <VersionSaveActions triggerLabel="Add profile" showDiscard={false} showRun={false} addProfile />
          </div>
          <div className="mt-3 flex flex-wrap gap-3">
            {profiles.length === 0 ? <EmptyState text="No profiles saved yet. Configure rules and save a new profile." /> : profileGroups.map((profile) => (
              <button
                key={profile.profileKey}
                type="button"
                onClick={() => setSelectedProfileKey(profile.profileKey)}
                className={`min-w-52 rounded-md border p-3 text-left ${
                  profile.profileKey === activeProfileKey
                    ? 'border-[#238c83] bg-[#f1faf8] shadow-sm'
                    : 'border-slate-200 bg-white hover:border-[#9bcfc8]'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-800">{profile.name}</span>
                  <span className="text-[10px] font-bold text-slate-500">Version {profile.versionNumber}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{profile.description}</p>
                <span className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold ${profile.isActive ? 'bg-[#238c83] text-white' : 'bg-slate-100 text-slate-600'}`}>{profile.isActive ? 'Active' : profile.badge}</span>
              </button>
            ))}
          </div>
        </section>
        {selectedProfile && (
          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold tracking-tight text-black">{selectedProfile.name} history</h2>
                <p className="mt-1 text-xs text-slate-500">
                  
                  {selectedProfile.isActive && (
                    <span className="ml-1 font-semibold text-[#147b73]">
                      Active version: Version {selectedProfile.activeVersionNumber}
                    </span>
                  )}
                </p>
              </div>
            </div>
            <div className="mt-3 space-y-2">
            {selectedHistory.length === 0 ? <EmptyState text="No versions saved for this profile." /> : selectedHistory.map((item) => (
              <div key={item.id || `${item.profileKey}-${item.version}`} className={`rounded-md border ${item.isCurrent ? 'border-[#9bcfc8] bg-[#f8fcfb]' : 'border-slate-200 bg-white'}`}>
                <div className="flex flex-wrap items-center gap-2 px-3 py-2">
                  <button
                    type="button"
                    onClick={() => setExpandedVersionId((current) => current === item.id ? null : item.id)}
                    aria-expanded={expandedVersionId === item.id}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left"
                  >
                    {expandedVersionId === item.id ? <ChevronDown size={14} className="shrink-0 text-slate-400" aria-hidden="true" /> : <ChevronRight size={14} className="shrink-0 text-slate-400" aria-hidden="true" />}
                    <span className="text-sm font-semibold text-slate-800">{item.name || selectedProfile.name}</span>
                    <span className="text-xs font-bold text-[#147b73]">v{item.versionNumber}</span>
                    {item.isCurrent && <span className="rounded-full bg-[#e1f0ed] px-2 py-0.5 text-[10px] font-bold text-[#147b73]">Active</span>}
                    <span className="hidden text-[11px] text-slate-400 sm:inline">{item.date} · {item.by}</span>
                  </button>
                  <div className="flex shrink-0 gap-1.5">
                    <button type="button" onClick={() => beginVersionEdit(item.id || item.version)} className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1 text-[10px] font-semibold text-slate-700 hover:bg-slate-50"><Pencil size={11} aria-hidden="true" />Edit</button>
                    <button type="button" onClick={() => restoreVersion(item.id)} className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1 text-[10px] font-semibold text-slate-700 hover:bg-slate-50"><RotateCcw size={11} aria-hidden="true" />Restore</button>
                    <button type="button" onClick={() => setVersionToDelete(item)} className="inline-flex items-center gap-1 rounded border border-red-200 px-2 py-1 text-[10px] font-semibold text-red-700 hover:bg-red-50"><Trash2 size={11} aria-hidden="true" />Delete</button>
                  </div>
                </div>
                {expandedVersionId === item.id && (
                  <div className="border-t border-slate-100 px-3 pb-3 pt-2">
                    <p className="text-[11px] text-slate-500">{item.changeSummary}</p>
                    {item.editedFromVersion && <p className="mt-1 text-[11px] font-semibold text-[#147b73]">Edited from Version {item.editedFromVersion}</p>}
                    {item.changes?.length > 0 && (
                      <div className="mt-2 rounded-md bg-slate-50 px-3 py-2">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Changes from previous version</p>
                        <ul className="mt-1 list-disc pl-4 text-[11px] text-slate-600">{item.changes.map((change) => <li key={change}>{change}</li>)}</ul>
                      </div>
                    )}
                    {item.snapshot && <VersionConfigurationSummary snapshot={item.snapshot} />}
                  </div>
                )}
              </div>
            ))}
            </div>
          </section>
        )}
      </div>
      {versionToDelete && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/30 p-4">
          <div role="dialog" aria-modal="true" aria-labelledby="delete-version-title" className="w-full max-w-md rounded-lg border border-slate-300 bg-white p-5 shadow-xl">
            <h2 id="delete-version-title" className="text-base font-semibold text-slate-900">Delete version?</h2>
            <p className="mt-2 text-sm text-slate-600">
              Delete {versionToDelete.name || selectedProfile?.name} version {versionToDelete.versionNumber}? This action cannot be undone.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setVersionToDelete(null)} className="rounded-md border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">Cancel</button>
              <button
                type="button"
                onClick={() => { deleteVersion(versionToDelete.id || versionToDelete.version); setVersionToDelete(null); }}
                className="inline-flex items-center gap-1.5 rounded-md bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-700"
              >
                <Trash2 size={13} aria-hidden="true" />Delete version
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

const EmptyState = ({ text }) => <p className="rounded-md border border-dashed border-slate-300 p-4 text-xs text-slate-500">{text}</p>;

const VersionConfigurationSummary = ({ snapshot }) => (
  <div className="mt-2 grid grid-cols-1 gap-2 border-t border-slate-100 pt-2 text-[10px] text-slate-600 md:grid-cols-4">
    <div className="min-w-52">
      <p className="font-semibold text-slate-800">Rules assigned</p>
      <div className="mt-1 space-y-1">
        {snapshot.metrics.map((metric) => (
          <p key={metric.name}>
            <span className="font-semibold">{metric.name}</span>
            {' · '}
            {metric.mode || 'Off'}
            {metric.condition && ` · ${metric.condition}`}
            {metric.value !== '' && metric.value !== undefined && ` ${metric.value}`}
            {metric.weight !== '' && metric.weight !== undefined && ` · Weight ${metric.weight}`}
          </p>
        ))}
      </div>
    </div>
    <div>
      <p className="font-semibold text-slate-800">Limits</p>
      <div className="mt-1 space-y-1">
        {snapshot.sectorLimits.map((limit) => (
          <p key={limit.sector}><span className="font-semibold">{limit.sector}:</span> {limit.limit || 'Not set'}{limit.note ? ` · ${limit.note}` : ''}</p>
        ))}
      </div>
    </div>
    <div>
      <p className="font-semibold text-slate-800">Universe</p>
      <p className="mt-1">
        {snapshot.countries.filter((country) => country.selected).map((country) => country.name).join(', ') || 'No countries selected'}
      </p>
    </div>
    <div>
      <p className="font-semibold text-slate-800">Diversification</p>
      <div className="mt-1 space-y-1">
        {Object.entries(snapshot.diversification).map(([key, value]) => (
          <p key={key}><span className="font-semibold">{key}:</span> {value === '' ? 'Not set' : value}</p>
        ))}
      </div>
    </div>
  </div>
);
