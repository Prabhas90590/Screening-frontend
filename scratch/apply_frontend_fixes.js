const fs = require('fs');

// =========================================================================
// 1. UPDATE frontend/src/context/ScreeningContext.jsx
// =========================================================================
let ctxPath = 'frontend/src/context/ScreeningContext.jsx';
let ctxContent = fs.readFileSync(ctxPath, 'utf8').replace(/\r\n/g, '\n');

// When saving a schedule, only retain scheduleId if user was explicitly editing an existing schedule.
// If forceNew was true or scheduleConfig.scheduleId was empty, set scheduleId to '' so edit mode is NOT sticky!
const targetSaveBlock = `  const saveScheduleToBackend = async (updates = {}, forceNew = false) => {
    const merged = { ...scheduleConfig, ...updates };
    const cleanTime = (merged.time || '08:30').replace(':', '');
    const cleanFreq = (merged.frequency || 'daily').toLowerCase();
    let schedId = forceNew ? '' : merged.scheduleId;
    if (!schedId) {
      const rand = Math.random().toString(36).substring(2, 7);
      schedId = \`sched-\${cleanFreq}-\${cleanTime}-\${rand}\`;
    }`;

const newSaveBlock = `  const saveScheduleToBackend = async (updates = {}, forceNew = false) => {
    const isNew = forceNew || !scheduleConfig.scheduleId;
    const merged = { ...scheduleConfig, ...updates };
    const cleanTime = (merged.time || '08:30').replace(':', '');
    const cleanFreq = (merged.frequency || 'daily').toLowerCase();
    let schedId = forceNew ? '' : merged.scheduleId;
    if (!schedId) {
      const rand = Math.random().toString(36).substring(2, 7);
      schedId = \`sched-\${cleanFreq}-\${cleanTime}-\${rand}\`;
    }`;

ctxContent = ctxContent.replace(targetSaveBlock, newSaveBlock);

ctxContent = ctxContent.replace(
  `        setScheduleConfig((prev) => ({ ...prev, ...merged, scheduleId: schedId }));
        return res;
      }
    } catch (err) {
      console.warn('[ScreeningContext] Could not save schedule to backend:', err.message);
      setScheduleConfig((prev) => ({ ...prev, ...merged, scheduleId: schedId }));
    }`,
  `        // Only enter edit mode if user was already editing an existing schedule.
        // For newly created schedules, keep scheduleId empty so edit banner does not trap the user!
        setScheduleConfig((prev) => ({
          ...prev,
          ...merged,
          scheduleId: isNew ? '' : schedId,
        }));
        return res;
      }
    } catch (err) {
      console.warn('[ScreeningContext] Could not save schedule to backend:', err.message);
      setScheduleConfig((prev) => ({
        ...prev,
        ...merged,
        scheduleId: isNew ? '' : schedId,
      }));
    }`
);

fs.writeFileSync(ctxPath, ctxContent.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated ScreeningContext.jsx');

// =========================================================================
// 2. UPDATE frontend/src/components/schedule/ScheduleConfigCard.jsx
// =========================================================================
let cardPath = 'frontend/src/components/schedule/ScheduleConfigCard.jsx';
let cardContent = fs.readFileSync(cardPath, 'utf8').replace(/\r\n/g, '\n');

// A. Filter Active Saved Schedules in the card by activeFrequency
const oldMapSchedules = `            <div className="space-y-2">
            {allSchedules.map((s) => {
              const isCurrent =
                scheduleConfig?.scheduleId === s.schedule_id ||
                (!scheduleConfig?.scheduleId &&
                  scheduleConfig?.time === s.time_of_day &&
                  scheduleConfig?.frequency === s.frequency);`;

const newMapSchedules = `            <div className="space-y-2">
            {(() => {
              const displayedSchedules = (allSchedules || []).filter(
                (s) => (s.frequency || '').toLowerCase() === (activeFrequency || 'daily').toLowerCase()
              );

              if (displayedSchedules.length === 0) {
                return (
                  <div className="p-4 bg-slate-50 border border-dashed border-slate-200 rounded-md text-center text-slate-400 text-xs">
                    No {activeFrequency} schedules configured yet. Adjust parameters below and click <strong>+ Save New Schedule</strong>.
                  </div>
                );
              }

              return displayedSchedules.map((s) => {
                const isCurrent = Boolean(scheduleConfig?.scheduleId) && scheduleConfig.scheduleId === s.schedule_id;`;

cardContent = cardContent.replace(oldMapSchedules, newMapSchedules);

// Close the IIFE in ScheduleConfigCard
cardContent = cardContent.replace(
  `                    </div>
                  </div>
                </div>
              );
            })}
          </div>`,
  `                    </div>
                  </div>
                </div>
              );
            });
            })()}
          </div>`
);

// B. In frequency buttons, switch cadence cleanly without carrying over old scheduleId
const oldFreqButton = `              return (
                <button
                  key={freq}
                  type="button"
                  onClick={() => updateScheduleConfig({ frequency: freq })}
                  className={\`flex-1 py-1.5 text-center text-xs font-medium transition-colors cursor-pointer \${`;

const newFreqButton = `              return (
                <button
                  key={freq}
                  type="button"
                  onClick={() => {
                    // Switching cadence cancels edit mode of different frequency
                    const isDifferent = scheduleConfig?.scheduleId && scheduleConfig?.frequency !== freq;
                    updateScheduleConfig({
                      frequency: freq,
                      scheduleId: isDifferent ? '' : (scheduleConfig?.scheduleId || ''),
                    });
                  }}
                  className={\`flex-1 py-1.5 text-center text-xs font-medium transition-colors cursor-pointer \${`;

cardContent = cardContent.replace(oldFreqButton, newFreqButton);

// C. Bottom Action Buttons: Clear separation between Update Schedule and + Save New Schedule
const oldBottomButtons = `          <button
            type="button"
            onClick={() => handleSave(false)}
            disabled={isSaving}
            className="px-5 py-2.5 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer flex items-center space-x-1.5"
          >
            {isSaving ? (
              <span>Saving...</span>
            ) : saveSuccess ? (
              <span>✓ Schedule Saved!</span>
            ) : isEditing ? (
              <span>✓ Update Schedule</span>
            ) : (
              <span>+ Save New Schedule</span>
            )}
          </button>

          {isEditing && (
            <button
              type="button"
              onClick={() => handleSave(true)}
              disabled={isSaving}
              className="px-3.5 py-2.5 bg-white hover:bg-slate-50 text-[#146b63] border border-[#146b63]/30 text-xs font-semibold rounded-md shadow-2xs transition-colors cursor-pointer flex items-center space-x-1"
              title="Save these settings as a brand new independent schedule"
            >
              <span>+</span>
              <span>Save As New Schedule</span>
            </button>
          )}`;

const newBottomButtons = `          {isEditing ? (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => handleSave(false)}
                disabled={isSaving}
                className="px-5 py-2.5 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer flex items-center space-x-1.5"
              >
                {isSaving ? (
                  <span>Updating...</span>
                ) : saveSuccess ? (
                  <span>✓ Schedule Updated!</span>
                ) : (
                  <span>✓ Update Schedule</span>
                )}
              </button>
              <button
                type="button"
                onClick={() => handleSave(true)}
                disabled={isSaving}
                className="px-3.5 py-2.5 bg-white hover:bg-slate-50 text-[#146b63] border border-[#146b63]/30 text-xs font-semibold rounded-md shadow-2xs transition-colors cursor-pointer flex items-center space-x-1"
                title="Save these settings as a brand new independent schedule"
              >
                <span>+</span>
                <span>Save As New Schedule</span>
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => handleSave(false)}
              disabled={isSaving}
              className="px-5 py-2.5 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer flex items-center space-x-1.5"
            >
              {isSaving ? (
                <span>Saving...</span>
              ) : saveSuccess ? (
                <span>✓ Schedule Saved!</span>
              ) : (
                <span>+ Save New Schedule</span>
              )}
            </button>
          )}`;

cardContent = cardContent.replace(oldBottomButtons, newBottomButtons);

fs.writeFileSync(cardPath, cardContent.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated ScheduleConfigCard.jsx');

// =========================================================================
// 3. UPDATE frontend/src/components/schedule/RunHistoryTable.jsx
// =========================================================================
let rhtPath = 'frontend/src/components/schedule/RunHistoryTable.jsx';
let rhtContent = fs.readFileSync(rhtPath, 'utf8').replace(/\r\n/g, '\n');

// Add displayedForecastRuns filtered by cadenceFilter
const targetRhtState = `  const displayedSchedules = cadenceFilter === 'all'
    ? (allSchedules || [])
    : (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === cadenceFilter);`;

const newRhtState = `  const displayedSchedules = cadenceFilter === 'all'
    ? (allSchedules || [])
    : (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === cadenceFilter);

  const displayedForecastRuns = cadenceFilter === 'all'
    ? upcomingRunsList
    : upcomingRunsList.filter((item) => (item.frequency || '').toLowerCase() === cadenceFilter);`;

rhtContent = rhtContent.replace(targetRhtState, newRhtState);

// Replace forecast mapping to use displayedForecastRuns
rhtContent = rhtContent.replace(
  '{upcomingRunsList.length > 0 && (',
  '{displayedForecastRuns.length > 0 && ('
);
rhtContent = rhtContent.replace(
  'Execution Cycles Forecast (Next {upcomingRunsList.length} Runs)',
  'Execution Cycles Forecast (Next {displayedForecastRuns.length} Runs)'
);
rhtContent = rhtContent.replace(
  '{upcomingRunsList.map((item, idx) => {',
  '{displayedForecastRuns.map((item, idx) => {'
);

fs.writeFileSync(rhtPath, rhtContent.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated RunHistoryTable.jsx');

