const fs = require('fs');

let p = 'frontend/src/components/schedule/ScheduleConfigCard.jsx';
let content = fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');

// 1. Update handleSave to take forceNew = false
content = content.replace(
  `  const handleSave = async () => {
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
  };`,
  `  const handleSave = async (forceNew = false) => {
    setIsSaving(true);
    try {
      if (saveScheduleToBackend) {
        await saveScheduleToBackend({}, forceNew);
      }
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    } catch (err) {
      console.error('Failed to save schedule:', err);
    } finally {
      setIsSaving(false);
    }
  };`
);

// 2. Add Save As New Schedule button when isEditing is true
const targetButtons = `          <button
            type="button"
            onClick={handleSave}
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
          </button>`;

const newButtons = `          <button
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

content = content.replace(targetButtons, newButtons);

fs.writeFileSync(p, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated ScheduleConfigCard.jsx successfully.');

