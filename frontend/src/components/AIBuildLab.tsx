import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Compass,
  Cpu,
  Crosshair,
  Flame,
  Gauge,
  Link2,
  Loader2,
  Map,
  Play,
  Search,
  Shield,
  Sparkles,
  Star,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import { useLanguage } from '../i18n/LanguageContext';
import type {
  AutoChampionDiffEntry,
  ChampionSummary,
  FeedbackSummaryResponse,
  GameStateKey,
  MapKey,
  PvELabReport,
  RecommendBuildsResponse,
  RecommendedVariation,
  RoleKey,
} from '../types/api';
import { AramModifiersBar } from './AramModifiersBar';
import { ItemIcon } from './ItemIcon';
import { PivotAndTrapsPanel } from './PivotAndTrapsPanel';
import { PvELabDrawer } from './PvELabDrawer';
import { VariationFeedbackBar } from './VariationFeedbackBar';

interface AIBuildLabProps {
  champions: ChampionSummary[];
  changedChampions: AutoChampionDiffEntry[];
  selectedChampionKey: string;
  onSelectChampion: (key: string) => void;
  selectedRole: RoleKey | '';
  onChangeRole: (role: RoleKey | '') => void;
  selectedMap: MapKey;
  onChangeMap: (map: MapKey) => void;
  targetProfile: 'squishy' | 'bruiser' | 'tank';
  onChangeTarget: (profile: 'squishy' | 'bruiser' | 'tank') => void;
  gameState: GameStateKey;
  onChangeGameState: (state: GameStateKey) => void;
  onSelectAndGenerateState: (state: GameStateKey) => void;
  onGenerate: () => void;
  isGenerating: boolean;
  response: RecommendBuildsResponse | null;
  onApplyVariationToSimulator: (
    variation: RecommendedVariation,
    champKey: string,
    role: RoleKey,
    gameMap: MapKey
  ) => void;
}

export function AIBuildLab({
  champions,
  changedChampions,
  selectedChampionKey,
  onSelectChampion,
  selectedRole,
  onChangeRole,
  selectedMap,
  onChangeMap,
  targetProfile,
  onChangeTarget,
  gameState,
  onChangeGameState,
  onSelectAndGenerateState,
  onGenerate,
  isGenerating,
  response,
  onApplyVariationToSimulator,
}: AIBuildLabProps) {
  const { locale, t } = useLanguage();
  const [champSearch, setChampSearch] = useState('');
  const [feedbackData, setFeedbackData] = useState<{
    key: string;
    summary: FeedbackSummaryResponse;
  } | null>(null);
  const [openPveKey, setOpenPveKey] = useState<string | null>(null);
  const [pveReports, setPveReports] = useState<Record<string, PvELabReport>>({});
  const [pveLoadingKey, setPveLoadingKey] = useState<string | null>(null);
  const [pveErrors, setPveErrors] = useState<Record<string, string>>({});

  const targets: { key: 'squishy' | 'bruiser' | 'tank'; label: string }[] = [
    { key: 'squishy', label: t.targetSquishy },
    { key: 'bruiser', label: t.targetBruiser },
    { key: 'tank', label: t.targetTank },
  ];

  const gameStates: { key: GameStateKey; label: string; hint: string }[] = [
    { key: 'behind', label: t.stateBehind, hint: t.stateBehindHint },
    { key: 'even', label: t.stateEven, hint: t.stateEvenHint },
    { key: 'ahead', label: t.stateAhead, hint: t.stateAheadHint },
  ];

  const roles: { key: RoleKey | ''; label: string; hint: string }[] = [
    { key: '', label: t.roleAuto, hint: t.roleAutoHint },
    { key: 'top', label: t.roleTop, hint: t.roleTopHint },
    { key: 'jungle', label: t.roleJungle, hint: t.roleJungleHint },
    { key: 'mid', label: t.roleMid, hint: t.roleMidHint },
    { key: 'adc', label: t.roleAdc, hint: t.roleAdcHint },
    { key: 'support', label: t.roleSupport, hint: t.roleSupportHint },
  ];

  const maps: { key: MapKey; label: string }[] = [
    { key: 'sr', label: t.mapSr },
    { key: 'aram', label: t.mapAram },
    { key: 'swiftplay', label: t.mapSwiftplay },
  ];

  const dirLabel = (dir: 'BUFF' | 'NERF' | 'ADJUSTMENT') =>
    dir === 'BUFF' ? t.dirBuff : dir === 'NERF' ? t.dirNerf : t.dirAdjustment;

  const shiftLabel = (status: 'GAINED' | 'LOST' | 'STABLE') =>
    status === 'GAINED' ? t.shiftGained : status === 'LOST' ? t.shiftLost : t.shiftStable;

  const playstyleLabel = (style: 'burst' | 'dps' | 'balanced') =>
    style === 'burst' ? t.playstyleBurst : style === 'dps' ? t.playstyleDps : t.playstyleBalanced;

  const renderVerdictBadge = (verdict: 'RECOMMENDED' | 'SITUATIONAL' | 'RISKY') => {
    const styles =
      verdict === 'RECOMMENDED'
        ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
        : verdict === 'SITUATIONAL'
          ? 'bg-amber-500/15 text-amber-300 border-amber-500/40'
          : 'bg-rose-500/15 text-rose-300 border-rose-500/40';

    const label =
      verdict === 'RECOMMENDED'
        ? t.verdictRecommended
        : verdict === 'SITUATIONAL'
          ? t.verdictSituational
          : t.verdictRisky;

    return (
      <span className={`px-2 py-0.5 text-[11px] font-bold rounded border ${styles}`}>{label}</span>
    );
  };

  const renderBootBadge = (slotType?: string) => {
    if (slotType === 'role_quest_boot') {
      return (
        <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
          {t.bootRoleSlot}
        </span>
      );
    }
    if (slotType === 'tier3_boot') {
      return (
        <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-purple-500/20 text-purple-300 border border-purple-500/40">
          {t.bootTier3}
        </span>
      );
    }
    return (
      <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-slate-800 text-slate-300 border border-slate-700">
        {t.bootStandard}
      </span>
    );
  };

  const filteredChampions = useMemo(() => {
    const q = champSearch.trim().toLowerCase();
    if (!q) return champions;
    return champions.filter(
      (c) => c.name.toLowerCase().includes(q) || c.key.toLowerCase().includes(q)
    );
  }, [champions, champSearch]);

  const report = response?.report;
  const reportChampKey = report?.champion_key;
  const reportToVersion = report?.to_version;
  const feedbackKey = reportChampKey ? `${reportChampKey}:${reportToVersion ?? ''}` : '';
  const feedbackSummary =
    feedbackKey && feedbackData?.key === feedbackKey ? feedbackData.summary : null;
  const fromDisp = report?.from_display_version || report?.from_version;
  const toDisp = report?.to_display_version || reportToVersion;

  const refreshFeedbackSummary = useCallback(() => {
    if (!reportChampKey) return;
    const key = `${reportChampKey}:${reportToVersion ?? ''}`;
    api
      .getFeedbackSummary(reportChampKey, reportToVersion)
      .then((summary) => setFeedbackData({ key, summary }))
      .catch(() => setFeedbackData(null));
  }, [reportChampKey, reportToVersion]);

  useEffect(() => {
    if (!reportChampKey) return;
    let cancelled = false;
    const key = `${reportChampKey}:${reportToVersion ?? ''}`;
    api
      .getFeedbackSummary(reportChampKey, reportToVersion)
      .then((summary) => {
        if (!cancelled) setFeedbackData({ key, summary });
      })
      .catch(() => {
        if (!cancelled) setFeedbackData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [reportChampKey, reportToVersion]);

  const handleTogglePveLab = (
    pveKey: string,
    variation: RecommendedVariation,
    champKey: string,
    role: RoleKey,
    gameMap: MapKey,
    stateKey: GameStateKey,
    toVersion?: string
  ) => {
    if (openPveKey === pveKey) {
      setOpenPveKey(null);
      return;
    }
    setOpenPveKey(pveKey);
    if (pveReports[pveKey] || pveLoadingKey === pveKey) {
      return;
    }
    setPveLoadingKey(pveKey);
    setPveErrors((prev) => {
      const next = { ...prev };
      delete next[pveKey];
      return next;
    });
    api
      .runPveLab({
        champion_key: champKey,
        item_ids: variation.items.map((it) => it.item_id),
        keystone_key: variation.keystone.key,
        role,
        game_map: gameMap,
        game_state: stateKey,
        to_version: toVersion ?? null,
        lang: locale,
      })
      .then((res) => {
        setPveReports((prev) => ({ ...prev, [pveKey]: res.report }));
      })
      .catch((err) => {
        setPveErrors((prev) => ({
          ...prev,
          [pveKey]: err instanceof Error ? err.message : String(err),
        }));
      })
      .finally(() => {
        setPveLoadingKey((cur) => (cur === pveKey ? null : cur));
      });
  };

  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            <div>
              <h2 className="text-base font-semibold text-white">{t.aiLabTitle}</h2>
              <p className="text-xs text-slate-400">{t.aiLabSubtitle}</p>
            </div>
          </div>
        </div>

        {changedChampions.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[11px] font-semibold uppercase text-slate-400 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              {t.changedChampsHeading} ({changedChampions.length} {t.quickSelectSuffix})
            </div>
            <div className="flex flex-wrap gap-2">
              {changedChampions.map((c) => {
                const active = c.entity_key === selectedChampionKey;
                return (
                  <button
                    key={c.entity_key}
                    type="button"
                    onClick={() => onSelectChampion(c.entity_key)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                      active
                        ? 'bg-purple-500/20 border-purple-500/60 text-purple-200'
                        : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <span>{c.entity_name}</span>
                    <span
                      className={`text-[10px] font-mono ${
                        c.direction === 'BUFF'
                          ? 'text-emerald-400'
                          : c.direction === 'NERF'
                            ? 'text-rose-400'
                            : 'text-amber-400'
                      }`}
                    >
                      {dirLabel(c.direction)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-slate-400">
              {t.selectChampionLabel} ({champions.length} {t.championsUnit})
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute start-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={champSearch}
                  onChange={(e) => setChampSearch(e.target.value)}
                  placeholder={t.searchChampionPlaceholder}
                  className="w-full ps-8 pe-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
              </div>
              <select
                value={selectedChampionKey}
                onChange={(e) => onSelectChampion(e.target.value)}
                className="px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-700 text-slate-100 focus:outline-none focus:border-purple-500 min-w-44"
              >
                <option value="">{t.selectChampionOption}</option>
                {filteredChampions.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-slate-400 flex items-center gap-1.5">
              <Map className="w-3.5 h-3.5" /> {t.mapModeLabel}
            </label>
            <div className="grid grid-cols-3 gap-2">
              {maps.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => onChangeMap(m.key)}
                  className={`px-2.5 py-2 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                    selectedMap === m.key
                      ? 'bg-cyan-500/20 border-cyan-500/60 text-cyan-200'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
            {selectedMap === 'swiftplay' && (
              <p className="text-[11px] text-cyan-300/90">{t.swiftplayHint}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {selectedMap === 'aram' ? (
            <div className="lg:col-span-2 flex items-center rounded-lg bg-cyan-950/25 border border-cyan-500/30 px-4 py-3 text-xs text-cyan-200/95">
              <div className="space-y-1">
                <div className="font-semibold text-cyan-300">{t.aramBoxTitle}</div>
                <p className="text-slate-300 leading-relaxed">{t.aramBoxDesc}</p>
              </div>
            </div>
          ) : (
            <div className="lg:col-span-2 space-y-2">
              <label className="text-xs font-semibold uppercase text-slate-400 flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" /> {t.roleLabel}
              </label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {roles.map((r) => (
                  <button
                    key={r.key || 'auto'}
                    type="button"
                    onClick={() => onChangeRole(r.key)}
                    className={`px-2 py-1.5 rounded-lg border text-center transition cursor-pointer ${
                      selectedRole === r.key
                        ? 'bg-purple-500/20 border-purple-500/60 text-purple-200'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <div className="text-xs font-semibold">{r.label}</div>
                    <div className="text-[10px] text-slate-400">{r.hint}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-slate-400 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5" /> {t.targetEnemyLabel}
            </label>
            <div className="grid grid-cols-3 gap-2">
              {targets.map((tg) => (
                <button
                  key={tg.key}
                  type="button"
                  onClick={() => onChangeTarget(tg.key)}
                  className={`px-2 py-2.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                    targetProfile === tg.key
                      ? 'bg-purple-500/20 border-purple-500/60 text-purple-200'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tg.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase text-slate-400 flex items-center gap-1.5">
            <Gauge className="w-3.5 h-3.5 text-cyan-400" /> {t.gameStateLabel}
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {gameStates.map((gs) => {
              const active = gameState === gs.key;
              const activeClass =
                gs.key === 'behind'
                  ? 'bg-cyan-500/20 border-cyan-500/60 text-cyan-200'
                  : gs.key === 'ahead'
                    ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-200'
                    : 'bg-purple-500/20 border-purple-500/60 text-purple-200';
              return (
                <button
                  key={gs.key}
                  type="button"
                  onClick={() => onChangeGameState(gs.key)}
                  className={`px-3 py-2 rounded-lg border text-start transition cursor-pointer ${
                    active
                      ? activeClass
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="text-xs font-semibold">{gs.label}</div>
                  <div className="text-[10px] opacity-80">{gs.hint}</div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onGenerate}
            disabled={isGenerating || !selectedChampionKey}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-purple-500 hover:bg-purple-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 transition cursor-pointer"
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Brain className="w-4 h-4" />
            )}
            {isGenerating ? t.generatingBtn : t.generateBtn}
          </button>
        </div>
      </section>

      {response && report && (
        <section className="space-y-4">
          <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-bold text-white">
                  {report.champion_name} — {t.patchWord} {fromDisp} → {toDisp}
                </h3>
                {report.champion_changed_in_patch && (
                  <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                    {t.changedInPatchBadge}
                  </span>
                )}
                {report.game_context && (
                  <span className="px-2 py-0.5 text-[11px] font-mono rounded bg-slate-800 text-slate-200 border border-slate-700">
                    {report.game_context.role_label} · {report.game_context.map_label} ·{' '}
                    {report.game_context.total_item_slots} {t.itemsUnit} · {t.maxLvPrefix}
                    {report.game_context.max_level}
                  </span>
                )}
                {report.profile?.kit_archetype_label && (
                  <span className="px-2 py-0.5 text-[11px] font-medium rounded bg-purple-500/15 text-purple-200 border border-purple-500/30">
                    {report.profile.kit_archetype_label}
                  </span>
                )}
                {feedbackSummary && feedbackSummary.total_count > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold rounded bg-amber-500/15 text-amber-300 border border-amber-500/35">
                    <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                    {feedbackSummary.avg_rating}/5 ({feedbackSummary.total_count} {t.votesUnit})
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-purple-500/15 text-purple-300 border border-purple-500/30">
                  <Cpu className="w-3 h-3" />
                  {response.engine_used}
                  {!response.cached && ` · ${response.latency_ms} ms`}
                </span>
                {response.cached && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                    <Zap className="w-3 h-3" /> {t.fastCacheBadge}
                  </span>
                )}
              </div>
            </div>

            {report.game_context && (
              <div className="text-xs text-cyan-300/90 bg-cyan-500/5 border border-cyan-500/20 rounded-lg px-3 py-2 space-y-1">
                <div>
                  <span className="font-semibold">
                    {report.game_context.role_quests_enabled
                      ? t.activeRoleQuestLabel
                      : t.mapRuleLabel}
                  </span>{' '}
                  {report.game_context.quest_reward}
                </div>
                {(report.profile?.patch_signals?.adaptation_notes ?? []).length > 0 && (
                  <div className="text-emerald-300/90">
                    <span className="font-semibold">{t.patchAdaptationLabel}</span>{' '}
                    {report.profile?.patch_signals?.adaptation_notes?.join(' ')}
                  </div>
                )}
              </div>
            )}

            <AramModifiersBar
              modifiers={report.aram_modifiers ?? report.game_context?.aram_modifiers}
              gameMap={report.game_context?.game_map ?? selectedMap}
            />

            {report.ai_summary && (
              <p className="text-sm text-slate-200 leading-relaxed bg-slate-950/70 border border-slate-800 rounded-lg p-3.5">
                {report.ai_summary}
              </p>
            )}

            {report.old_meta_baseline && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                <span className="font-semibold text-slate-300">
                  {t.oldMetaBaselineLabel} ({fromDisp})
                </span>
                <div className="flex flex-wrap items-center gap-1.5">
                  {report.old_meta_baseline.items.map((bi, bIdx) => (
                    <span
                      key={`${bi.item_id}-${bIdx}`}
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-200"
                    >
                      <ItemIcon
                        iconUrl={bi.icon_url}
                        name={bi.name}
                        gold={bi.gold_total}
                        size="sm"
                      />
                      <span className="text-[11px]">{bi.name}</span>
                    </span>
                  ))}
                </div>
                <span>
                  · {t.runePrefix} {report.old_meta_baseline.keystone.label}
                </span>
                <span className="text-amber-400 font-mono">
                  ({report.old_meta_baseline.total_gold}g)
                </span>
              </div>
            )}
          </div>

          <PivotAndTrapsPanel
            warnings={report.winrate_trap_warnings ?? report.pivot_tree?.winrate_trap_warnings ?? []}
            pivotTree={report.pivot_tree}
            activeGameState={report.game_state ?? gameState}
            isGenerating={isGenerating}
            onSelectAndGenerateState={onSelectAndGenerateState}
          />

          <div className="grid grid-cols-1 gap-5">
            {report.variations.map((v) => {
              const ai = v.ai_review;
              const shift = v.patch_shift;
              const vsMeta = v.vs_old_meta;
              const rp = v.rune_page;
              const resolvedRole: RoleKey = report.game_context?.role ?? 'mid';
              const resolvedMap: MapKey = report.game_context?.game_map ?? 'sr';
              const resolvedState: GameStateKey = report.game_state ?? gameState;
              const pveKey = `${locale}:${report.champion_key}:${report.to_version}:${resolvedRole}:${resolvedMap}:${resolvedState}:${v.playstyle}:${v.rank}`;
              const isPveOpen = openPveKey === pveKey;

              return (
                <div
                  key={`${v.playstyle}-${v.rank}`}
                  className={`rounded-xl bg-slate-900 border p-5 space-y-4 ${
                    v.rank === 1 ? 'border-emerald-500/40' : 'border-slate-800'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-xs font-bold">
                          #{v.rank}
                        </span>
                        <h4 className="text-base font-bold text-white">
                          {ai?.title || playstyleLabel(v.playstyle)}
                        </h4>
                        {ai && renderVerdictBadge(ai.verdict)}
                        {vsMeta?.is_new_meta_discovery && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-bold rounded bg-purple-500/20 text-purple-300 border border-purple-500/40">
                            <Flame className="w-3 h-3" /> {t.newMetaDiscoveryBadge}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400">
                        {t.playstylePrefix}{' '}
                        <span className="text-slate-300">{playstyleLabel(v.playstyle)}</span> ·{' '}
                        <span className="text-slate-200 font-semibold">
                          {v.items.length} {t.itemsUnit}
                        </span>{' '}
                        · {t.totalCostPrefix}{' '}
                        <span className="text-amber-400 font-mono">{v.total_gold}g</span>
                        {vsMeta && vsMeta.gold_diff !== 0 && (
                          <span
                            className={`ms-1 font-mono ${
                              vsMeta.gold_diff < 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            ({vsMeta.gold_diff > 0 ? '+' : ''}
                            {vsMeta.gold_diff} {t.goldUnit} {t.vsOldMetaPrefix})
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {ai && (
                        <div className="text-end">
                          <div className="text-[10px] uppercase text-slate-400">
                            {t.matchFitLabel}
                          </div>
                          <div className="text-lg font-bold font-mono text-emerald-400">
                            {ai.practicality_score}
                            <span className="text-xs text-slate-500">/100</span>
                          </div>
                        </div>
                      )}
                      <button
                        type="button"
                        onClick={() =>
                          handleTogglePveLab(
                            pveKey,
                            v,
                            report.champion_key,
                            resolvedRole,
                            resolvedMap,
                            resolvedState,
                            report.to_version
                          )
                        }
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                          isPveOpen
                            ? 'bg-cyan-500/25 text-cyan-200 border-cyan-400/60'
                            : 'bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border-cyan-500/40'
                        }`}
                      >
                        <Crosshair className="w-3.5 h-3.5" />
                        {isPveOpen ? t.pveLabCloseBtn : t.pveLabOpenBtn}
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          onApplyVariationToSimulator(
                            v,
                            report.champion_key,
                            resolvedRole,
                            resolvedMap
                          )
                        }
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 transition cursor-pointer"
                      >
                        <Play className="w-3.5 h-3.5" /> {t.viewDamageChartBtn}
                      </button>
                    </div>
                  </div>

                  {isPveOpen && (
                    <PvELabDrawer
                      report={pveReports[pveKey] ?? null}
                      isLoading={pveLoadingKey === pveKey}
                      error={pveErrors[pveKey] ?? null}
                    />
                  )}

                  <div className="space-y-1.5">
                    <div className="text-[11px] font-semibold uppercase text-slate-400">
                      {t.buyOrderHeading} ({v.items.length} {t.slotUnit})
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                      {v.items.map((it, idx) => (
                        <div
                          key={`${it.item_id}-${idx}`}
                          className={`flex items-center justify-between gap-2.5 p-2.5 rounded-lg border text-xs ${
                            it.is_boot
                              ? 'bg-cyan-950/30 border-cyan-500/35'
                              : 'bg-slate-950 border-slate-800'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <ItemIcon
                              iconUrl={it.icon_url}
                              name={it.name}
                              gold={it.gold_total}
                              stats={it.stats}
                              size="lg"
                              highlight={it.is_boot ? 'boot' : 'default'}
                            />
                            <div className="min-w-0 space-y-0.5">
                              <div className="font-medium text-slate-100 truncate">
                                <span className="text-slate-500 font-mono me-1.5">
                                  {it.buy_order ?? idx + 1}.
                                </span>
                                {it.name}
                              </div>
                              {it.is_boot && renderBootBadge(it.slot_type)}
                            </div>
                          </div>
                          <span className="text-amber-400 font-mono shrink-0">
                            {it.gold_total}g
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {rp && (
                    <div className="rounded-lg bg-slate-950 border border-slate-800 p-3.5 space-y-3">
                      <div className="text-[11px] font-semibold uppercase text-amber-300/90">
                        {t.fullRunePageHeading}
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                        <div className="space-y-1.5 border-b md:border-b-0 md:border-e border-slate-800 pb-2 md:pb-0 md:pe-3">
                          <div className="text-[11px] font-semibold text-amber-300">
                            {t.primaryTreePrefix} {rp.primary_tree.name}
                          </div>
                          <div className="px-2 py-1 rounded bg-amber-500/15 border border-amber-500/35 text-amber-200 font-semibold">
                            ★ {rp.primary_tree.keystone.name}
                          </div>
                          <div className="space-y-1 ps-1">
                            {rp.primary_tree.runes.map((r) => (
                              <div key={r.key} className="text-slate-300">
                                • {r.name}
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="space-y-1.5 border-b md:border-b-0 md:border-e border-slate-800 pb-2 md:pb-0 md:pe-3">
                          <div className="text-[11px] font-semibold text-cyan-300">
                            {t.secondaryTreePrefix} {rp.secondary_tree.name}
                          </div>
                          <div className="space-y-1 ps-1">
                            {rp.secondary_tree.runes.map((r) => (
                              <div key={r.key} className="text-slate-300">
                                • {r.name}
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <div className="text-[11px] font-semibold text-purple-300">
                            {t.statShardsHeading}
                          </div>
                          <div className="space-y-1">
                            {rp.stat_shards.map((sh) => (
                              <div
                                key={sh.slot}
                                className="text-slate-300 flex justify-between gap-2"
                              >
                                <span className="text-slate-500">{sh.slot}:</span>
                                <span className="font-mono text-[11px] text-slate-200">
                                  {sh.label}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      {ai?.rune_item_synergy && (
                        <div className="pt-2 border-t border-slate-800 flex items-start gap-2 text-xs text-purple-200/90">
                          <Link2 className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
                          <span>
                            <strong className="text-purple-300">{t.runeItemSynergyLabel}</strong>{' '}
                            {ai.rune_item_synergy}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs font-mono">
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[10px] font-sans text-slate-400">
                        {t.metricBurstPrefix} ({t.levelShort}
                        {v.metrics.max_level ?? 18})
                      </div>
                      <div className="text-emerald-400 font-bold">
                        {v.metrics.lvl_max_burst ?? v.metrics.lvl18_burst}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[10px] font-sans text-slate-400">{t.metricDps}</div>
                      <div className="text-cyan-400 font-bold">
                        {v.metrics.lvl_max_dps ?? v.metrics.lvl18_dps}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[10px] font-sans text-slate-400">{t.metricTtk}</div>
                      <div className="text-amber-400 font-bold">
                        {v.metrics.lvl18_ttk_sec} {t.metricSecUnit}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[10px] font-sans text-slate-400">{t.metricEhpAh}</div>
                      <div className="text-slate-200 font-bold">
                        {v.metrics.phys_ehp_lvl11} / {v.metrics.ability_haste}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[10px] font-sans text-slate-400">
                        {t.metricPatchImpact}
                      </div>
                      <div
                        className={`font-bold ${
                          shift.status === 'GAINED'
                            ? 'text-emerald-400'
                            : shift.status === 'LOST'
                              ? 'text-rose-400'
                              : 'text-slate-300'
                        }`}
                      >
                        {shiftLabel(shift.status)} ({shift.lvl18_burst_delta_pct > 0 ? '+' : ''}
                        {shift.lvl18_burst_delta_pct}%)
                      </div>
                    </div>
                  </div>

                  {ai && (
                    <div className="space-y-2.5 pt-2 border-t border-slate-800 text-xs">
                      <p className="text-slate-200 leading-relaxed">{ai.rationale}</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <div className="font-semibold text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> {t.strengthsHeading}
                          </div>
                          {ai.strengths.map((s, idx) => (
                            <p key={idx} className="text-slate-300">
                              • {s}
                            </p>
                          ))}
                        </div>
                        <div className="space-y-1">
                          <div className="font-semibold text-amber-400 flex items-center gap-1">
                            <AlertTriangle className="w-3.5 h-3.5" /> {t.watchoutsHeading}
                          </div>
                          {ai.watchouts.map((w, idx) => (
                            <p key={idx} className="text-slate-300">
                              • {w}
                            </p>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  <VariationFeedbackBar
                    key={`${report.champion_key}-${report.to_version}-${resolvedRole}-${resolvedMap}-${v.playstyle}`}
                    patchVersion={report.to_version}
                    championKey={report.champion_key}
                    role={resolvedRole}
                    gameMap={resolvedMap}
                    targetProfile={report.target_profile}
                    playstyle={v.playstyle}
                    items={v.items}
                    runePage={rp ?? null}
                    onSubmitted={refreshFeedbackSummary}
                  />
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
