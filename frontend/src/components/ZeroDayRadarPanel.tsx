import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Award,
  Check,
  Copy,
  Download,
  EyeOff,
  Loader2,
  RefreshCw,
  Share2,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { api } from '../services/api';
import { useLanguage } from '../i18n/LanguageContext';
import type { MapKey, ZeroDayChampionEntry, ZeroDayRadarResponse } from '../types/api';
import { ItemIcon } from './ItemIcon';
import { buildZeroDayShareText, downloadZeroDayCardPng } from '../utils/socialCardRenderer';

interface ZeroDayRadarPanelProps {
  latestVersion: string | null;
  selectedMap: MapKey;
  onChangeMap: (gameMap: MapKey) => void;
  targetProfile: 'squishy' | 'bruiser' | 'tank';
  onChangeTarget: (profile: 'squishy' | 'bruiser' | 'tank') => void;
  onOpenChampionInAiLab: (championKey: string) => void;
}

type RadarSubtab = 'myths' | 'hidden' | 'leaders' | 'studio';

function formatSigned(val: number): string {
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
}

export function ZeroDayRadarPanel({
  latestVersion,
  selectedMap,
  onChangeMap,
  targetProfile,
  onChangeTarget,
  onOpenChampionInAiLab,
}: ZeroDayRadarPanelProps) {
  const { locale, localeInfo, t } = useLanguage();

  const queryKey = `${locale}:${latestVersion ?? 'latest'}:${selectedMap}:${targetProfile}`;
  const [radarCache, setRadarCache] = useState<{ key: string; res: ZeroDayRadarResponse } | null>(null);
  const [errorState, setErrorState] = useState<{ key: string; msg: string } | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [subtab, setSubtab] = useState<RadarSubtab>('myths');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const activeRes = radarCache?.key === queryKey ? radarCache.res : null;
  const activeError = errorState?.key === queryKey ? errorState.msg : null;
  const isLoading = !activeRes && !activeError;
  const isCopied = copiedKey === queryKey;

  useEffect(() => {
    if (radarCache?.key === queryKey) return;
    let cancelled = false;
    api
      .getZeroDayRadar({
        to_version: latestVersion,
        target_profile: targetProfile,
        game_map: selectedMap,
        limit: 8,
        lang: locale,
      })
      .then((res) => {
        if (cancelled) return;
        setErrorState(null);
        setRadarCache({ key: queryKey, res });
      })
      .catch((err) => {
        if (cancelled) return;
        setErrorState({
          key: queryKey,
          msg: err instanceof Error ? err.message : String(err),
        });
      });

    return () => {
      cancelled = true;
    };
  }, [queryKey, radarCache, latestVersion, targetProfile, selectedMap, locale]);

  const handleRefresh = async () => {
    setErrorState(null);
    setIsRefreshing(true);
    try {
      const res = await api.getZeroDayRadar({
        to_version: latestVersion,
        target_profile: targetProfile,
        game_map: selectedMap,
        limit: 8,
        lang: locale,
      });
      setRadarCache({ key: queryKey, res });
    } catch (err) {
      setErrorState({
        key: queryKey,
        msg: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleCopyShareText = async () => {
    if (!activeRes) return;
    const text = buildZeroDayShareText(activeRes.radar, t);
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopiedKey(queryKey);
    window.setTimeout(() => {
      setCopiedKey((prev) => (prev === queryKey ? null : prev));
    }, 2500);
  };

  const radar = activeRes?.radar ?? null;

  const renderCatalystsAndBuild = (entry: ZeroDayChampionEntry) => (
    <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-3">
        {entry.catalysts.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-slate-400">{t.zeroDayCatalystsLabel}:</span>
            {entry.catalysts.map((cat) => (
              <span
                key={`${cat.entity_type}-${cat.entity_key}`}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                  cat.direction === 'BUFF'
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                    : cat.direction === 'NERF'
                      ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                      : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                }`}
              >
                {cat.icon_url && <ItemIcon iconUrl={cat.icon_url} name={cat.entity_name} size="sm" />}
                {cat.entity_name}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-1">
          <span className="text-[11px] text-slate-500 mr-1">{t.zeroDayCoreBuildLabel}:</span>
          {entry.core_items.slice(0, 6).map((item) => (
            <ItemIcon
              key={item.item_id}
              iconUrl={item.icon_url}
              name={item.name}
              gold={item.gold_total}
              size="sm"
              highlight={item.is_boot ? 'boot' : 'default'}
            />
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={() => onOpenChampionInAiLab(entry.champion_key)}
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 transition cursor-pointer"
      >
        {t.zeroDayOpenAiLabBtn} <ArrowRight className="w-3 h-3" />
      </button>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-5 space-y-4">
        {/* Header Row */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-bold text-slate-100">{t.zeroDayTitle}</h2>
              {radar && (
                <span className="px-2 py-0.5 rounded-full text-[11px] font-mono bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  LoL {radar.from_display_version} → {radar.to_display_version}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">{t.zeroDaySubtitle}</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {activeRes && (
              <span className="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-950 border border-slate-800 text-slate-400">
                {activeRes.cached ? t.fastCacheBadge : `${radar?.scan_duration_ms ?? 0}ms`}
              </span>
            )}
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isLoading || isRefreshing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              {t.zeroDayRefreshBtn}
            </button>
          </div>
        </div>

        {/* Map & Target Profile Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-slate-400 mr-1">{t.mapModeLabel}:</span>
            {(
              [
                { key: 'sr', label: t.mapSr },
                { key: 'aram', label: t.mapAram },
                { key: 'swiftplay', label: t.mapSwiftplay },
              ] as const
            ).map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => onChangeMap(opt.key)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold border transition cursor-pointer ${
                  selectedMap === opt.key
                    ? 'bg-cyan-500/20 text-cyan-200 border-cyan-500/50'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-slate-400 mr-1">{t.targetEnemyLabel}:</span>
            {(
              [
                { key: 'squishy', label: t.targetSquishy },
                { key: 'bruiser', label: t.targetBruiser },
                { key: 'tank', label: t.targetTank },
              ] as const
            ).map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => onChangeTarget(opt.key)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold border transition cursor-pointer ${
                  targetProfile === opt.key
                    ? 'bg-purple-500/20 text-purple-200 border-purple-500/50'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Loading & Error */}
        {isLoading && (
          <div className="rounded-lg bg-slate-950/70 border border-slate-800 p-8 flex items-center justify-center gap-2.5 text-sm text-slate-300">
            <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
            {t.zeroDayScanningMsg}
          </div>
        )}

        {activeError && (
          <div className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 text-xs text-rose-300">
            {activeError}
          </div>
        )}

        {/* Loaded Radar Content */}
        {radar && (
          <>
            {/* 4 KPI Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="rounded-lg bg-slate-950 border border-slate-800 p-3">
                <div className="text-[11px] text-slate-400">{t.zeroDayStatScanned}</div>
                <div className="text-xl font-bold font-mono text-slate-100 mt-0.5">
                  {radar.champions_scanned}
                </div>
              </div>
              <div className="rounded-lg bg-slate-950 border border-purple-500/30 p-3">
                <div className="text-[11px] text-purple-300">{t.zeroDayStatMyths}</div>
                <div className="text-xl font-bold font-mono text-purple-200 mt-0.5">
                  {radar.summary_counts.myths_busted}
                </div>
              </div>
              <div className="rounded-lg bg-slate-950 border border-emerald-500/30 p-3">
                <div className="text-[11px] text-emerald-300">{t.zeroDayStatHiddenWinners}</div>
                <div className="text-xl font-bold font-mono text-emerald-300 mt-0.5">
                  {radar.summary_counts.hidden_winners}
                </div>
              </div>
              <div className="rounded-lg bg-slate-950 border border-rose-500/30 p-3">
                <div className="text-[11px] text-rose-300">{t.zeroDayStatHiddenLosers}</div>
                <div className="text-xl font-bold font-mono text-rose-300 mt-0.5">
                  {radar.summary_counts.hidden_losers}
                </div>
              </div>
            </div>

            {/* Sub-tab Navigation */}
            <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
              {(
                [
                  { id: 'myths', label: t.zeroDaySubtabMyths, icon: ShieldAlert },
                  { id: 'hidden', label: t.zeroDaySubtabHidden, icon: EyeOff },
                  { id: 'leaders', label: t.zeroDaySubtabLeaders, icon: Award },
                  { id: 'studio', label: t.zeroDaySubtabStudio, icon: Share2 },
                ] as const
              ).map((item) => {
                const Icon = item.icon;
                const active = subtab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSubtab(item.id)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                      active
                        ? 'bg-amber-500/20 text-amber-200 border-amber-500/50'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {item.label}
                  </button>
                );
              })}
            </div>

            {/* Subtab 1: Patch Mythbusters */}
            {subtab === 'myths' && (
              <div className="grid grid-cols-1 gap-3">
                {radar.mythbusters.map((entry) => {
                  const busted = Boolean(entry.is_myth_busted);
                  return (
                    <div
                      key={entry.champion_key}
                      className={`rounded-lg bg-slate-950/90 border p-4 ${
                        busted ? 'border-amber-500/40' : 'border-slate-800'
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-base font-bold text-slate-100">
                              {entry.champion_name}
                            </span>
                            <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                              {entry.role_label} · {entry.kit_archetype_label}
                            </span>
                            {entry.official_direction && (
                              <span
                                className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                                  entry.official_direction === 'BUFF'
                                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                                    : entry.official_direction === 'NERF'
                                      ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                                      : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                                }`}
                              >
                                {t.zeroDayOfficialLabel} {entry.official_direction}
                              </span>
                            )}
                            <span
                              className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded border ${
                                busted
                                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                                  : 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                              }`}
                            >
                              {busted ? (
                                <AlertTriangle className="w-3 h-3" />
                              ) : (
                                <Check className="w-3 h-3" />
                              )}
                              {busted ? t.zeroDayMythBustedBadge : t.zeroDayMathVerifiedBadge}
                            </span>
                          </div>
                          {entry.verdict_label && (
                            <div className="text-sm font-semibold text-amber-200 mt-2">
                              {entry.verdict_label}
                            </div>
                          )}
                          {entry.verdict_summary && (
                            <p className="text-xs text-slate-400 mt-0.5">{entry.verdict_summary}</p>
                          )}
                        </div>

                        <div className="text-right">
                          <div className="text-[11px] text-slate-400">{t.zeroDayNetShiftLabel}</div>
                          <div
                            className={`text-xl font-bold font-mono ${
                              entry.power_shift_score > 0
                                ? 'text-emerald-400'
                                : entry.power_shift_score < 0
                                  ? 'text-rose-400'
                                  : 'text-slate-300'
                            }`}
                          >
                            {formatSigned(entry.power_shift_score)}
                          </div>
                          <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                            Burst {formatSigned(entry.burst_delta_pct)} · DPS{' '}
                            {formatSigned(entry.dps_delta_pct)}
                          </div>
                        </div>
                      </div>
                      {renderCatalystsAndBuild(entry)}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Subtab 2: Hidden Winners & Losers */}
            {subtab === 'hidden' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Hidden Winners */}
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2 text-sm font-bold text-emerald-300">
                    <TrendingUp className="w-4 h-4" />
                    {t.zeroDayStatHiddenWinners} ({radar.summary_counts.hidden_winners})
                  </div>
                  {radar.hidden_winners.length === 0 ? (
                    <div className="rounded-lg bg-slate-950 border border-slate-800 p-4 text-xs text-slate-400">
                      {t.zeroDayEmptyHiddenWinners}
                    </div>
                  ) : (
                    radar.hidden_winners.map((entry) => (
                      <div
                        key={entry.champion_key}
                        className="rounded-lg bg-slate-950 border border-emerald-500/30 p-3.5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-100">{entry.champion_name}</span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                                {t.zeroDayUnlistedBadge}
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5">
                              {entry.role_label} · {entry.kit_archetype_label}
                            </div>
                          </div>
                          <span className="text-lg font-bold font-mono text-emerald-400">
                            {formatSigned(entry.power_shift_score)}
                          </span>
                        </div>
                        {renderCatalystsAndBuild(entry)}
                      </div>
                    ))
                  )}
                </div>

                {/* Hidden Losers */}
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2 text-sm font-bold text-rose-300">
                    <TrendingDown className="w-4 h-4" />
                    {t.zeroDayStatHiddenLosers} ({radar.summary_counts.hidden_losers})
                  </div>
                  {radar.hidden_losers.length === 0 ? (
                    <div className="rounded-lg bg-slate-950 border border-slate-800 p-4 text-xs text-slate-400">
                      {t.zeroDayEmptyHiddenLosers}
                    </div>
                  ) : (
                    radar.hidden_losers.map((entry) => (
                      <div
                        key={entry.champion_key}
                        className="rounded-lg bg-slate-950 border border-rose-500/30 p-3.5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-100">{entry.champion_name}</span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                                {t.zeroDayUnlistedBadge}
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5">
                              {entry.role_label} · {entry.kit_archetype_label}
                            </div>
                          </div>
                          <span className="text-lg font-bold font-mono text-rose-400">
                            {formatSigned(entry.power_shift_score)}
                          </span>
                        </div>
                        {renderCatalystsAndBuild(entry)}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Subtab 3: Day-0 Leaderboard */}
            {subtab === 'leaders' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="rounded-lg bg-slate-950 border border-slate-800 p-4 space-y-2.5">
                  <h3 className="text-sm font-bold text-emerald-300 flex items-center gap-1.5">
                    <TrendingUp className="w-4 h-4" /> {t.zeroDayTopWinnersTitle}
                  </h3>
                  {radar.top_winners.map((entry, idx) => (
                    <div
                      key={entry.champion_key}
                      className="flex items-center justify-between gap-2 py-2 border-b border-slate-800/70 last:border-b-0"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="w-5 text-xs font-mono text-slate-500">#{idx + 1}</span>
                        <div>
                          <div className="text-sm font-semibold text-slate-100">
                            {entry.champion_name}
                          </div>
                          <div className="text-[11px] text-slate-400">
                            {entry.role_label} · Burst {formatSigned(entry.burst_delta_pct)} · DPS{' '}
                            {formatSigned(entry.dps_delta_pct)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold font-mono text-emerald-400">
                          {formatSigned(entry.power_shift_score)}
                        </span>
                        <button
                          type="button"
                          onClick={() => onOpenChampionInAiLab(entry.champion_key)}
                          className="text-[11px] px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-slate-700 cursor-pointer"
                        >
                          {t.zeroDayOpenAiLabBtn}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg bg-slate-950 border border-slate-800 p-4 space-y-2.5">
                  <h3 className="text-sm font-bold text-rose-300 flex items-center gap-1.5">
                    <TrendingDown className="w-4 h-4" /> {t.zeroDayTopLosersTitle}
                  </h3>
                  {radar.top_losers.map((entry, idx) => (
                    <div
                      key={entry.champion_key}
                      className="flex items-center justify-between gap-2 py-2 border-b border-slate-800/70 last:border-b-0"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="w-5 text-xs font-mono text-slate-500">#{idx + 1}</span>
                        <div>
                          <div className="text-sm font-semibold text-slate-100">
                            {entry.champion_name}
                          </div>
                          <div className="text-[11px] text-slate-400">
                            {entry.role_label} · Burst {formatSigned(entry.burst_delta_pct)} · DPS{' '}
                            {formatSigned(entry.dps_delta_pct)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold font-mono text-rose-400">
                          {formatSigned(entry.power_shift_score)}
                        </span>
                        <button
                          type="button"
                          onClick={() => onOpenChampionInAiLab(entry.champion_key)}
                          className="text-[11px] px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-slate-700 cursor-pointer"
                        >
                          {t.zeroDayOpenAiLabBtn}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Subtab 4: Viral Social Card Studio */}
            {subtab === 'studio' && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">{t.zeroDayStudioHeading}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{t.zeroDayStudioDesc}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        downloadZeroDayCardPng(radar, t, locale, localeInfo.dir)
                      }
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 border border-cyan-500/50 transition cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      {t.zeroDayDownloadPngBtn}
                    </button>
                    <button
                      type="button"
                      onClick={handleCopyShareText}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-purple-500/20 hover:bg-purple-500/30 text-purple-200 border border-purple-500/50 transition cursor-pointer"
                    >
                      {isCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      {isCopied ? t.zeroDayCopiedMsg : t.zeroDayCopyPostBtn}
                    </button>
                  </div>
                </div>

                {/* Live Visual Social Card Preview */}
                <div className="rounded-2xl bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 border border-cyan-500/30 p-6 shadow-xl space-y-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="px-3 py-1 rounded-full text-[11px] font-bold tracking-wider uppercase bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                      PatchDiff Sandbox · Zero-Vanguard Math Engine
                    </span>
                    <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-purple-500/20 text-purple-200 border border-purple-500/40">
                      {radar.share_card.patch_transition}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-xl font-extrabold text-slate-50">
                      {radar.share_card.headline}
                    </h4>
                    <p className="text-xs text-slate-400 mt-1">{radar.share_card.subtitle}</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Spotlight 1: Top Winner */}
                    <div className="rounded-xl bg-slate-950/85 border border-emerald-500/40 p-4 space-y-1.5">
                      <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-400">
                        {t.zeroDayCardBestWinner}
                      </div>
                      {radar.share_card.top_winner ? (
                        <>
                          <div className="text-lg font-extrabold text-slate-100">
                            {radar.share_card.top_winner.champion_name}
                          </div>
                          <div className="text-2xl font-extrabold font-mono text-emerald-400">
                            {formatSigned(radar.share_card.top_winner.power_shift_score)}
                          </div>
                          <div className="text-xs text-slate-400">
                            {radar.share_card.top_winner.role_label} ·{' '}
                            {radar.share_card.top_winner.kit_archetype_label}
                          </div>
                        </>
                      ) : (
                        <div className="text-xs text-slate-500">-</div>
                      )}
                    </div>

                    {/* Spotlight 2: Top Hidden Mover */}
                    <div className="rounded-xl bg-slate-950/85 border border-amber-500/40 p-4 space-y-1.5">
                      <div className="text-[11px] font-bold uppercase tracking-wide text-amber-400">
                        {t.zeroDayCardHiddenMover}
                      </div>
                      {radar.share_card.top_hidden_mover ? (
                        <>
                          <div className="text-lg font-extrabold text-slate-100">
                            {radar.share_card.top_hidden_mover.champion_name}
                          </div>
                          <div
                            className={`text-2xl font-extrabold font-mono ${
                              radar.share_card.top_hidden_mover.power_shift_score >= 0
                                ? 'text-emerald-400'
                                : 'text-rose-400'
                            }`}
                          >
                            {formatSigned(radar.share_card.top_hidden_mover.power_shift_score)}
                          </div>
                          <div className="text-xs text-slate-400">
                            {t.zeroDayCatalystsLabel}:{' '}
                            {radar.share_card.top_hidden_mover.catalysts
                              .map((c) => c.entity_name)
                              .join(', ') || '-'}
                          </div>
                        </>
                      ) : (
                        <div className="text-xs text-slate-500">{t.zeroDayEmptyHiddenLosers}</div>
                      )}
                    </div>

                    {/* Spotlight 3: Top Myth Busted */}
                    <div className="rounded-xl bg-slate-950/85 border border-purple-500/40 p-4 space-y-1.5">
                      <div className="text-[11px] font-bold uppercase tracking-wide text-purple-300">
                        {t.zeroDayCardTopMyth}
                      </div>
                      {radar.share_card.top_myth ? (
                        <>
                          <div className="text-lg font-extrabold text-slate-100">
                            {radar.share_card.top_myth.champion_name}
                          </div>
                          <div
                            className={`text-2xl font-extrabold font-mono ${
                              radar.share_card.top_myth.power_shift_score >= 0
                                ? 'text-emerald-400'
                                : 'text-rose-400'
                            }`}
                          >
                            {formatSigned(radar.share_card.top_myth.power_shift_score)}
                          </div>
                          <div className="text-xs text-slate-300">
                            {radar.share_card.top_myth.verdict_label}
                          </div>
                        </>
                      ) : (
                        <div className="text-xs text-slate-500">-</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
