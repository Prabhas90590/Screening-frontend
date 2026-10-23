import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  INITIAL_COUNTRIES,
  INITIAL_DIVERSIFICATION,
  INITIAL_EXCHANGES,
  INITIAL_FUNNEL,
  INITIAL_RUN_HISTORY,
  INITIAL_RULE_METRICS,
  INITIAL_SECTORS,
  INITIAL_SCHEDULE,
  INITIAL_SECTOR_LIMITS,
  INITIAL_SECURITIES,
} from '../data/mockData';
import {
  fetchProfiles as fetchProfilesApi,
  createProfile as createProfileApi,
  updateProfile as updateProfileApi,
  activateProfile as activateProfileApi,
  deleteProfile as deleteProfileApi,
} from '../services/api';

const ScreeningContext = createContext(null);

function reconstructSnapshotFromBackend(bp) {
  const rulesMap = new Map();
  (bp.rules || []).forEach((r) => {
    if (r.name) rulesMap.set(r.name.toLowerCase(), r);
    if (r.metric_name) rulesMap.set(r.metric_name.toLowerCase(), r);
    if (r.id) rulesMap.set(r.id.toLowerCase(), r);
  });

  const metrics = INITIAL_RULE_METRICS.map((metric) => {
    const matched = rulesMap.get(metric.name.toLowerCase());
    if (matched) {
      return {
        ...metric,
        mode: matched.mode || 'Both',
        condition: matched.condition || '>=',
        value: matched.value !== undefined ? String(matched.value) : String(matched.threshold_value ?? ''),
        weight: matched.weight !== undefined ? matched.weight : 0,
      };
    }
    return { ...metric };
  });

  const sectorLimitsMap = bp.sector_limits || {};
  const sectorLimits = INITIAL_SECTOR_LIMITS.map((sl) => {
    if (sectorLimitsMap[sl.sector] !== undefined) {
      return { ...sl, limit: String(sectorLimitsMap[sl.sector]) };
    }
    return { ...sl };
  });

  return {
    metrics,
    sectorLimits,
    countries: INITIAL_COUNTRIES.map((c) => ({ ...c })),
    exchanges: INITIAL_EXCHANGES.map((e) => ({ ...e })),
    sectors: INITIAL_SECTORS.map((s) => ({ ...s })),
    diversification: { ...INITIAL_DIVERSIFICATION },
  };
}

function mapBackendProfilesToFrontend(backendProfiles) {
  const parsedProfiles = [];
  const parsedHistory = [];

  backendProfiles.forEach((bp) => {
    const profileKey = bp.profile_name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const versionNumber = parseInt(String(bp.version_number).replace(/\D/g, '')) || 1;
    const versionStr = `v${versionNumber}`;
    const snapshot = bp.diversification_rules?.snapshot || reconstructSnapshotFromBackend(bp);

    const profileItem = {
      id: bp.version_id,
      profileKey,
      name: bp.profile_name,
      badge: bp.is_active ? 'Active' : 'Saved',
      description: bp.description || `Saved screening rules (${versionStr})`,
      version: versionStr,
      versionNumber,
      snapshot,
    };
    parsedProfiles.push(profileItem);

    const historyItem = {
      id: bp.version_id,
      profileKey,
      versionNumber,
      version: versionStr,
      isCurrent: bp.is_active,
      date: bp.updated_at
        ? new Date(bp.updated_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
        : 'Saved',
      by: 'PM',
      name: bp.profile_name,
      changeSummary: `${bp.rules?.length || 0} active rules configured in profile`,
      resultImpact: '-',
      changes: (bp.rules || []).map((r) => `${r.name || r.metric_name}: ${r.condition || ''} ${r.value ?? r.threshold_value ?? ''}`.trim()),
      snapshot,
    };
    parsedHistory.push(historyItem);
  });

  return { parsedProfiles, parsedHistory };
}

export const ScreeningProvider = ({ children }) => {
  const [activeNav, setActiveNav] = useState('rules'); // 'rules' | 'results' | 'schedule'
  const [rulesTab, setRulesTab] = useState('profiles'); // 'configuration' | 'profiles'
  const [resultsTab, setResultsTab] = useState('top20'); // 'top20' | 'rankNearMisses' | 'ruleNearMisses' | 'myHoldings' | 'allScreened'
  const [selectedProfileName, setSelectedProfileName] = useState('');
  const [draftProfileName, setDraftProfileName] = useState('');

  const [securities, setSecurities] = useState(INITIAL_SECURITIES);
  const [selectedSecurityId, setSelectedSecurityId] = useState(null);

  const [filterSector, setFilterSector] = useState('All');
  const [filterRegion, setFilterRegion] = useState('All');
  const [filterCap, setFilterCap] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const [funnelState, setFunnelState] = useState(INITIAL_FUNNEL);
  const [scheduleConfig, setScheduleConfig] = useState(INITIAL_SCHEDULE);
  const [runHistory, setRunHistory] = useState(INITIAL_RUN_HISTORY);

  // Persistent workspace states across browser refreshes
  const [sectorLimits, setSectorLimits] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_sector_limits');
      return cached ? JSON.parse(cached) : INITIAL_SECTOR_LIMITS;
    } catch {
      return INITIAL_SECTOR_LIMITS;
    }
  });

  const [sectors, setSectors] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_sectors');
      return cached ? JSON.parse(cached) : INITIAL_SECTORS;
    } catch {
      return INITIAL_SECTORS;
    }
  });

  const [countries, setCountries] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_countries');
      return cached ? JSON.parse(cached) : INITIAL_COUNTRIES;
    } catch {
      return INITIAL_COUNTRIES;
    }
  });

  const [exchanges, setExchanges] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_exchanges');
      return cached ? JSON.parse(cached) : INITIAL_EXCHANGES;
    } catch {
      return INITIAL_EXCHANGES;
    }
  });

  const [diversification, setDiversification] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_diversification');
      return cached ? JSON.parse(cached) : INITIAL_DIVERSIFICATION;
    } catch {
      return INITIAL_DIVERSIFICATION;
    }
  });

  const [ruleMetrics, setRuleMetrics] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_rule_metrics');
      return cached ? JSON.parse(cached) : INITIAL_RULE_METRICS;
    } catch {
      return INITIAL_RULE_METRICS;
    }
  });

  // Profiles and Version History with instant LocalStorage hydration & Backend sync
  const [profiles, setProfiles] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_profiles_cache');
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });

  const [versionHistory, setVersionHistory] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_history_cache');
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });

  const [editingVersion, setEditingVersion] = useState(null);
  const activeProfile = profiles.find((profile) => profile.badge === 'Active');

  const selectedSecurity = securities.find((s) => s.id === selectedSecurityId) || null;
  const selectedSectorNames = sectors.filter((sector) => sector.selected).map((sector) => sector.name);

  // Sync workspace state to localStorage on every change
  useEffect(() => {
    try {
      localStorage.setItem('screening_active_rule_metrics', JSON.stringify(ruleMetrics));
    } catch {}
  }, [ruleMetrics]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_sector_limits', JSON.stringify(sectorLimits));
    } catch {}
  }, [sectorLimits]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_countries', JSON.stringify(countries));
    } catch {}
  }, [countries]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_exchanges', JSON.stringify(exchanges));
    } catch {}
  }, [exchanges]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_sectors', JSON.stringify(sectors));
    } catch {}
  }, [sectors]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_diversification', JSON.stringify(diversification));
    } catch {}
  }, [diversification]);

  // Load authoritative profiles from PostgreSQL backend on mount
  useEffect(() => {
    let isMounted = true;

    async function loadBackendProfiles() {
      try {
        const backendProfiles = await fetchProfilesApi();
        if (isMounted && backendProfiles && Array.isArray(backendProfiles) && backendProfiles.length > 0) {
          const { parsedProfiles, parsedHistory } = mapBackendProfilesToFrontend(backendProfiles);
          setProfiles(parsedProfiles);
          setVersionHistory(parsedHistory);

          try {
            localStorage.setItem('screening_profiles_cache', JSON.stringify(parsedProfiles));
            localStorage.setItem('screening_history_cache', JSON.stringify(parsedHistory));
          } catch {}

          const active = parsedProfiles.find((p) => p.badge === 'Active') || parsedProfiles[0];
          if (active && active.snapshot) {
            setSelectedProfileName(`${active.name} - Version ${active.versionNumber}`);
            const hasLocalEdits = localStorage.getItem('screening_active_rule_metrics');
            if (!hasLocalEdits) {
              loadConfiguration(active.snapshot, false);
            }
          }
        }
      } catch (err) {
        console.warn('[ScreeningContext] Error loading profiles from backend:', err);
      }
    }

    loadBackendProfiles();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (filterSector !== 'All' && !selectedSectorNames.includes(filterSector)) {
      setFilterSector('All');
    }
  }, [filterSector, selectedSectorNames.join('|')]);

  const setSecurityDecision = (id, decision, reason, note) => {
    setSecurities((prev) =>
      prev.map((sec) =>
        sec.id === id
          ? {
              ...sec,
              decision,
              decisionReason: reason !== undefined ? reason : sec.decisionReason,
              decisionNote: note !== undefined ? note : sec.decisionNote,
            }
          : sec
      )
    );
  };

  const toggleSector = (name) => {
    setSectors((prev) =>
      prev.map((sector) => (sector.name === name ? { ...sector, selected: !sector.selected } : sector))
    );
  };

  const updateScheduleConfig = (updates) => {
    setScheduleConfig((prev) => ({ ...prev, ...updates }));
  };

  const triggerRunNow = () => {
    const nextRunNumber = funnelState.runInfo.runNumber + 1;
    const newHistoryItem = {
      id: String(nextRunNumber),
      run: `#${nextRunNumber}`,
      started: 'Just now',
      rules: activeProfile ? `${activeProfile.name} v${activeProfile.versionNumber}` : 'No active profile',
      profile: activeProfile?.name || 'No active profile',
      version: activeProfile ? `Version ${activeProfile.versionNumber}` : '-',
      screened: 1215,
      selected: 20,
      status: 'Succeeded',
      duration: '9 min',
    };
    setRunHistory([newHistoryItem, ...runHistory]);
    setFunnelState((prev) => ({
      ...prev,
      runInfo: {
        ...prev.runInfo,
        runNumber: nextRunNumber,
        asOfDate: 'data updated just now',
      },
    }));
  };

  const loadConfiguration = (snapshot, navigateToCatalog = true) => {
    if (!snapshot) return;
    const metrics = (snapshot.metrics || []).map((metric) => ({ ...metric }));
    const limits = (snapshot.sectorLimits || []).map((item) => ({ ...item }));
    const c = (snapshot.countries || INITIAL_COUNTRIES).map((country) => ({ ...country }));
    const ex = (snapshot.exchanges || INITIAL_EXCHANGES).map((exchange) => ({ ...exchange }));
    const sec = (snapshot.sectors || INITIAL_SECTORS).map((sector) => ({ ...sector }));
    const div = { ...(snapshot.diversification || INITIAL_DIVERSIFICATION) };

    setRuleMetrics(metrics);
    setSectorLimits(limits);
    setCountries(c);
    setExchanges(ex);
    setSectors(sec);
    setDiversification(div);

    try {
      localStorage.setItem('screening_active_rule_metrics', JSON.stringify(metrics));
      localStorage.setItem('screening_active_sector_limits', JSON.stringify(limits));
      localStorage.setItem('screening_active_countries', JSON.stringify(c));
      localStorage.setItem('screening_active_exchanges', JSON.stringify(ex));
      localStorage.setItem('screening_active_sectors', JSON.stringify(sec));
      localStorage.setItem('screening_active_diversification', JSON.stringify(div));
    } catch {}

    if (navigateToCatalog) {
      setRulesTab('catalog');
    }
  };

  const activateProfile = async (id) => {
    const target = profiles.find((p) => p.id === id);
    if (target) {
      try {
        await activateProfileApi(id);
      } catch (err) {
        console.warn('[ScreeningContext] Backend activation sync skipped:', err);
      }

      const version = versionHistory.find(
        (item) =>
          item.profileKey === target.profileKey &&
          item.versionNumber === target.versionNumber
      );
      loadConfiguration(target.snapshot || version?.snapshot, false);

      setProfiles((prev) => {
        const updated = prev.map((profile) => ({
          ...profile,
          badge: profile.id === id ? 'Active' : profile.badge === 'Active' ? 'Saved' : profile.badge,
        }));
        try {
          localStorage.setItem('screening_profiles_cache', JSON.stringify(updated));
        } catch {}
        return updated;
      });

      setVersionHistory((prev) => {
        const updated = prev.map((item) => ({
          ...item,
          isCurrent:
            item.profileKey === target.profileKey &&
            item.versionNumber === target.versionNumber,
        }));
        try {
          localStorage.setItem('screening_history_cache', JSON.stringify(updated));
        } catch {}
        return updated;
      });

      setSelectedProfileName(`${target.name} - Version ${target.versionNumber}`);
    }
  };

  const restoreVersion = (version) => {
    const target = versionHistory.find(
      (item) => item.id === version || item.version === version
    );
    loadConfiguration(target?.snapshot, false);
    if (target) {
      setProfiles((prev) => {
        const updated = prev.map((profile) => ({
          ...profile,
          badge:
            profile.profileKey === target.profileKey &&
            profile.versionNumber === target.versionNumber
              ? 'Active'
              : profile.badge === 'Active'
                ? 'Saved'
                : profile.badge,
        }));
        try {
          localStorage.setItem('screening_profiles_cache', JSON.stringify(updated));
        } catch {}
        return updated;
      });
    }
    setVersionHistory((prev) => {
      const updated = prev.map((v) => ({
        ...v,
        isCurrent: v.id === version || v.version === version,
      }));
      try {
        localStorage.setItem('screening_history_cache', JSON.stringify(updated));
      } catch {}
      return updated;
    });
    if (target) {
      setSelectedProfileName(`${target.name || 'Saved profile'} - Version ${target.versionNumber}`);
    }
  };

  const updateSectorLimit = (sector, newLimit) => {
    setSectorLimits((prev) =>
      prev.map((item) => (item.sector === sector ? { ...item, limit: newLimit } : item))
    );
  };

  const updateSectorNote = (sector, note) => {
    setSectorLimits((prev) =>
      prev.map((item) => (item.sector === sector ? { ...item, note } : item))
    );
  };

  const toggleCountry = (id) => {
    setCountries((prev) =>
      prev.map((country) => (country.id === id ? { ...country, selected: !country.selected } : country))
    );
    setExchanges((prev) =>
      prev.map((exchange) =>
        exchange.countryId === id && countries.find((country) => country.id === id)?.selected
          ? { ...exchange, selected: false }
          : exchange
      )
    );
  };

  const toggleExchange = (id) => {
    setExchanges((prev) =>
      prev.map((exchange) => (exchange.id === id ? { ...exchange, selected: !exchange.selected } : exchange))
    );
  };

  const updateDiversification = (updates) => {
    setDiversification((prev) => ({ ...prev, ...updates }));
  };

  const updateRuleMetric = (metricName, updates) => {
    setRuleMetrics((prev) =>
      prev.map((metric) => (metric.name === metricName ? { ...metric, ...updates } : metric))
    );
  };

  const saveConfigurationAsNewVersion = async (name, configuration, profileKey = null, editedFromVersion = null) => {
    const trimmedName = name.trim();
    const snapshot = configuration || {
      metrics: ruleMetrics.map((metric) => ({ ...metric })),
      sectorLimits: sectorLimits.map((item) => ({ ...item })),
      countries: countries.map((country) => ({ ...country })),
      exchanges: exchanges.map((exchange) => ({ ...exchange })),
      sectors: sectors.map((sector) => ({ ...sector })),
      diversification: { ...diversification },
    };
    const existingProfile = profiles.find(
      (profile) => profile.name.trim().toLowerCase() === trimmedName.toLowerCase()
    );
    const nextProfileKey =
      profileKey ||
      existingProfile?.profileKey ||
      `${trimmedName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${Date.now()}`;
    const nextVersionNumber =
      Math.max(
        ...profiles
          .filter((profile) => profile.profileKey === nextProfileKey)
          .map((profile) => profile.versionNumber || 0),
        0
      ) + 1;
    const version = `v${nextVersionNumber}`;

    // Format for backend PostgreSQL persistence
    const sectorLimitsMap = {};
    (snapshot.sectorLimits || []).forEach((item) => {
      if (item.limit !== '' && !isNaN(parseFloat(item.limit))) {
        sectorLimitsMap[item.sector] = parseFloat(item.limit);
      }
    });

    const activeRulesForBackend = (snapshot.metrics || [])
      .filter((m) => m.mode !== 'Off' || m.value !== '' || m.condition !== '')
      .map((m) => ({
        id: m.name.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
        name: m.name,
        category: m.category || 'Valuation',
        mode: m.mode || 'Both',
        condition: m.condition || '>=',
        value: parseFloat(m.value) || 0.0,
        value_display: `${m.condition || ''} ${m.value || ''}`.trim(),
        weight: parseFloat(m.weight) || 0.0,
      }));

    const backendPayload = {
      profile_name: trimmedName,
      version_number: String(nextVersionNumber),
      description: `Saved screening rules (Version ${nextVersionNumber})`,
      is_active: true,
      sector_limits: sectorLimitsMap,
      diversification_rules: {
        ...snapshot.diversification,
        snapshot,
      },
      rules: activeRulesForBackend,
    };

    let backendVersionId = `${nextProfileKey}-${version}`;
    try {
      const createdBackend = await createProfileApi(backendPayload);
      if (createdBackend?.version_id) {
        backendVersionId = createdBackend.version_id;
      }
    } catch (err) {
      console.warn('[ScreeningContext] Could not persist profile to backend, using local store:', err);
    }

    const newHistoryItem = {
      id: backendVersionId,
      profileKey: nextProfileKey,
      versionNumber: nextVersionNumber,
      version,
      isCurrent: true,
      date: new Date().toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }),
      by: 'PM',
      name: trimmedName,
      editedFromVersion,
      changeSummary: `${activeRulesForBackend.length} active rules configured in profile`,
      resultImpact: '-',
      changes: activeRulesForBackend.map((r) => `${r.name}: ${r.condition} ${r.value}`),
      snapshot,
    };

    const newProfileItem = {
      id: backendVersionId,
      profileKey: nextProfileKey,
      name: trimmedName,
      badge: 'Active',
      description: `Saved screening rules (Version ${nextVersionNumber})`,
      version,
      versionNumber: nextVersionNumber,
      snapshot,
    };

    setVersionHistory((prev) => {
      const updated = [newHistoryItem, ...prev.map((item) => ({ ...item, isCurrent: false }))];
      try {
        localStorage.setItem('screening_history_cache', JSON.stringify(updated));
      } catch {}
      return updated;
    });

    setProfiles((prev) => {
      const updated = [
        ...prev.map((profile) => ({
          ...profile,
          badge: profile.badge === 'Active' ? 'Saved' : profile.badge,
        })),
        newProfileItem,
      ];
      try {
        localStorage.setItem('screening_profiles_cache', JSON.stringify(updated));
      } catch {}
      return updated;
    });

    setSelectedProfileName(`${trimmedName} - ${version}`);
    return { saved: true, version };
  };

  const deleteVersion = async (versionId) => {
    const target = versionHistory.find(
      (item) => item.id === versionId || item.version === versionId
    );
    if (!target) return false;

    try {
      await deleteProfileApi(target.id);
    } catch (err) {
      console.warn('[ScreeningContext] Backend delete sync skipped:', err);
    }

    const remainingHistory = versionHistory.filter((item) => item.id !== target.id);
    const profileVersions = remainingHistory
      .filter((item) => item.profileKey === target.profileKey)
      .sort((left, right) => (right.versionNumber || 0) - (left.versionNumber || 0));
    const replacement = profileVersions.find((item) => item.isCurrent) || profileVersions[0];

    const updatedHistory = remainingHistory.map((item) => ({
      ...item,
      isCurrent: item.profileKey === target.profileKey
        ? Boolean(replacement && item.id === replacement.id)
        : item.isCurrent,
    }));
    setVersionHistory(updatedHistory);
    try {
      localStorage.setItem('screening_history_cache', JSON.stringify(updatedHistory));
    } catch {}

    setProfiles((prev) => {
      const remainingProfiles = prev.filter((profile) => profile.id !== target.id);
      let updatedProfiles;
      if (!replacement) {
        updatedProfiles = remainingProfiles;
      } else {
        updatedProfiles = remainingProfiles.map((profile) => (
          profile.profileKey === target.profileKey
            ? {
                ...profile,
                badge: profile.id === replacement.id ? 'Active' : 'Saved',
              }
            : profile
        ));
      }
      try {
        localStorage.setItem('screening_profiles_cache', JSON.stringify(updatedProfiles));
      } catch {}
      return updatedProfiles;
    });

    return true;
  };

  const beginVersionEdit = (versionId) => {
    const target = versionHistory.find((item) => item.id === versionId || item.version === versionId);
    if (!target?.snapshot) return;

    loadConfiguration(target.snapshot);
    setEditingVersion({
      id: target.id || target.version,
      name: target.name || 'Saved profile',
      profileKey: target.profileKey,
      versionNumber: target.versionNumber,
    });
    setRulesTab('configuration');
  };

  const saveAsNewVersion = (name) => saveConfigurationAsNewVersion(name);

  const discardChanges = () => {
    setRuleMetrics(INITIAL_RULE_METRICS.map((metric) => ({ ...metric })));
    setSectorLimits(INITIAL_SECTOR_LIMITS.map((item) => ({ ...item })));
    setSectors(INITIAL_SECTORS.map((sector) => ({ ...sector })));
    setCountries(INITIAL_COUNTRIES.map((country) => ({ ...country })));
    setExchanges(INITIAL_EXCHANGES.map((exchange) => ({ ...exchange })));
    setDiversification({ ...INITIAL_DIVERSIFICATION });

    try {
      localStorage.removeItem('screening_active_rule_metrics');
      localStorage.removeItem('screening_active_sector_limits');
      localStorage.removeItem('screening_active_countries');
      localStorage.removeItem('screening_active_exchanges');
      localStorage.removeItem('screening_active_sectors');
      localStorage.removeItem('screening_active_diversification');
    } catch {}
  };

  return (
    <ScreeningContext.Provider
      value={{
        activeNav,
        setActiveNav,
        rulesTab,
        setRulesTab,
        resultsTab,
        setResultsTab,
        selectedProfileName,
        draftProfileName,
        setDraftProfileName,
        selectedSecurity,
        selectedSecurityId,
        setSelectedSecurityId,
        securities,
        filterSector,
        setFilterSector,
        filterRegion,
        setFilterRegion,
        filterCap,
        setFilterCap,
        searchQuery,
        setSearchQuery,
        funnelState,
        setSecurityDecision,
        scheduleConfig,
        updateScheduleConfig,
        runHistory,
        triggerRunNow,
        profiles,
        activateProfile,
        versionHistory,
        restoreVersion,
        editingVersion,
        setEditingVersion,
        beginVersionEdit,
        sectorLimits,
        updateSectorLimit,
        updateSectorNote,
        ruleMetrics,
        updateRuleMetric,
        saveAsNewVersion,
        saveConfigurationAsNewVersion,
        deleteVersion,
        discardChanges,
        loadConfiguration,
        countries,
        sectors,
        toggleCountry,
        exchanges,
        toggleExchange,
        toggleSector,
        diversification,
        updateDiversification,
      }}
    >
      {children}
    </ScreeningContext.Provider>
  );
};

export const useScreening = () => {
  const context = useContext(ScreeningContext);
  if (!context) {
    throw new Error('useScreening must be used within a ScreeningProvider');
  }
  return context;
};
