import React, { useState, useEffect } from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { Toggle } from '../common/Toggle';

// Helper to parse 24h "HH:MM" into 12h time and period
function parse24to12(time24 = '08:30') {
  const parts = (time24 || '08:30').split(':');
  let h = parseInt(parts[0], 10);
  if (isNaN(h) || h < 0 || h > 23) h = 8;
  let m = parts[1] ? parseInt(parts[1], 10) : 0;
  if (isNaN(m) || m < 0 || m > 59) m = 30;
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return {
    time12: `${String(h12).padStart(2, '0')}:${String(m).padStart(2, '0')}`,
    period,
  };
}

// Helper to convert 12h time string and period back to 24h "HH:MM" with strict clamping
function format12to24(time12 = '08:30', period = 'AM') {
  const parts = (time12 || '08:30').split(':');
  let h = parseInt(parts[0], 10);
  if (isNaN(h)) h = 8;
  if (h < 1) h = 1;
  if (h > 12) h = 12;
  let m = parts[1] ? parseInt(parts[1], 10) : 0;
  if (isNaN(m) || m < 0) m = 0;
  if (m > 59) m = 59;
  if (period === 'AM') {
    if (h === 12) h = 0;
  } else {
    if (h < 12) h += 12;
  }
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

const TimePickerWithAmPm = ({ value24, onChange, timezone }) => {
  const parsed = parse24to12(value24);
  const [localText, setLocalText] = useState(parsed.time12);
  const [currentPeriod, setCurrentPeriod] = useState(parsed.period);

  // Sync from props only when value24 changes externally (e.g. preset buttons clicked)
  useEffect(() => {
    const p = parse24to12(value24);
    setLocalText(p.time12);
    setCurrentPeriod(p.period);
  }, [value24]);

  const commitTime = (text, period) => {
    const cleaned = (text || '').trim();
    if (!cleaned) return;
    const parts = cleaned.split(':');
    let h = parseInt(parts[0], 10);
    if (isNaN(h)) h = 8;
    if (h < 1) h = 1;
    if (h > 12) h = 12;

    let m = 0;
    if (parts.length > 1) {
      m = parseInt(parts[1], 10);
      if (isNaN(m) || m < 0) m = 0;
      if (m > 59) m = 59;
    }

    const formatted12 = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    setLocalText(formatted12);
    const new24 = format12to24(formatted12, period);
    onChange(new24);
  };

  const handleInputChange = (e) => {
    const val = e.target.value;
    // Allow digits and colon up to 5 characters
    if (/^[0-9:]*$/.test(val) && val.length <= 5) {
      setLocalText(val);
      // Auto-commit if user types full "HH:MM" e.g. "10:45"
      if (/^\d{1,2}:\d{2}$/.test(val)) {
        commitTime(val, currentPeriod);
      }
    }
  };

  const handleBlur = () => {
    commitTime(localText, currentPeriod);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      commitTime(localText, currentPeriod);
      e.target.blur();
    }
  };

  const handlePeriodChange = (newPeriod) => {
    setCurrentPeriod(newPeriod);
    const new24 = format12to24(localText, newPeriod);
    onChange(new24);
  };

  return (
    <div className="flex items-center space-x-2">
      <div className="flex items-center border border-slate-300 rounded overflow-hidden shadow-2xs bg-white focus-within:border-[#146b63]">
        <input
          type="text"
          value={localText}
          onChange={handleInputChange}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder="08:30"
          className="w-16 px-2.5 py-1 text-slate-800 font-mono text-xs focus:outline-hidden"
          title="Type time in 12-hour format (e.g. 10:45) and toggle AM/PM"
        />
        <div className="flex border-l border-slate-200 bg-slate-50 text-[11px] font-semibold">
          <button
            type="button"
            onClick={() => handlePeriodChange('AM')}
            className={`px-2 py-1 transition-colors cursor-pointer ${
              currentPeriod === 'AM'
                ? 'bg-[#146b63] text-white font-bold'
                : 'text-slate-600 hover:bg-slate-200/60'
            }`}
          >
            AM
          </button>
          <button
            type="button"
            onClick={() => handlePeriodChange('PM')}
            className={`px-2 py-1 transition-colors cursor-pointer ${
              currentPeriod === 'PM'
                ? 'bg-[#146b63] text-white font-bold'
                : 'text-slate-600 hover:bg-slate-200/60'
            }`}
          >
            PM
          </button>
        </div>
      </div>
      {timezone && (
        <span className="text-slate-500 bg-white border border-slate-200 px-2.5 py-1 rounded text-[11px] font-mono">
          {timezone}
        </span>
      )}
    </div>
  );
};

export const ScheduleConfigCard = () => {
  const {
    scheduleConfig,
    updateScheduleConfig,
    saveScheduleToBackend,
    nextRuns,
    triggerRunNow,
    isScreeningRunning,
    profiles,
    activateProfile,
    setActiveNav,
  } = useScreening();

  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [profileError, setProfileError] = useState(false);
  const [emailTouched, setEmailTouched] = useState(false);

  const notifyEmailValue = (scheduleConfig.notifyEmail || '').trim();
  const parsedEmails = notifyEmailValue
    .split(/[,;]+/)
    .map((e) => e.trim())
    .filter(Boolean);

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const isEmailValid = parsedEmails.length > 0 && parsedEmails.every((e) => emailRegex.test(e));

  const daysOfWeek = [
    { id: 'mon', label: 'Mon' },
    { id: 'tue', label: 'Tue' },
    { id: 'wed', label: 'Wed' },
    { id: 'thu', label: 'Thu' },
    { id: 'fri', label: 'Fri' },
  ];
  const frequencies = ['Daily', 'Weekly', 'Monthly', 'Custom'];

  // Current selected profile
  const selectedProfile =
    profiles.find((p) => p.id === scheduleConfig.selectedProfileId) ||
    profiles.find((p) => scheduleConfig.profile === `${p.name} - Version ${p.versionNumber}`) ||
    profiles.find((p) => scheduleConfig.profile === p.name) ||
    (profiles.length > 0 ? profiles[0] : null);

  const activeFrequency = scheduleConfig.frequency || 'Daily';
  const dailyType = scheduleConfig.dailyType || 'trading_days';
  const timeValue = scheduleConfig.time || '08:30';
  const timezoneValue = scheduleConfig.timezone || 'Asia/Kolkata';
  const isEnabled = scheduleConfig.isEnabled ?? true;

  const toggleDay = (day) => {
    const current = scheduleConfig.activeDays || [];
    const updated = current.includes(day)
      ? current.filter((d) => d !== day)
      : [...current, day];
    updateScheduleConfig({ activeDays: updated.length ? updated : ['mon'] });
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
        [key]: !scheduleConfig.notifyTriggers?.[key],
      },
    });
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (saveScheduleToBackend) {
        await saveScheduleToBackend();
      }
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    } catch (err) {
      console.error('Failed to save schedule:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRunNow = async () => {
    if (!selectedProfile || !selectedProfile.id) {
      setProfileError(true);
      return;
    }
    if (!isEmailValid) {
      setEmailTouched(true);
      return;
    }

    setProfileError(false);
    try {
      await triggerRunNow(selectedProfile.id, parsedEmails.join(', '));
      setActiveNav('results');
    } catch (err) {
      console.warn('Execution error:', err.message);
    }
  };

  // Human-readable next run string
  const firstNextRun = nextRuns && nextRuns.length ? new Date(nextRuns[0]) : null;
  const formattedNextRun = firstNextRun
    ? firstNextRun.toLocaleString('en-IN', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      }) + ' IST'
    : `Tomorrow at ${timeValue} IST`;

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <h2 className="text-base font-bold text-slate-800 flex items-center space-x-2">
            <span>{activeFrequency} Automated Screening</span>
            <span className="text-xs font-normal text-slate-400">| Phase 17 Scheduler</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Automatically executes institutional screening rules and emails reports at target market hours.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs text-slate-500 font-medium">Status:</span>
          <button
            type="button"
            onClick={() => updateScheduleConfig({ isEnabled: !isEnabled })}
            className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer ${
              isEnabled
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${isEnabled ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            <span>{isEnabled ? 'Active & Scheduled' : 'Schedule Paused'}</span>
          </button>
        </div>
      </div>

      <div className="space-y-5 text-xs">
        {/* 1. Strategy Profile Selection */}
        <div className="grid grid-cols-4 items-start gap-4">
          <label className="text-slate-600 font-medium pt-2">Strategy Profile</label>
          <div className="col-span-3 space-y-1.5">
            <select
              value={selectedProfile?.id || ''}
              onChange={handleProfileChange}
              className={`w-full bg-white border rounded px-3 py-2 text-slate-700 text-xs font-medium focus:outline-hidden transition-colors ${
                profileError
                  ? 'border-rose-400 bg-rose-50/20 focus:border-rose-500'
                  : 'border-slate-300 focus:border-[#146b63]'
              }`}
            >
              <option value="">-- Select a strategy profile to schedule --</option>
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name} - Version {profile.versionNumber} {profile.badge === 'Active' ? '(Active)' : ''}
                </option>
              ))}
            </select>
            {profileError && (
              <p className="text-[11px] font-semibold text-rose-600 flex items-center space-x-1">
                <span>⚠️ Please select a profile before running or saving.</span>
              </p>
            )}
          </div>
        </div>

        {/* 2. Frequency Selector */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-600 font-medium">Frequency</label>
          <div className="col-span-3 flex border border-slate-200 rounded-md overflow-hidden max-w-sm">
            {frequencies.map((freq) => {
              const isActive = activeFrequency === freq;
              return (
                <button
                  key={freq}
                  type="button"
                  onClick={() => updateScheduleConfig({ frequency: freq })}
                  className={`flex-1 py-1.5 text-center text-xs font-medium transition-colors cursor-pointer ${
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

        {/* 3. DYNAMIC CADENCE SECTION BASED ON FREQUENCY */}
        {activeFrequency === 'Daily' && (
          <div className="bg-slate-50/70 p-4 rounded-lg border border-slate-200 space-y-4">
            <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <span>📅</span>
              <span>Daily Cadence Configuration</span>
            </div>

            {/* Daily Type */}
            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Run On</label>
              <div className="col-span-3 flex items-center space-x-4">
                <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="radio"
                    name="dailyType"
                    value="trading_days"
                    checked={dailyType === 'trading_days'}
                    onChange={() => updateScheduleConfig({ dailyType: 'trading_days' })}
                    className="accent-[#146b63]"
                  />
                  <span className="font-medium">Every Trading Day (Mon–Fri)</span>
                </label>
                <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="radio"
                    name="dailyType"
                    value="all_days"
                    checked={dailyType === 'all_days'}
                    onChange={() => updateScheduleConfig({ dailyType: 'all_days' })}
                    className="accent-[#146b63]"
                  />
                  <span>Every Calendar Day (7 Days)</span>
                </label>
              </div>
            </div>

            {/* Daily Execution Time & Market Presets */}
            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Execution Time</label>
              <div className="col-span-3 flex flex-wrap items-center gap-3">
                <div className="flex items-center space-x-1.5">
                  <button
                    type="button"
                    onClick={() => updateScheduleConfig({ time: '08:30' })}
                    className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                      timeValue === '08:30'
                        ? 'bg-[#146b63] text-white font-semibold'
                        : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-100'
                    }`}
                    title="45 mins before NSE/BSE open"
                  >
                    Pre-Market (08:30 AM)
                  </button>
                  <button
                    type="button"
                    onClick={() => updateScheduleConfig({ time: '16:00' })}
                    className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                      timeValue === '16:00'
                        ? 'bg-[#146b63] text-white font-semibold'
                        : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-100'
                    }`}
                    title="After market close"
                  >
                    Post-Close (04:00 PM)
                  </button>
                </div>

                <div className="h-4 w-px bg-slate-300 hidden sm:block" />

                <div className="flex items-center space-x-2">
                  <span className="text-slate-500 text-[11px] font-medium">Or Custom:</span>
                  <TimePickerWithAmPm
                    value24={timeValue}
                    onChange={(new24) => updateScheduleConfig({ time: new24 })}
                    timezone={timezoneValue}
                  />
                </div>
              </div>
            </div>

            {/* Skip Holidays Checkbox - ONLY shown for Trading Days */}
            {dailyType === 'trading_days' ? (
              <div className="grid grid-cols-4 items-center gap-4">
                <span />
                <div className="col-span-3">
                  <label className="flex items-center space-x-2 text-xs text-slate-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={scheduleConfig.skipHolidays ?? true}
                      onChange={(e) => updateScheduleConfig({ skipHolidays: e.target.checked })}
                      className="accent-[#146b63]"
                    />
                    <span>Skip official national exchange holidays (e.g. Diwali, Independence Day, Christmas)</span>
                  </label>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-4 items-center gap-4">
                <span />
                <div className="col-span-3">
                  <p className="text-[11px] text-slate-500 italic flex items-center space-x-1">
                    <span>ℹ️</span>
                    <span>Calendar Day cadence runs 7 days a week, 365 days a year (including weekends and holidays).</span>
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeFrequency === 'Weekly' && (
          <div className="bg-slate-50/70 p-4 rounded-lg border border-slate-200 space-y-4">
            <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <span>📆</span>
              <span>Weekly Cadence Configuration</span>
            </div>

            {/* Day Selector */}
            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Active Days</label>
              <div className="col-span-3 flex items-center space-x-2">
                {daysOfWeek.map((day) => {
                  const isSelected = (scheduleConfig.activeDays || []).includes(day.id);
                  return (
                    <button
                      key={day.id}
                      type="button"
                      onClick={() => toggleDay(day.id)}
                      className={`px-3 py-1 rounded text-xs font-semibold flex items-center justify-center transition-colors cursor-pointer ${
                        isSelected
                          ? 'bg-[#146b63] text-white shadow-xs'
                          : 'bg-white border border-slate-300 text-slate-600 hover:bg-slate-100'
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
              <label className="text-slate-600 font-medium">Execution Time</label>
              <div className="col-span-3">
                <TimePickerWithAmPm
                  value24={timeValue}
                  onChange={(new24) => updateScheduleConfig({ time: new24 })}
                  timezone={timezoneValue}
                />
              </div>
            </div>
          </div>
        )}

        {activeFrequency === 'Monthly' && (
          <div className="bg-slate-50/70 p-4 rounded-lg border border-slate-200 space-y-4">
            <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <span>🗓️</span>
              <span>Monthly Cadence Configuration</span>
            </div>

            {/* Day of Month */}
            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Day of Month</label>
              <div className="col-span-3 flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => updateScheduleConfig({ dayOfMonth: 1 })}
                  className={`px-3 py-1 rounded text-xs transition-colors cursor-pointer ${
                    (scheduleConfig.dayOfMonth ?? 1) === 1
                      ? 'bg-[#146b63] text-white font-semibold'
                      : 'bg-white border border-slate-300 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  1st of Month
                </button>
                <button
                  type="button"
                  onClick={() => updateScheduleConfig({ dayOfMonth: 15 })}
                  className={`px-3 py-1 rounded text-xs transition-colors cursor-pointer ${
                    scheduleConfig.dayOfMonth === 15
                      ? 'bg-[#146b63] text-white font-semibold'
                      : 'bg-white border border-slate-300 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  15th of Month
                </button>
                <div className="flex items-center space-x-1.5 pl-2">
                  <span className="text-slate-500">Day:</span>
                  <input
                    type="number"
                    min="1"
                    max="31"
                    value={scheduleConfig.dayOfMonth ?? 1}
                    onChange={(e) => updateScheduleConfig({ dayOfMonth: parseInt(e.target.value, 10) || 1 })}
                    className="w-16 bg-white border border-slate-300 rounded px-2.5 py-1 text-slate-700 font-mono text-xs focus:outline-hidden focus:border-[#146b63]"
                  />
                </div>
              </div>
            </div>

            {/* Time */}
            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Execution Time</label>
              <div className="col-span-3">
                <TimePickerWithAmPm
                  value24={timeValue}
                  onChange={(new24) => updateScheduleConfig({ time: new24 })}
                  timezone={timezoneValue}
                />
              </div>
            </div>
          </div>
        )}

        {activeFrequency === 'Custom' && (
          <div className="bg-slate-50/70 p-4 rounded-lg border border-slate-200 space-y-4">
            <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <span>⚙️</span>
              <span>Custom Cron Expression</span>
            </div>

            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Cron Pattern</label>
              <div className="col-span-3 space-y-1.5">
                <input
                  type="text"
                  value={scheduleConfig.cronExpression || '0 9 * * 1-5'}
                  onChange={(e) => updateScheduleConfig({ cronExpression: e.target.value })}
                  placeholder="0 9 * * 1-5"
                  className="w-full max-w-sm bg-white border border-slate-300 rounded px-3 py-1.5 text-slate-700 font-mono text-xs focus:outline-hidden focus:border-[#146b63]"
                />
                <p className="text-[11px] text-slate-500">
                  Standard format: <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-700">minute hour day month day-of-week</code>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 4. Pre-Run Market Data Refresh */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-600 font-medium">Data Freshness</label>
          <div className="col-span-3 flex items-center space-x-3">
            <Toggle
              enabled={scheduleConfig.refreshDataFirst ?? true}
              onChange={(val) => updateScheduleConfig({ refreshDataFirst: val })}
            />
            <span className="text-slate-600 text-xs">
              Pull fresh vendor market snapshots before running pipeline
            </span>
          </div>
        </div>

        {/* 5. Notification Email(s) */}
        <div className="grid grid-cols-4 items-start gap-4">
          <label className="text-slate-600 font-medium pt-1.5 flex items-center space-x-1">
            <span>Notify by email(s)</span>
            <span className="text-rose-500 font-bold" title="Mandatory recipient">*</span>
          </label>
          <div className="col-span-3 space-y-1.5">
            <div className="relative max-w-md">
              <input
                type="text"
                placeholder="e.g. prabhas.muthyala@zeniusit.com, manoj@zenius.com"
                value={scheduleConfig.notifyEmail || ''}
                onChange={(e) => {
                  setEmailTouched(true);
                  updateScheduleConfig({ notifyEmail: e.target.value });
                }}
                onBlur={() => setEmailTouched(true)}
                className={`w-full bg-white border rounded px-3 py-2 text-slate-700 text-xs focus:outline-hidden transition-colors ${
                  !isEmailValid && emailTouched
                    ? 'border-rose-400 bg-rose-50/20 focus:border-rose-500'
                    : isEmailValid
                    ? 'border-emerald-500 focus:border-emerald-600'
                    : 'border-slate-300 focus:border-[#146b63]'
                }`}
              />
              {isEmailValid && (
                <span className="absolute right-2.5 top-2 text-emerald-600 font-bold text-xs" title={`Valid recipient${parsedEmails.length > 1 ? 's' : ''}`}>
                  ✓ {parsedEmails.length > 1 ? `(${parsedEmails.length})` : ''}
                </span>
              )}
            </div>
            {!notifyEmailValue ? (
              <p className="text-[11px] text-amber-700 font-medium flex items-center space-x-1">
                <span>⚠️</span>
                <span>Mandatory: Enter recipient email(s) (comma-separated for multiple) to receive Excel reports.</span>
              </p>
            ) : !isEmailValid ? (
              <p className="text-[11px] text-rose-600 font-medium flex items-center space-x-1">
                <span>⚠️</span>
                <span>One or more emails are invalid. Separate multiple emails with commas.</span>
              </p>
            ) : (
              <p className="text-[11px] text-emerald-700 font-medium flex items-center space-x-1">
                <span>✓</span>
                <span>Excel report (Top 20, Near Misses, Master Universe) will be emailed to {parsedEmails.length} recipient{parsedEmails.length > 1 ? 's' : ''}.</span>
              </p>
            )}
          </div>
        </div>

        {/* 6. Alert Triggers */}
        <div className="grid grid-cols-4 items-center gap-4">
          <label className="text-slate-600 font-medium">Notify when</label>
          <div className="col-span-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => toggleTrigger('runCompletes')}
              className={`px-3 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                scheduleConfig.notifyTriggers?.runCompletes
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 line-through'
              }`}
            >
              ✓ Run completes
            </button>
            <button
              type="button"
              onClick={() => toggleTrigger('runFails')}
              className={`px-3 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                scheduleConfig.notifyTriggers?.runFails
                  ? 'bg-rose-100 text-rose-800 border border-rose-300'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 line-through'
              }`}
            >
              ⚠ Run fails
            </button>
            <button
              type="button"
              onClick={() => toggleTrigger('dataBlockers')}
              className={`px-3 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                scheduleConfig.notifyTriggers?.dataBlockers
                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 line-through'
              }`}
            >
              ⚡ Data blockers
            </button>
          </div>
        </div>
      </div>

      {/* 7. LIVE SCHEDULE PREVIEW BOX */}
      <div className="p-3.5 bg-blue-50/50 border border-blue-200/80 rounded-lg text-xs space-y-1">
        <div className="font-semibold text-blue-900 flex items-center space-x-1.5">
          <span>🕒</span>
          <span>Next Scheduled Execution:</span>
          <span className="font-bold text-[#146b63]">{formattedNextRun}</span>
        </div>
        <p className="text-slate-600 text-[11px]">
          Target Strategy: <strong>{selectedProfile ? `${selectedProfile.name} - Version ${selectedProfile.versionNumber}` : 'Global Quality Growth Core'}</strong>
          {parsedEmails.length > 0 && ` · Delivering to: ${parsedEmails.join(', ')}`}
        </p>
      </div>

      {/* Action Buttons */}
      <div className="pt-2 flex items-center space-x-3 border-t border-slate-100">
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="px-5 py-2.5 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer flex items-center space-x-1.5"
        >
          {isSaving ? (
            <span>Saving...</span>
          ) : saveSuccess ? (
            <span>✓ Schedule Saved to Database!</span>
          ) : (
            <span>Save Schedule</span>
          )}
        </button>

        {/* RUN NOW - Instant Execution */}
        <button
          type="button"
          onClick={handleRunNow}
          disabled={isScreeningRunning || !selectedProfile || !isEmailValid}
          className={`px-5 py-2.5 text-xs font-semibold rounded-md shadow-xs transition-all flex items-center space-x-2 ${
            isScreeningRunning
              ? 'bg-blue-100 text-blue-700 border border-blue-200 cursor-not-allowed'
              : !selectedProfile || !isEmailValid
              ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
              : 'bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer active:scale-95'
          }`}
          title={
            !selectedProfile
              ? 'Please select a strategy profile'
              : !isEmailValid
              ? 'Enter mandatory notification email to enable Run now'
              : 'Execute strategy immediately and dispatch Excel report'
          }
        >
          {isScreeningRunning ? (
            <>
              <span className="h-2 w-2 rounded-full bg-blue-600 animate-ping" />
              <span>Running screening...</span>
            </>
          ) : (
            <>
              <span>⚡</span>
              <span>Run now</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
