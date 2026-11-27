import { ArrowRight, Cpu, GitCompare, ShieldAlert } from 'lucide-react';
import type { ChampionPatchDiff } from '../types/api';
import { useLanguage } from '../i18n/LanguageContext';

interface DiffCardListProps {
  champions: ChampionPatchDiff[];
  selectedChampionKey: string;
  onSelectChampion: (key: string) => void;
  warnings: string[];
  engineUsed?: string | null;
  latencyMs?: number | null;
}

function formatValueSeries(values: number[], suffix = ''): string {
  if (values.length === 0) return '-';
  const allEqual = values.every((v) => v === values[0]);
  return allEqual ? `${values[0]}${suffix}` : `${values.join('/')}${suffix}`;
}

export function DiffCardList({
  champions,
  selectedChampionKey,
  onSelectChampion,
  warnings,
  engineUsed,
  latencyMs,
}: DiffCardListProps) {
  const { t } = useLanguage();

  if (champions.length === 0) return null;

  const activeChamp =
    champions.find((c) => c.champion_key === selectedChampionKey) || champions[0];

  const isLlmEngine = engineUsed && !engineUsed.includes('deterministic');

  const renderDirectionBadge = (direction: 'BUFF' | 'NERF' | 'ADJUSTMENT') => {
    const styles =
      direction === 'BUFF'
        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
        : direction === 'NERF'
          ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
          : 'bg-amber-500/15 text-amber-400 border-amber-500/30';

    const label =
      direction === 'BUFF'
        ? t.dirBuffDetail
        : direction === 'NERF'
          ? t.dirNerfDetail
          : t.dirAdjustmentDetail;

    return (
      <span className={`px-2 py-0.5 text-[11px] font-bold rounded border ${styles}`}>{label}</span>
    );
  };

  const damageTypeLabel = (damageType: 'physical' | 'magic' | 'true') => {
    if (damageType === 'physical') return t.dmgPhysical;
    if (damageType === 'magic') return t.dmgMagic;
    return t.dmgTrue;
  };

  return (
    <section className="rounded-xl bg-slate-900 border border-slate-800 p-3.5 sm:p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-semibold text-white">{t.diffDetailsHeading}</h2>
          </div>

          {engineUsed && (
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono border ${
                isLlmEngine
                  ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                  : 'bg-slate-800 text-slate-300 border-slate-700'
              }`}
            >
              <Cpu className="w-3 h-3" />
              {engineUsed}
              {latencyMs !== null && latencyMs !== undefined && ` · ${latencyMs} ms`}
            </span>
          )}
        </div>

        <div className="flex overflow-x-auto no-scrollbar sm:flex-wrap items-center gap-2 w-full sm:w-auto pb-1 sm:pb-0">
          {champions.map((c) => {
            const isSelected = c.champion_key === activeChamp.champion_key;
            return (
              <button
                key={c.champion_key}
                type="button"
                onClick={() => onSelectChampion(c.champion_key)}
                className={`shrink-0 px-3 py-1 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                {c.champion_key}
              </button>
            );
          })}
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs space-y-1">
          <div className="flex items-center gap-1.5 font-semibold">
            <ShieldAlert className="w-4 h-4" /> {t.autoFixesHeading}
          </div>
          {warnings.map((w, idx) => (
            <p key={idx}>• {w}</p>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {activeChamp.stat_deltas.map((st, idx) => (
          <div
            key={`${st.stat_name}-${idx}`}
            className={`flex flex-wrap items-center justify-between gap-2 p-3 rounded-lg border font-mono text-xs ${
              st.direction === 'BUFF'
                ? 'bg-emerald-950/30 border-emerald-500/25'
                : 'bg-rose-950/30 border-rose-500/25'
            }`}
          >
            <div className="flex items-center gap-2">
              {renderDirectionBadge(st.direction)}
              <span className="text-slate-100 font-semibold font-sans">
                {st.stat_label || st.stat_name}
              </span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <span className="text-rose-400 line-through">{st.old_value}</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-emerald-400 font-bold">{st.new_value}</span>
              <span className="text-slate-400">
                ({st.delta_percent > 0 ? '+' : ''}
                {st.delta_percent}%)
              </span>
            </div>
          </div>
        ))}

        {activeChamp.ability_deltas.map((ab, idx) => (
          <div
            key={`${ab.slot}-${idx}`}
            className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded bg-cyan-500/20 text-cyan-300 font-bold text-xs flex items-center justify-center border border-cyan-500/30">
                  {ab.slot}
                </span>
                <span className="text-sm font-semibold text-white">
                  {ab.ability_name || `${ab.slot} ${t.abilityFallback}`}
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {damageTypeLabel(ab.damage_type)}
                </span>
              </div>
              {renderDirectionBadge(ab.direction)}
            </div>

            <div className="space-y-1.5 font-mono text-xs text-slate-300 ps-0 sm:ps-8 break-words">
              {ab.old_base_damage && ab.new_base_damage && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-slate-400 font-sans">{t.baseDamageLabel}</span>
                  <span className="text-rose-400">{ab.old_base_damage.join('/')}</span>
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                  <span className="text-emerald-400 font-semibold">
                    {ab.new_base_damage.join('/')}
                  </span>
                </div>
              )}

              {ab.old_cooldown && ab.new_cooldown && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-slate-400 font-sans">{t.cooldownLabel}</span>
                  <span className="text-rose-400">
                    {formatValueSeries(ab.old_cooldown, t.metricSecUnit)}
                  </span>
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                  <span className="text-emerald-400 font-semibold">
                    {formatValueSeries(ab.new_cooldown, t.metricSecUnit)}
                  </span>
                </div>
              )}

              {ab.old_mana_cost && ab.new_mana_cost && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-slate-400 font-sans">{t.manaCostLabel}</span>
                  <span className="text-rose-400">{formatValueSeries(ab.old_mana_cost)}</span>
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                  <span className="text-emerald-400 font-semibold">
                    {formatValueSeries(ab.new_mana_cost)}
                  </span>
                </div>
              )}

              {ab.scaling_changes.map((sc, sIdx) => (
                <div key={sIdx} className="flex items-center gap-2">
                  <span className="text-slate-400 font-sans">
                    {t.scalingRatioLabel} ({sc.scaling_stat.toUpperCase()}):
                  </span>
                  <span className="text-rose-400">{Math.round(sc.old_ratio * 100)}%</span>
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                  <span className="text-emerald-400 font-semibold">
                    {Math.round(sc.new_ratio * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {(activeChamp.mechanic_deltas ?? []).map((mc, idx) => (
          <div
            key={`${mc.spell_name}-${mc.field_name}-${idx}`}
            className={`flex flex-wrap items-center justify-between gap-2 p-3 rounded-lg border font-mono text-xs ${
              mc.direction === 'BUFF'
                ? 'bg-emerald-950/30 border-emerald-500/25'
                : mc.direction === 'NERF'
                  ? 'bg-rose-950/30 border-rose-500/25'
                  : 'bg-amber-950/20 border-amber-500/25'
            }`}
          >
            <div className="flex flex-wrap items-center gap-2 font-sans">
              {renderDirectionBadge(mc.direction)}
              <span className="text-cyan-300 font-semibold">
                {mc.spell_label || mc.spell_name}
              </span>
              <span className="text-slate-500">·</span>
              <span className="text-slate-100 font-medium">
                {mc.field_label || mc.field_name}
              </span>
            </div>
            <div className="flex items-center gap-2 text-slate-300 font-mono">
              <span className="text-rose-400">
                {mc.display_old ?? formatValueSeries(mc.old_values)}
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-emerald-400 font-bold">
                {mc.display_new ?? formatValueSeries(mc.new_values)}
              </span>
            </div>
          </div>
        ))}

        {activeChamp.stat_deltas.length === 0 &&
          activeChamp.ability_deltas.length === 0 &&
          (activeChamp.mechanic_deltas ?? []).length === 0 && (
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300">
              {activeChamp.summary || t.noDiffDetailFallback}
            </div>
          )}
      </div>
    </section>
  );
}
