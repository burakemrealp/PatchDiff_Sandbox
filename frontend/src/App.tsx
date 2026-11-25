import { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import { Activity, Brain, CloudDownload, FileText, Loader2, Sparkles, Swords } from 'lucide-react';
import { api } from './services/api';
import { useLanguage } from './i18n/LanguageContext';
import type {
  AutoChampionDiffEntry,
  AutoItemDiffEntry,
  AutoRuneDiffEntry,
  ChampionPatchDiff,
  ChampionSummary,
  GameStateKey,
  HealthResponse,
  ItemSummary,
  LatestPatchInfo,
  LatestPatchResponse,
  MapKey,
  PatchDiffsResponse,
  RecommendBuildsResponse,
  RecommendedVariation,
  RoleKey,
  SimulateResponse,
} from './types/api';
import { AIBuildLab } from './components/AIBuildLab';
import { DiffCardList } from './components/DiffCardList';
import { SimulationControls } from './components/SimulationControls';
import { LanguageSelector } from './components/LanguageSelector';

const ZeroDayRadarPanel = lazy(() =>
  import('./components/ZeroDayRadarPanel').then((m) => ({ default: m.ZeroDayRadarPanel }))
);
const AutoPatchPanel = lazy(() =>
  import('./components/AutoPatchPanel').then((m) => ({ default: m.AutoPatchPanel }))
);
const PatchInputPanel = lazy(() =>
  import('./components/PatchInputPanel').then((m) => ({ default: m.PatchInputPanel }))
);
const SimulationCharts = lazy(() =>
  import('./components/SimulationCharts').then((m) => ({ default: m.SimulationCharts }))
);

type SourceMode = 'ai-lab' | 'zero-day' | 'auto' | 'manual';

interface AutoPatchBundle {
  latestRes: LatestPatchResponse;
  diffsRes: PatchDiffsResponse | null;
}

async function fetchLatestAutoPatchBundle(activeLocale: string): Promise<AutoPatchBundle> {
  const latestRes = await api.getLatestPatch();
  if (latestRes.synced && latestRes.patch) {
    const diffsRes = await api.getPatchDiffs(latestRes.patch.version, activeLocale);
    return { latestRes, diffsRes };
  }
  return { latestRes, diffsRes: null };
}

export default function App() {
  const { locale, t } = useLanguage();

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [champions, setChampions] = useState<ChampionSummary[]>([]);
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sourceMode, setSourceMode] = useState<SourceMode>('ai-lab');

  const [latestPatch, setLatestPatch] = useState<LatestPatchInfo | null>(null);
  const [autoChampions, setAutoChampions] = useState<AutoChampionDiffEntry[]>([]);
  const [autoItems, setAutoItems] = useState<AutoItemDiffEntry[]>([]);
  const [autoRunes, setAutoRunes] = useState<AutoRuneDiffEntry[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);

  const [labChampKey, setLabChampKey] = useState<string>('');
  const [selectedRole, setSelectedRole] = useState<RoleKey | ''>('');
  const [selectedMap, setSelectedMap] = useState<MapKey>('sr');
  const [gameState, setGameState] = useState<GameStateKey>('even');
  const [isGeneratingBuilds, setIsGeneratingBuilds] = useState(false);

  // Locale-scoped states automatically clear previous-language outputs on language switch
  const [syncNoticeState, setSyncNoticeState] = useState<{ locale: string; text: string } | null>(null);
  const [recommendState, setRecommendState] = useState<{ locale: string; data: RecommendBuildsResponse } | null>(null);
  const [simState, setSimState] = useState<{ locale: string; data: SimulateResponse } | null>(null);

  const syncNotice = syncNoticeState?.locale === locale ? syncNoticeState.text : null;
  const recommendResponse = recommendState?.locale === locale ? recommendState.data : null;
  const simResponse = simState?.locale === locale ? simState.data : null;

  const [rawText, setRawText] = useState('');
  const [patchVersion, setPatchVersion] = useState('26.23');
  const [isParsing, setIsParsing] = useState(false);
  const [parsedChampions, setParsedChampions] = useState<ChampionPatchDiff[]>([]);
  const [sanityWarnings, setSanityWarnings] = useState<string[]>([]);
  const [parseMeta, setParseMeta] = useState<{ engine: string; latencyMs: number } | null>(null);
  const [activeFromVersion, setActiveFromVersion] = useState<string | null>(null);
  const [selectedChampKey, setSelectedChampKey] = useState<string>('');

  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([]);
  const [selectedKeystoneKey, setSelectedKeystoneKey] = useState<string | null>(null);
  const [targetProfile, setTargetProfile] = useState<'squishy' | 'bruiser' | 'tank'>('squishy');
  const [isSimulating, setIsSimulating] = useState(false);

  const applyLatestAutoPatchBundle = useCallback((bundle: AutoPatchBundle) => {
    const { latestRes, diffsRes } = bundle;
    setLatestPatch(latestRes.patch);
    if (latestRes.synced && latestRes.patch && diffsRes) {
      const dispVer = latestRes.patch.display_version || latestRes.patch.version;
      setPatchVersion(dispVer);
      setAutoChampions(diffsRes.champions);
      setAutoItems(diffsRes.items);
      setAutoRunes(diffsRes.runes ?? []);
      setParsedChampions(diffsRes.champions.map((c) => c.diff));
      setActiveFromVersion(diffsRes.from_version);
      setSanityWarnings([]);
      const fromDisp = diffsRes.from_display_version || diffsRes.from_version || '?';
      const toDisp = diffsRes.to_display_version || diffsRes.to_version;
      setParseMeta({
        engine: `auto-diff (${fromDisp} -> ${toDisp})`,
        latencyMs: 0,
      });
      if (diffsRes.champions.length > 0) {
        setSelectedChampKey((prev) => prev || diffsRes.champions[0].entity_key);
        setLabChampKey((prev) => prev || diffsRes.champions[0].entity_key);
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.getHealth(),
      api.getChampions(locale),
      api.getItems(locale),
      fetchLatestAutoPatchBundle(locale),
    ])
      .then(([h, c, i, patchBundle]) => {
        if (cancelled) return;
        setHealth(h);
        setChampions(c);
        setItems(i);
        applyLatestAutoPatchBundle(patchBundle);
        if (c.length > 0) {
          setLabChampKey((prev) => prev || c[0].key);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [locale, applyLatestAutoPatchBundle]);

  const handleSyncPatches = async (force = false) => {
    setError(null);
    setSyncNoticeState(null);
    setIsSyncing(true);
    try {
      const res = await api.syncPatches(force);
      const disp = latestPatch?.display_version || res.latest_version;
      if (res.status === 'up_to_date') {
        setSyncNoticeState({ locale, text: `${t.syncUpToDate} (${disp}).` });
      } else if (res.status === 'synced') {
        setSyncNoticeState({
          locale,
          text: `${t.syncSuccess} (${res.champions_changed ?? 0} ${t.championsUnit}, ${res.items_changed ?? 0} ${t.itemsUnit}).`,
        });
      } else if (res.message) {
        setSyncNoticeState({ locale, text: res.message });
      }
      const [updatedChamps, updatedItems, patchBundle] = await Promise.all([
        api.getChampions(locale),
        api.getItems(locale),
        fetchLatestAutoPatchBundle(locale),
      ]);
      setChampions(updatedChamps);
      setItems(updatedItems);
      applyLatestAutoPatchBundle(patchBundle);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.syncError);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleGenerateRecommendations = async (overrideState?: GameStateKey) => {
    if (!labChampKey) return;
    const activeState = overrideState ?? gameState;
    setError(null);
    setIsGeneratingBuilds(true);
    try {
      const res = await api.recommendBuilds({
        champion_key: labChampKey,
        target_profile: targetProfile,
        role: selectedRole || null,
        game_map: selectedMap,
        game_state: activeState,
        to_version: latestPatch?.version ?? null,
        use_ai: true,
        lang: locale,
      });
      setRecommendState({ locale, data: res });
    } catch (err) {
      setError(err instanceof Error ? err.message : t.aiBuildError);
    } finally {
      setIsGeneratingBuilds(false);
    }
  };

  const handleApplyVariationToSimulator = async (
    variation: RecommendedVariation,
    champKey: string,
    role: RoleKey,
    gameMap: MapKey
  ) => {
    const itemIds = variation.items.map((i) => i.item_id);
    setSelectedItemIds(itemIds);
    setSelectedKeystoneKey(variation.keystone.key);
    setError(null);
    setIsSimulating(true);

    const matchingAuto = autoChampions.find((c) => c.entity_key === champKey);
    try {
      const res = await api.simulate({
        champion_key: champKey,
        item_ids: itemIds,
        target_profile: targetProfile,
        patch_diff: matchingAuto ? matchingAuto.diff : null,
        from_version: matchingAuto ? latestPatch?.previous_version ?? null : null,
        keystone_key: variation.keystone.key,
        role,
        game_map: gameMap,
        lang: locale,
        raw_patch_text: `AI Lab Simulation (${variation.playstyle} / ${variation.keystone.key} / ${role} / ${gameMap})`,
      });
      setSimState({ locale, data: res });
    } catch (err) {
      setError(err instanceof Error ? err.message : t.simError);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSwitchMode = (mode: SourceMode) => {
    setSourceMode(mode);
    setSimState(null);
    setSelectedKeystoneKey(null);
    setError(null);
    if (mode === 'auto' && autoChampions.length > 0) {
      setParsedChampions(autoChampions.map((c) => c.diff));
      setActiveFromVersion(latestPatch?.previous_version ?? null);
      setSelectedChampKey(autoChampions[0].entity_key);
      setSanityWarnings([]);
      const fromDisp = latestPatch?.previous_display_version || latestPatch?.previous_version || '?';
      const toDisp = latestPatch?.display_version || latestPatch?.version || '?';
      setParseMeta({
        engine: `auto-diff (${fromDisp} -> ${toDisp})`,
        latencyMs: 0,
      });
    } else if (mode === 'manual') {
      setActiveFromVersion(null);
      setParsedChampions([]);
      setSelectedChampKey('');
      setParseMeta(null);
    }
  };

  const handleParse = async () => {
    setError(null);
    setIsParsing(true);
    setSimState(null);
    setParseMeta(null);
    setActiveFromVersion(null);
    try {
      const res = await api.parsePatch(rawText, patchVersion);
      setParsedChampions(res.payload.champions);
      setSanityWarnings(res.sanity_warnings);
      setParseMeta({ engine: res.engine_used, latencyMs: res.latency_ms });
      if (res.payload.champions.length > 0) {
        setSelectedChampKey(res.payload.champions[0].champion_key);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t.parseError);
    } finally {
      setIsParsing(false);
    }
  };

  const handleToggleItem = (itemId: string) => {
    setSelectedItemIds((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]
    );
  };

  const handleSimulate = async () => {
    const activeDiff = parsedChampions.find((c) => c.champion_key === selectedChampKey) || null;
    if (!activeDiff) return;

    setError(null);
    setIsSimulating(true);
    try {
      const res = await api.simulate({
        champion_key: activeDiff.champion_key,
        item_ids: selectedItemIds,
        target_profile: targetProfile,
        patch_diff: activeDiff,
        from_version: activeFromVersion,
        keystone_key: selectedKeystoneKey,
        game_map: selectedMap,
        lang: locale,
        raw_patch_text:
          sourceMode === 'auto'
            ? `Auto Patch Diff ${activeFromVersion ?? ''} -> ${latestPatch?.version ?? ''}`
            : rawText,
      });
      setSimState({ locale, data: res });
    } catch (err) {
      setError(err instanceof Error ? err.message : t.simError);
    } finally {
      setIsSimulating(false);
    }
  };

  const headerPatchLabel = latestPatch?.display_version || latestPatch?.version;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <Swords className="w-7 h-7 text-cyan-400" />
            <div>
              <h1 className="text-2xl font-bold tracking-tight">PatchDiff Sandbox</h1>
              <p className="text-xs text-slate-400">{t.appSubtitle}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {latestPatch && (
              <span
                title={`Riot API: ${latestPatch.version}`}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
              >
                LoL {headerPatchLabel}
              </span>
            )}
            {health && (
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                <Activity className="w-3.5 h-3.5" />
                {health.status === 'healthy' ? t.systemOnline : t.systemPartial}
              </span>
            )}
            <LanguageSelector />
          </div>
        </header>

        {error && (
          <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
            {error}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => handleSwitchMode('ai-lab')}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold border transition cursor-pointer ${
              sourceMode === 'ai-lab'
                ? 'bg-purple-500/20 text-purple-200 border-purple-500/60'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            <Brain className="w-3.5 h-3.5" /> {t.tabAiLab}
          </button>
          <button
            type="button"
            onClick={() => handleSwitchMode('zero-day')}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold border transition cursor-pointer ${
              sourceMode === 'zero-day'
                ? 'bg-amber-500/20 text-amber-200 border-amber-500/60'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" /> {t.tabZeroDay}
          </button>
          <button
            type="button"
            onClick={() => handleSwitchMode('auto')}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold border transition cursor-pointer ${
              sourceMode === 'auto'
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            <CloudDownload className="w-3.5 h-3.5" /> {t.tabPatchStats}
          </button>
          <button
            type="button"
            onClick={() => handleSwitchMode('manual')}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold border transition cursor-pointer ${
              sourceMode === 'manual'
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" /> {t.tabManualInput}
          </button>
        </div>

        {sourceMode === 'ai-lab' && (
          <AIBuildLab
            champions={champions}
            changedChampions={autoChampions}
            selectedChampionKey={labChampKey}
            onSelectChampion={(key) => {
              setLabChampKey(key);
              setRecommendState(null);
              setSimState(null);
            }}
            selectedRole={selectedRole}
            onChangeRole={(r) => {
              setSelectedRole(r);
              setRecommendState(null);
            }}
            selectedMap={selectedMap}
            onChangeMap={(m) => {
              setSelectedMap(m);
              if (m === 'aram') {
                setSelectedRole('');
              }
              setRecommendState(null);
            }}
            targetProfile={targetProfile}
            onChangeTarget={(p) => {
              setTargetProfile(p);
              setRecommendState(null);
            }}
            gameState={gameState}
            onChangeGameState={(st) => {
              setGameState(st);
              setRecommendState(null);
            }}
            onSelectAndGenerateState={(st) => {
              setGameState(st);
              void handleGenerateRecommendations(st);
            }}
            onGenerate={() => handleGenerateRecommendations()}
            isGenerating={isGeneratingBuilds}
            response={recommendResponse}
            onApplyVariationToSimulator={handleApplyVariationToSimulator}
          />
        )}

        {sourceMode === 'zero-day' && (
          <Suspense
            fallback={
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-8 flex items-center justify-center gap-2 text-xs text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                {t.loadingCharts}
              </div>
            }
          >
            <ZeroDayRadarPanel
              latestVersion={latestPatch?.version ?? null}
              selectedMap={selectedMap}
              onChangeMap={(m) => {
                setSelectedMap(m);
                if (m === 'aram') {
                  setSelectedRole('');
                }
              }}
              targetProfile={targetProfile}
              onChangeTarget={setTargetProfile}
              onOpenChampionInAiLab={(champKey) => {
                setLabChampKey(champKey);
                setRecommendState(null);
                setSimState(null);
                setSourceMode('ai-lab');
              }}
            />
          </Suspense>
        )}

        {sourceMode === 'auto' && (
          <Suspense
            fallback={
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-8 flex items-center justify-center gap-2 text-xs text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                {t.loadingCharts}
              </div>
            }
          >
            <AutoPatchPanel
              latestPatch={latestPatch}
              changedChampions={autoChampions}
              changedItems={autoItems}
              changedRunes={autoRunes}
              selectedChampionKey={selectedChampKey}
              onSelectChampion={(key) => {
                setSelectedChampKey(key);
                setSimState(null);
              }}
              onSync={handleSyncPatches}
              isSyncing={isSyncing}
              syncNotice={syncNotice}
            />
          </Suspense>
        )}

        {sourceMode === 'manual' && (
          <Suspense
            fallback={
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-8 flex items-center justify-center gap-2 text-xs text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                {t.loadingCharts}
              </div>
            }
          >
            <PatchInputPanel
              rawText={rawText}
              setRawText={setRawText}
              patchVersion={patchVersion}
              setPatchVersion={setPatchVersion}
              onParse={handleParse}
              isParsing={isParsing}
            />
          </Suspense>
        )}

        {(sourceMode === 'auto' || sourceMode === 'manual') && (
          <>
            <DiffCardList
              champions={parsedChampions}
              selectedChampionKey={selectedChampKey}
              onSelectChampion={(key) => {
                setSelectedChampKey(key);
                setSimState(null);
              }}
              warnings={sanityWarnings}
              engineUsed={parseMeta?.engine}
              latencyMs={parseMeta?.latencyMs}
            />

            {parsedChampions.length > 0 && (
              <SimulationControls
                items={items}
                selectedItemIds={selectedItemIds}
                onToggleItem={handleToggleItem}
                onClearItems={() => setSelectedItemIds([])}
                targetProfile={targetProfile}
                onChangeTarget={setTargetProfile}
                onSimulate={handleSimulate}
                isSimulating={isSimulating}
                disabled={!selectedChampKey}
              />
            )}
          </>
        )}

        {simResponse && (
          <Suspense
            fallback={
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-8 flex items-center justify-center gap-2 text-xs text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                {t.loadingCharts}
              </div>
            }
          >
            <SimulationCharts simResponse={simResponse} />
          </Suspense>
        )}

        <footer className="mt-10 pt-4 border-t border-slate-800/80 text-center text-[11px] leading-relaxed text-slate-500">
          PatchDiff Sandbox isn&apos;t endorsed by Riot Games and doesn&apos;t
          reflect the views or opinions of Riot Games or anyone officially
          involved in producing or managing Riot Games properties. Riot Games,
          and all associated properties are trademarks or registered trademarks
          of Riot Games, Inc.
        </footer>
      </div>
    </div>
  );
}
