import { CloudDownload, Loader2, RefreshCw, Sparkles } from 'lucide-react';
import type {
  AutoChampionDiffEntry,
  AutoItemDiffEntry,
  AutoRuneDiffEntry,
  LatestPatchInfo,
} from '../types/api';
import { ItemIcon } from './ItemIcon';
import { useLanguage } from '../i18n/LanguageContext';

interface AutoPatchPanelProps {
  latestPatch: LatestPatchInfo | null;
  changedChampions: AutoChampionDiffEntry[];
  changedItems: AutoItemDiffEntry[];
  changedRunes?: AutoRuneDiffEntry[];
  selectedChampionKey: string;
  onSelectChampion: (key: string) => void;
  onSync: (force?: boolean) => void;
  isSyncing: boolean;
  syncNotice: string | null;
}

export function AutoPatchPanel({
  latestPatch,
  changedChampions,
  changedItems,
  changedRunes = [],
  selectedChampionKey,
  onSelectChampion,
  onSync,
  isSyncing,
  syncNotice,
}: AutoPatchPanelProps) {
  const { t } = useLanguage();
  const dispVer = latestPatch?.display_version || latestPatch?.version;
  const prevDispVer = latestPatch?.previous_display_version || latestPatch?.previous_version;

  const dirLabel = (dir: 'BUFF' | 'NERF' | 'ADJUSTMENT') =>
    dir === 'BUFF' ? t.dirBuff : dir === 'NERF' ? t.dirNerf : t.dirAdjustment;

  return (
    <section className="rounded-xl bg-slate-900 border border-slate-800 p-3.5 sm:p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CloudDownload className="w-5 h-5 text-cyan-400" />
          <div>
            <h2 className="text-base font-semibold text-white">{t.autoPatchHeading}</h2>
            {latestPatch ? (
              <p className="text-xs text-slate-400" title={`Riot API: ${latestPatch.version}`}>
                {t.activePatchPrefix}{' '}
                <span className="text-cyan-300 font-mono font-semibold">{dispVer}</span>
                {prevDispVer && (
                  <>
                    {' '}
                    ({t.previousPatchPrefix}{' '}
                    <span className="font-mono text-slate-300">{prevDispVer}</span>)
                  </>
                )}{' '}
                · {latestPatch.champions_count} {t.championsUnit} · {latestPatch.items_count}{' '}
                {t.itemsUnit} · {latestPatch.runes_count} {t.runesUnit}
              </p>
            ) : (
              <p className="text-xs text-slate-400">{t.noSyncedPatchMsg}</p>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={() => onSync(false)}
          disabled={isSyncing}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 transition cursor-pointer"
        >
          {isSyncing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          {isSyncing ? t.syncingBtn : t.checkNewPatchBtn}
        </button>
      </div>

      {syncNotice && (
        <div className="px-3 py-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-200 text-xs">
          {syncNotice}
        </div>
      )}

      {changedChampions.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase text-slate-400 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            {t.detectedChampChangesHeading} ({changedChampions.length})
          </div>
          <div className="flex overflow-x-auto no-scrollbar sm:flex-wrap gap-2 pb-1 sm:pb-0">
            {changedChampions.map((entry) => {
              const active = entry.entity_key === selectedChampionKey;
              const badgeStyle =
                entry.direction === 'BUFF'
                  ? 'text-emerald-400'
                  : entry.direction === 'NERF'
                    ? 'text-rose-400'
                    : 'text-amber-400';

              return (
                <button
                  key={entry.entity_key}
                  type="button"
                  onClick={() => onSelectChampion(entry.entity_key)}
                  className={`shrink-0 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                    active
                      ? 'bg-cyan-500/20 border-cyan-500/60 text-white'
                      : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <span>{entry.entity_name}</span>
                  <span className={`text-[10px] font-mono ${badgeStyle}`}>
                    {dirLabel(entry.direction)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        latestPatch && <p className="text-xs text-slate-400">{t.noNumericDiffMsg}</p>
      )}

      {changedItems.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="text-xs font-semibold uppercase text-slate-400">
            {t.changedItemsHeading} ({changedItems.length})
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {changedItems.map((it) => (
              <div
                key={it.entity_key}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs"
              >
                <div className="flex items-center gap-2 shrink-0">
                  <ItemIcon iconUrl={it.icon_url} name={it.entity_name} size="md" />
                  <span
                    className={`text-[10px] font-mono font-bold ${
                      it.direction === 'BUFF'
                        ? 'text-emerald-400'
                        : it.direction === 'NERF'
                          ? 'text-rose-400'
                          : 'text-amber-400'
                    }`}
                  >
                    {dirLabel(it.direction)}
                  </span>
                  <span className="font-medium text-slate-200">{it.entity_name}</span>
                </div>
                <span className="text-slate-300 text-[11px] sm:text-end leading-relaxed">
                  {it.diff.summary}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {changedRunes.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="text-xs font-semibold uppercase text-slate-400">
            {t.changedRunesHeading} ({changedRunes.length})
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {changedRunes.map((rn) => (
              <div
                key={rn.entity_key}
                className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs"
              >
                <span className="font-medium text-slate-200">{rn.entity_name}</span>
                <span className="font-mono text-slate-400 text-[11px]">{rn.diff.summary}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
