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

const ScreeningContext = createContext(null);

export const ScreeningProvider = ({ children }) => {
  const [activeNav, setActiveNav] = useState('rules'); // 'rules' | 'results' | 'schedule'
  const [rulesTab, setRulesTab] = useState('profiles'); // 'configuration' | 'profiles'
  const [resultsTab, setResultsTab] = useState('top20'); // 'top20' | 'rankNearMisses' | 'ruleNearMisses' | 'myHoldings' | 'allScreened'
  const [selectedProfileName, setSelectedProfileName] = useState('');
  const [draftProfileName, setDraftProfileName] = useState('');

  const [securities, setSecurities] = useState(INITIAL_SECURITIES);
  const [selectedSecurityId, setSelectedSecurityId] = useState('hmp');

  const [filterSector, setFilterSector] = useState('All');
  const [filterRegion, setFilterRegion] = useState('All');
  const [filterCap, setFilterCap] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const [funnelState, setFunnelState] = useState(INITIAL_FUNNEL);
  const [scheduleConfig, setScheduleConfig] = useState(INITIAL_SCHEDULE);
  const [runHistory, setRunHistory] = useState(INITIAL_RUN_HISTORY);
  const [sectorLimits, setSectorLimits] = useState(INITIAL_SECTOR_LIMITS);
  const [sectors, setSectors] = useState(INITIAL_SECTORS);
  const [countries, setCountries] = useState(INITIAL_COUNTRIES);
  const [exchanges, setExchanges] = useState(INITIAL_EXCHANGES);
  const [diversification, setDiversification] = useState(INITIAL_DIVERSIFICATION);
  const [ruleMetrics, setRuleMetrics] = useState(INITIAL_RULE_METRICS);
  const [profiles, setProfiles] = useState([]);
  const [versionHistory, setVersionHistory] = useState([]);
  const [editingVersion, setEditingVersion] = useState(null);
  const activeProfile = profiles.find((profile) => profile.badge === 'Active');

  const selectedSecurity = securities.find((s) => s.id === selectedSecurityId) || null;
  const selectedSectorNames = sectors.filter((sector) => sector.selected).map((sector) => sector.name);

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
    setRuleMetrics(snapshot.metrics.map((metric) => ({ ...metric })));
    setSectorLimits(snapshot.sectorLimits.map((item) => ({ ...item })));
    setSectors((snapshot.sectors || INITIAL_SECTORS).map((sector) => ({ ...sector })));
    setCountries(snapshot.countries.map((country) => ({ ...country })));
    setExchanges((snapshot.exchanges || INITIAL_EXCHANGES).map((exchange) => ({ ...exchange })));
    setDiversification({ ...snapshot.diversification });
    if (navigateToCatalog) {
      setRulesTab('catalog');
    }
  };

  const activateProfile = (id) => {
    const target = profiles.find((p) => p.id === id);
    if (target) {
      const version = versionHistory.find(
        (item) =>
          item.profileKey === target.profileKey &&
          item.versionNumber === target.versionNumber
      );
      loadConfiguration(target.snapshot || version?.snapshot, false);
      setProfiles((prev) =>
        prev.map((profile) => ({
          ...profile,
          badge: profile.id === id ? 'Active' : profile.badge === 'Active' ? 'Saved' : profile.badge,
        }))
      );
      setVersionHistory((prev) =>
        prev.map((item) => ({
          ...item,
          isCurrent:
            item.profileKey === target.profileKey &&
            item.versionNumber === target.versionNumber,
        }))
      );
      setSelectedProfileName(`${target.name} - Version ${target.versionNumber}`);
    }
  };

  const restoreVersion = (version) => {
    const target = versionHistory.find(
      (item) => item.id === version || item.version === version
    );
    loadConfiguration(target?.snapshot, false);
    if (target) {
      setProfiles((prev) =>
        prev.map((profile) => ({
          ...profile,
          badge:
            profile.profileKey === target.profileKey &&
            profile.versionNumber === target.versionNumber
              ? 'Active'
              : profile.badge === 'Active'
                ? 'Saved'
                : profile.badge,
        }))
      );
    }
    setVersionHistory((prev) =>
      prev.map((v) => ({
        ...v,
        isCurrent: v.id === version || v.version === version,
      }))
    );
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

  const saveConfigurationAsNewVersion = (name, configuration, profileKey = null, editedFromVersion = null) => {
    const trimmedName = name.trim();
    const snapshot = configuration || {
      metrics: ruleMetrics.map((metric) => ({ ...metric })),
      sectorLimits: sectorLimits.map((item) => ({ ...item })),
      countries: countries.map((country) => ({ ...country })),
      exchanges: exchanges.map((exchange) => ({ ...exchange })),
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
    const previousSnapshot = versionHistory.find(
      (item) =>
        item.profileKey === nextProfileKey &&
        item.versionNumber === nextVersionNumber - 1
    )?.snapshot;
    const configurationsMatch = (left, right) =>
      JSON.stringify(left) === JSON.stringify(right);
    if (configurationsMatch(snapshot, previousSnapshot || {
      metrics: INITIAL_RULE_METRICS,
      sectorLimits: INITIAL_SECTOR_LIMITS,
      countries: INITIAL_COUNTRIES,
      exchanges: INITIAL_EXCHANGES,
      sectors: INITIAL_SECTORS,
      diversification: INITIAL_DIVERSIFICATION,
    })) {
      return { saved: false, reason: 'no-changes' };
    }
    const changedRules = snapshot.metrics
      .filter((metric) => {
        const previous = previousSnapshot?.metrics.find((item) => item.name === metric.name);
        return !previous || ['mode', 'condition', 'value', 'weight', 'category'].some(
          (field) => previous[field] !== metric[field]
        );
      })
      .map((metric) => `${metric.name}: ${metric.condition || 'no condition'} ${metric.value || ''}`.trim());
    const changedLimits = snapshot.sectorLimits
      .filter((limit) => {
        const previous = previousSnapshot?.sectorLimits.find((item) => item.sector === limit.sector);
        return !previous || previous.limit !== limit.limit || previous.note !== limit.note;
      })
      .map((limit) => `${limit.sector} limit updated`);
    const previousCountries = previousSnapshot?.countries || [];
    const changedCountries = snapshot.countries
      .filter((country) => {
        const previous = previousCountries.find((item) => item.id === country.id);
        return previous?.selected !== country.selected;
      })
      .map((country) => `${country.name}: ${country.selected ? 'selected' : 'deselected'}`);
    const previousExchanges = previousSnapshot?.exchanges || [];
    const changedExchanges = (snapshot.exchanges || [])
      .filter((exchange) => previousExchanges.find((item) => item.id === exchange.id)?.selected !== exchange.selected)
      .map((exchange) => `${exchange.name}: ${exchange.selected ? 'selected' : 'deselected'}`);
    const previousSectors = previousSnapshot?.sectors || [];
    const changedSectors = (snapshot.sectors || [])
      .filter((sector) => previousSectors.find((item) => item.name === sector.name)?.selected !== sector.selected)
      .map((sector) => `${sector.name}: ${sector.selected ? 'selected' : 'deselected'}`);
    const changedDiversification = Object.keys(snapshot.diversification)
      .filter((key) => snapshot.diversification[key] !== previousSnapshot?.diversification?.[key])
      .map((key) => `${key}: ${previousSnapshot?.diversification?.[key] ?? 'not set'} → ${snapshot.diversification[key] ?? 'not set'}`);
    const changes = [
      ...changedRules.map((change) => `Rule updated · ${change}`),
      ...changedLimits.map((change) => `Limit updated · ${change}`),
      ...changedCountries.map((change) => `Universe updated · ${change}`),
      ...changedExchanges.map((change) => `Exchange universe updated · ${change}`),
      ...changedSectors.map((change) => `Sector universe updated · ${change}`),
      ...changedDiversification.map((change) => `Diversification updated · ${change}`),
    ];
    const isInitialVersion = nextVersionNumber === 1;
    const historyChanges = isInitialVersion ? [] : changes;

    setVersionHistory((prev) => [
      {
        id: `${nextProfileKey}-${version}`,
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
        changeSummary: isInitialVersion
          ? 'Initial profile configuration saved'
          : changes.length
          ? `${changes.length} rule${changes.length === 1 ? '' : 's'} changed`
          : `${snapshot.metrics.length} metrics and limits saved`,
        resultImpact: '-',
        changes: historyChanges,
        snapshot,
      },
      ...prev.map((item) => ({ ...item, isCurrent: false })),
    ]);
    setProfiles((prev) => {
      const updated = prev.map((profile) => ({
        ...profile,
        badge: profile.badge === 'Active' ? 'Saved' : profile.badge,
      }));
      return [
        ...updated,
        {
          id: `${nextProfileKey}-${version}`,
          profileKey: nextProfileKey,
          name: trimmedName,
          badge: 'Active',
          description: `Saved screening rules (Version ${nextVersionNumber})`,
          version,
          versionNumber: nextVersionNumber,
          snapshot,
        },
      ];
    });
    setSelectedProfileName(`${trimmedName} - ${version}`);
    return { saved: true, version };
  };

  const deleteVersion = (versionId) => {
    const target = versionHistory.find(
      (item) => item.id === versionId || item.version === versionId
    );
    if (!target) return false;

    const remainingHistory = versionHistory.filter((item) => item.id !== target.id);
    const profileVersions = remainingHistory
      .filter((item) => item.profileKey === target.profileKey)
      .sort((left, right) => (right.versionNumber || 0) - (left.versionNumber || 0));
    const replacement = profileVersions.find((item) => item.isCurrent) || profileVersions[0];

    setVersionHistory(remainingHistory.map((item) => ({
      ...item,
      isCurrent: item.profileKey === target.profileKey
        ? Boolean(replacement && item.id === replacement.id)
        : item.isCurrent,
    })));
    setProfiles((prev) => {
      const remainingProfiles = prev.filter((profile) => profile.id !== target.id);
      if (!replacement) {
        return remainingProfiles;
      }
      return remainingProfiles.map((profile) => (
        profile.profileKey === target.profileKey
          ? {
              ...profile,
              badge: profile.id === replacement.id ? 'Active' : 'Saved',
            }
          : profile
      ));
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
