import React, { useState } from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { Toggle } from '../common/Toggle';

export const ScheduleConfigCard = () => {
  const {
    scheduleConfig,
    updateScheduleConfig,
    triggerRunNow,
    profiles,
    activateProfile,
  } = useScreening();
  const [saveSuccess, setSaveSuccess] = useState(false);

  const daysOfWeek = [
    { id: 'mon', label: 'M' },
    { id: 'tue', label: 'T' },
    { id: 'wed', label: 'W' },
    { id: 'thu', label: 'T' },
    { id: 'fri', label: 'F' },
  ];
  const frequencies = ['Daily', 'Weekly', 'Monthly', 'Custom'];
  const selectedProfile = profiles.find(
    (profile) => scheduleConfig.profile === `${profile.name} - Version ${profile.versionNumber}`
  );

  const toggleDay = (day) => {
    const current = scheduleConfig.activeDays || [];
    const updated = current.includes(day)
      ? current.filter((d) => d !== day)
      : [...current, day];
    updateScheduleConfig({ activeDays: updated });
  };

  const handleProfileChange = (event) => {
    const profile = profiles.find((item) => item.id === event.target.value);
    if (!profile) return;

    activateProfile(profile.id);
    updateScheduleConfig({
      profile: `${profile.name} - Version ${profile.versionNumber}`,
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

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs space-y-5">
      <h2 className="text-base font-bold text-slate-800">Weekly Core screen</h2>

      <div className="space-y-4 text-xs">
        {/* Profile */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-500 font-medium">Profile</label>
          <div className="col-span-3">
            <select
              value={selectedProfile?.id || ''}
              onChange={handleProfileChange}
              className="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-slate-700 focus:outline-hidden focus:border-[#146b63]"
            >
              {profiles.length === 0 ? (
                <option value="">
                  No saved profiles available
                </option>
              ) : (
                <>
                  <option value="">Select a saved profile</option>
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name} - Version {profile.versionNumber}
                    </option>
                  ))}
                </>
              )}
            </select>
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
                  onClick={() => updateScheduleConfig({ frequency: freq })}
                  className={`flex-1 py-1.5 text-center font-medium transition-colors ${
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
                  onClick={() => toggleDay(day.id)}
                  className={`w-7 h-7 rounded-full text-xs font-semibold flex items-center justify-center transition-colors ${
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
              onClick={() => toggleTrigger('runCompletes')}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors ${
                scheduleConfig.notifyTriggers?.runCompletes
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 line-through'
              }`}
            >
              Run completes
            </button>
            <button
              onClick={() => toggleTrigger('runFails')}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors ${
                scheduleConfig.notifyTriggers?.runFails
                  ? 'bg-rose-100 text-rose-800 border border-rose-300'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 line-through'
              }`}
            >
              Run fails
            </button>
            <button
              onClick={() => toggleTrigger('dataBlockers')}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors ${
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
          onClick={handleSave}
          className="px-4 py-2 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded-md shadow-xs transition-colors"
        >
          {saveSuccess ? '✓ Saved!' : 'Save schedule'}
        </button>
        <button
          onClick={triggerRunNow}
          className="px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-md shadow-2xs transition-colors"
        >
          Run now
        </button>
        <button
          className="px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-md shadow-2xs transition-colors"
        >
          Pause
        </button>
      </div>
    </div>
  );
};
