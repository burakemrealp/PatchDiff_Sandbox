import { useState } from 'react';
import { AlertTriangle, ArrowRightLeft, Flame, GitBranch, Scale, ShieldAlert } from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';
import type { GameStateKey, PivotTreeReport, WinrateTrapWarning } from '../types/api';
import { ItemIcon } from './ItemIcon';

interface PivotAndTrapsPanelProps {
  warnings?: WinrateTrapWarning[];
  pivotTree?: PivotTreeReport | null;
  activeGameState: GameStateKey;
  isGenerating: boolean;
  onSelectAndGenerateState: (state: GameStateKey) => void;
}

const ORDERED_STATES: GameStateKey[] = ['behind', 'even', 'ahead'];

export function PivotAndTrapsPanel({
  warnings = [],
  pivotTree,
  activeGameState,
  isGenerating,
  onSelectAndGenerateState,
}: PivotAndTrapsPanelProps) {
  const { t } = useLanguage();
  const [mobileStateTab, setMobileStateTab] = useState<GameStateKey | null>(null);

  if (warnings.length === 0 && !pivotTree) {
    return null;
  }

  const shortStateLabels: Record<GameStateKey, string> = {
    behind: t.stateBehind,
    even: t.stateEven,
    ahead: t.stateAhead,
  };
  const activeReportState = pivotTree?.active_game_state || activeGameState;
  const displayedMobileState = mobileStateTab ?? activeReportState;

  return (
    <div className="space-y-4">
      {warnings.length > 0 && (
        <div className="rounded-xl bg-slate-900 border border-amber-500/35 p-3.5 sm:p-5 space-y-3">
          <div className="flex items-start gap-2.5">
            <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-bold text-amber-200">{t.trapSectionTitle}</h3>
              <p className="text-xs text-slate-400">{t.trapSectionSubtitle}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {warnings.map((w) => {
              const alt = w.comeback_alternative;
              const isHigh = w.risk_level === 'HIGH';
              return (
                <div
                  key={`${w.item_id}-${w.trap_code}`}
                  className="rounded-lg bg-slate-950 border border-slate-800 p-3.5 space-y-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <ItemIcon iconUrl={w.icon_url} name={w.item_name} gold={w.gold_total} size="md" />
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-white truncate">{w.item_name}</div>
                        <div className="text-[11px] font-mono text-amber-400">{w.gold_total}g</div>
                      </div>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border shrink-0 ${
                        isHigh
                          ? 'bg-rose-500/15 text-rose-300 border-rose-500/40'
                          : 'bg-amber-500/15 text-amber-300 border-amber-500/40'
                      }`}
                    >
                      {w.risk_label || w.risk_level}
                    </span>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="font-semibold text-amber-300 flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>{w.trap_title}</span>
                    </div>
                    <p className="text-slate-300 leading-relaxed text-[11px]">{w.trap_reason}</p>
                  </div>

                  {alt && (
                    <div className="pt-2 border-t border-slate-800 flex items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[11px] font-semibold text-cyan-300 shrink-0">
                          {t.trapComebackSwapLabel}
                        </span>
                        <ItemIcon iconUrl={alt.icon_url} name={alt.name} gold={alt.gold_total} size="sm" />
                        <span className="text-slate-100 font-medium truncate">{alt.name}</span>
                      </div>
                      {alt.gold_saved > 0 && (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/35 font-mono text-[10px] shrink-0">
                          -{alt.gold_saved}g ({t.trapGoldSavedSuffix})
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {pivotTree && (
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-3.5 sm:p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-start gap-2.5">
              <GitBranch className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-white">{t.pivotSectionTitle}</h3>
                <p className="text-xs text-slate-400">{t.pivotSectionSubtitle}</p>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-purple-500/15 text-purple-200 border border-purple-500/35">
              {pivotTree.active_state_label}
            </span>
          </div>

          <div className="lg:hidden grid grid-cols-3 gap-1.5">
            {ORDERED_STATES.map((stateKey) => {
              const isTabSelected = displayedMobileState === stateKey;
              return (
                <button
                  key={`mob-${stateKey}`}
                  type="button"
                  onClick={() => setMobileStateTab(stateKey)}
                  className={`px-2 py-2 rounded-lg text-xs font-semibold border text-center transition cursor-pointer ${
                    isTabSelected
                      ? 'bg-cyan-500/20 border-cyan-500/60 text-cyan-200'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  {shortStateLabels[stateKey]}
                </button>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            {ORDERED_STATES.map((stateKey) => {
              const node = pivotTree.pivots?.[stateKey];
              if (!node) return null;

              const isActive =
                (pivotTree.active_game_state || activeGameState) === stateKey;
              const isMobileShown = displayedMobileState === stateKey;

              const accentBorder = isActive
                ? stateKey === 'behind'
                  ? 'border-cyan-400/70 bg-cyan-950/20'
                  : stateKey === 'ahead'
                    ? 'border-emerald-400/70 bg-emerald-950/20'
                    : 'border-purple-400/70 bg-purple-950/20'
                : 'border-slate-800 bg-slate-950';

              const StateIcon =
                stateKey === 'behind' ? ArrowRightLeft : stateKey === 'ahead' ? Flame : Scale;

              return (
                <div
                  key={stateKey}
                  className={`rounded-xl border p-3.5 sm:p-4 flex-col justify-between gap-3 ${
                    isMobileShown ? 'flex' : 'hidden lg:flex'
                  } ${accentBorder}`}
                >
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-white">
                        <StateIcon className="w-3.5 h-3.5 text-cyan-300" />
                        {node.state_label}
                      </span>
                      {isActive && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/25 text-purple-200 border border-purple-400/50">
                          {t.pivotActiveBadge}
                        </span>
                      )}
                    </div>

                    <p className="text-[11px] text-slate-300 leading-relaxed min-h-10">
                      {node.tactical_rule}
                    </p>

                    <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                      <span className="text-amber-400 font-bold">{node.total_gold}g</span>
                      {stateKey !== 'even' && (
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                            node.gold_diff_vs_even < 0
                              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/35'
                              : node.gold_diff_vs_even > 0
                                ? 'bg-rose-500/15 text-rose-300 border-rose-500/35'
                                : 'bg-slate-900 text-slate-300 border-slate-700'
                          }`}
                        >
                          {node.gold_diff_vs_even === 0
                            ? t.pivotSameGoldBadge
                            : `${node.gold_diff_vs_even > 0 ? '+' : ''}${node.gold_diff_vs_even}g`}
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {node.items.map((it, idx) => (
                        <ItemIcon
                          key={`${stateKey}-${it.item_id}-${idx}`}
                          iconUrl={it.icon_url}
                          name={it.name}
                          gold={it.gold_total}
                          stats={it.stats}
                          size="md"
                          highlight={it.is_boot ? 'boot' : 'default'}
                        />
                      ))}
                    </div>

                    {node.swapped_in_items.length > 0 && (
                      <div className="space-y-1 pt-1">
                        <div className="text-[10px] uppercase font-semibold text-cyan-300">
                          {t.pivotSwappedInLabel}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {node.swapped_in_items.map((sw) => (
                            <span
                              key={`${stateKey}-swap-${sw.item_id}`}
                              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-[10px] text-slate-200"
                            >
                              <ItemIcon
                                iconUrl={sw.icon_url}
                                name={sw.name}
                                gold={sw.gold_total}
                                size="sm"
                              />
                              <span className="truncate max-w-28">{sw.name}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2 pt-2 border-t border-slate-800/80">
                    <div className="grid grid-cols-3 gap-1.5 text-[11px] font-mono">
                      <div className="p-1.5 rounded bg-slate-900/90 border border-slate-800">
                        <div className="text-[9px] font-sans text-slate-400">
                          {t.levelShort}18 {t.chartTabBurst}
                        </div>
                        <div className="text-emerald-400 font-bold">{node.lvl18_burst}</div>
                      </div>
                      <div className="p-1.5 rounded bg-slate-900/90 border border-slate-800">
                        <div className="text-[9px] font-sans text-slate-400">{t.chartTabDps}</div>
                        <div className="text-cyan-400 font-bold">{node.lvl18_dps}</div>
                      </div>
                      <div className="p-1.5 rounded bg-slate-900/90 border border-slate-800">
                        <div className="text-[9px] font-sans text-slate-400">{t.levelShort}11 EHP</div>
                        <div className="text-slate-200 font-bold">{node.avg_ehp_lvl11}</div>
                      </div>
                    </div>

                    {!isActive && (
                      <button
                        type="button"
                        disabled={isGenerating}
                        onClick={() => onSelectAndGenerateState(stateKey)}
                        className="w-full py-1.5 px-3 rounded-lg text-xs font-semibold bg-cyan-500/15 hover:bg-cyan-500/25 disabled:opacity-50 text-cyan-200 border border-cyan-500/40 transition cursor-pointer"
                      >
                        {t.pivotApplyStateBtn}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
