import React, { useState } from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { Toggle } from '../common/Toggle';

export const ScheduleConfigCard = () => {
  const {
    scheduleConfig,
    updateScheduleConfig,
    triggerRunNow,
    isScreeningRunning,
    profiles,
    activateProfile,
    setActiveNav,
  } = useScreening();

  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [profileError, setProfileError] = useState(false);

  const daysOfWeek = [
    { id: 'mon', label: 'M' },
    { id: 'tue', label: 'T' },
    { id: 'wed', label: 'W' },
    { id: 'thu', label: 'T' },
    { id: 'fri', label: 'F' },
  ];
  const frequencies = ['Daily', 'Weekly', 'Monthly', 'Custom'];

  // Current selected profile
  const selectedProfile =
    profiles.find((p) => p.id === scheduleConfig.selectedProfileId) ||
    profiles.find((p) => scheduleConfig.profile === `${p.name} - Version ${p.versionNumber}`) ||
    null;

  const toggleDay = (day) => {
    const current = scheduleConfig.activeDays || [];
    const updated = current.includes(day)
      ? current.filter((d) => d !== day)
      : [...current, day];
    updateScheduleConfig({ activeDays: updated });
  };

  const handleProfileChange = (event) => {
    const pId = event.target.value;
    if (!pId) {
      updateScheduleConfig({ profile: '', selectedProfileId: '' });
      return;
    }
    const profile = profiles.find((item) => item.id === pId);
    if (!profile) return;

    setProfileError(false);
    activateProfile(profile.id);
    updateScheduleConfig({
      profile: `${profile.name} - Version ${profile.versionNumber}`,
      selectedProfileId: profile.id,
    });
  };

  const toggleTrigger = (key) => {
    updateScheduleConfig({
      notifyTriggers: {
        ...scheduleConfig.notifyTriggers,
        [key]: !scheduleConfig.notifyTriggers[key],
      },
    });
  };

  const handleSave = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2500);
  };

  const handleRunNow = async () => {
    if (!selectedProfile || !selectedProfile.id) {
      setProfileError(true);
      return;
    }

    setProfileError(false);
    try {
      await triggerRunNow(selectedProfile.id);
      // Switch immediately to Results view to display the current run
      setActiveNav('results');
    } catch (err) {
      console.warn('Execution error:', err.message);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-800">Weekly Core screen</h2>
        {isPaused && (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            Schedule Paused
          </span>
        )}
      </div>

      <div className="space-y-4 text-xs">
        {/* Profile */}
        <div className="grid grid-cols-4 items-start gap-4">
          <label className="text-slate-500 font-medium pt-2">Profile</label>
          <div className="col-span-3 space-y-1.5">
            <select
              value={selectedProfile?.id || ''}
              onChange={handleProfileChange}
              className={`w-full bg-white border rounded px-3 py-1.5 text-slate-700 focus:outline-hidden transition-colors ${
                profileError
                  ? 'border-rose-400 bg-rose-50/20 focus:border-rose-500'
                  : 'border-slate-300 focus:border-[#146b63]'
              }`}
            >
              <option value="">-- Select a strategy profile --</option>
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name} - Version {profile.versionNumber} {profile.badge === 'Active' ? '(Active)' : ''}
                </option>
              ))}
            </select>
            {profileError && (
              <p className="text-[11px] font-semibold text-rose-600 flex items-center space-x-1">
                <span>⚠️ Please select a profile before running.</span>
              </p>
            )}
          </div>
        </div>

        {/* Frequency */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-500 font-medium">Frequency</label>
          <div className="col-span-3 flex border border-slate-200 rounded-md overflow-hidden max-w-sm">
            {frequencies.map((freq) => {
              const isActive = scheduleConfig.frequency === freq;
              return (
                <button
                  key={freq}
                  type="button"
                  onClick={() => updateScheduleConfig({ frequency: freq })}
                  className={`flex-1 py-1.5 text-center font-medium transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-[#146b63] text-white font-semibold'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {freq}
                </button>
              );
            })}
          </div>
        </div>

        {/* Day */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-500 font-medium">Day</label>
          <div className="col-span-3 flex items-center space-x-2">
            {daysOfWeek.map((day) => {
              const isSelected = (scheduleConfig.activeDays || []).includes(day.id);
              return (
                <button
                  key={day.id}
                  type="button"
                  onClick={() => toggleDay(day.id)}
                  className={`w-7 h-7 rounded-full text-xs font-semibold flex items-center justify-center transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[#146b63] text-white shadow-xs'
                      : 'border border-slate-300 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {day.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Time */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-500 font-medium">Time</label>
          <div className="col-span-3 flex items-center space-x-2">
            <input
              type="text"
              value={scheduleConfig.time}
              onChange={(e) => updateScheduleConfig({ time: e.target.value })}
              className="w-24 bg-white border border-slate-300 rounded px-3 py-1.5 text-slate-700 font-mono focus:outline-hidden focus:border-[#146b63]"
            />
            <span className="text-slate-500 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded text-[11px] font-mono">
              {scheduleConfig.timezone}
            </span>
          </div>
        </div>

        {/* Refresh data first */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-500 font-medium">Refresh data first</label>
          <div className="col-span-3">
            <Toggle
              enabled={scheduleConfig.refreshDataFirst}
              onChange={(val) => updateScheduleConfig({ refreshDataFirst: val })}
            />
          </div>
        </div>

        {/* Notify by email */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-500 font-medium">Notify by email</label>
          <div className="col-span-3">
            <input
              type="email"
              value={scheduleConfig.notifyEmail}
              onChange={(e) => updateScheduleConfig({ notifyEmail: e.target.value })}
              className="w-full max-w-sm bg-white border border-slate-300 rounded px-3 py-1.5 text-slate-700 focus:outline-hidden focus:border-[#146b63]"
            />
          </div>
        </div>

        {/* Notify me when */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-500 font-medium">Notify me when</label>
          <div className="col-span-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => toggleTrigger('runCompletes')}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
                scheduleConfig.notifyTriggers?.runCompletes
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 line-through'
              }`}
            >
              Run completes
            </button>
            <button
              type="button"
              onClick={() => toggleTrigger('runFails')}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
                scheduleConfig.notifyTriggers?.runFails
                  ? 'bg-rose-100 text-rose-800 border border-rose-300'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 line-through'
              }`}
            >
              Run fails
            </button>
            <button
              type="button"
              onClick={() => toggleTrigger('dataBlockers')}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
                scheduleConfig.notifyTriggers?.dataBlockers
                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 line-through'
              }`}
            >
              Data blockers
            </button>
          </div>
        </div>
      </div>

      {/* Buttons */}
      <div className="pt-2 flex items-center space-x-3">
        <button
          type="button"
          onClick={handleSave}
          className="px-4 py-2 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer"
        >
          {saveSuccess ? '✓ Saved!' : 'Save schedule'}
        </button>

        {/* RUN NOW - Real Instant Execution */}
        <button
          type="button"
          onClick={handleRunNow}
          disabled={isScreeningRunning}
          className={`flex items-center space-x-1.5 px-4 py-2 border rounded-md shadow-2xs text-xs font-semibold transition-colors ${
            isScreeningRunning
              ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
              : 'bg-white border-slate-300 hover:bg-slate-50 text-slate-700 cursor-pointer active:scale-98'
          }`}
        >
          {isScreeningRunning ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5 text-slate-600" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Running screen...</span>
            </>
          ) : (
            <>
              <span>⚡</span>
              <span>Run now</span>
            </>
          )}
        </button>

        <button
          type="button"
          onClick={() => setIsPaused((prev) => !prev)}
          className={`px-4 py-2 bg-white border text-xs font-semibold rounded-md shadow-2xs transition-colors cursor-pointer ${
            isPaused
              ? 'border-amber-400 bg-amber-50 text-amber-800'
              : 'border-slate-300 hover:bg-slate-50 text-slate-700'
          }`}
        >
          {isPaused ? 'Resume' : 'Pause'}
        </button>
      </div>
    </div>
  );
};
