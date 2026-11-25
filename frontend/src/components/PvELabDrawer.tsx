import { CheckCircle2, Clock, Crosshair, Loader2, Skull, Swords, XCircle } from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';
import type { PvELabReport } from '../types/api';

interface PvELabDrawerProps {
  report: PvELabReport | null;
  isLoading: boolean;
  error: string | null;
}

export function PvELabDrawer({ report, isLoading, error }: PvELabDrawerProps) {
  const { t } = useLanguage();

  if (isLoading) {
    return (
      <div className="rounded-lg bg-slate-950 border border-cyan-500/30 p-4 flex items-center gap-2 text-xs text-cyan-300">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>{t.pveLabLoadingMsg}</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-300">
        {error}
      </div>
    );
  }

  if (!report) {
    return null;
  }

  return (
    <div className="rounded-lg bg-slate-950 border border-cyan-500/35 p-4 space-y-4">
      <div className="space-y-2.5">
        <div>
          <div className="flex items-center gap-1.5 text-xs font-bold text-cyan-300">
            <Crosshair className="w-3.5 h-3.5" />
            <span>{t.pveWaveclearHeading}</span>
          </div>
          <p className="text-[11px] text-slate-400">{t.pveWaveclearSub}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          {report.waveclear_breakpoints.map((row) => (
            <div
              key={row.minute}
              className={`rounded-lg border p-3 space-y-2 text-xs ${
                row.can_oneshot_caster
                  ? 'bg-emerald-950/20 border-emerald-500/35'
                  : 'bg-slate-900 border-amber-500/30'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono font-bold text-white">
                  {row.minute} {t.pveMinuteLabel} · {t.levelShort}
                  {row.champion_level}
                </span>
                <span
                  className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                    row.can_oneshot_caster
                      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
                      : 'bg-rose-500/15 text-rose-300 border-rose-500/40'
                  }`}
                >
                  {row.can_oneshot_caster ? (
                    <CheckCircle2 className="w-3 h-3" />
                  ) : (
                    <XCircle className="w-3 h-3" />
                  )}
                  {row.can_oneshot_caster ? t.pveOneshotPassBadge : t.pveOneshotFailBadge}
                </span>
              </div>

              <div className="text-[11px] text-slate-300 truncate">
                <span className="px-1 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono me-1.5">
                  {row.primary_slot}
                </span>
                <span>{row.primary_spell_name}</span>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-slate-200 font-bold">{row.total_hit_damage}</span>
                <span className="text-slate-400">
                  vs {t.pveCasterHpLabel}: {row.caster_hp}
                </span>
              </div>

              <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-800/80">
                {row.can_oneshot_caster ? (
                  <span className="font-mono text-emerald-400 font-semibold">
                    +{row.damage_margin}
                  </span>
                ) : (
                  <span className="text-amber-300 font-medium">
                    {row.missing_stat_value > 0
                      ? `${t.pveNeedsMorePrefix}${row.missing_stat_value} ${row.scaling_stat_label || row.scaling_stat || ''}`
                      : `${row.damage_margin}`}
                  </span>
                )}
                <span className="inline-flex items-center gap-1 text-slate-400 font-mono">
                  <Clock className="w-3 h-3 text-cyan-400" />
                  {t.pveWaveClearSecLabel}: {row.full_wave_clear_sec}
                  {t.metricSecUnit}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-2.5 pt-2 border-t border-slate-800">
        <div>
          <div className="flex items-center gap-1.5 text-xs font-bold text-amber-300">
            <Skull className="w-3.5 h-3.5" />
            <span>{t.pveObjectivesHeading}</span>
          </div>
          <p className="text-[11px] text-slate-400">{t.pveObjectivesSub}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          {report.objective_benchmarks.map((mon) => {
            const tierBadge =
              mon.speed_tier === 'FAST'
                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
                : mon.speed_tier === 'MODERATE'
                  ? 'bg-amber-500/15 text-amber-300 border-amber-500/40'
                  : 'bg-rose-500/15 text-rose-300 border-rose-500/40';
            return (
              <div
                key={mon.monster_key}
                className="rounded-lg bg-slate-900 border border-slate-800 p-3 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-white inline-flex items-center gap-1.5">
                    <Swords className="w-3.5 h-3.5 text-amber-400" />
                    {mon.monster_name}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${tierBadge}`}>
                    {mon.speed_label}
                  </span>
                </div>

                <div className="text-[11px] font-mono text-slate-400">
                  {t.levelShort}
                  {mon.reference_level} · {mon.monster_hp} HP · {mon.armor}/{mon.mr}
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800/80 font-mono">
                  <div>
                    <div className="text-[10px] font-sans text-slate-400">{t.pveSoloKillLabel}</div>
                    <div className="text-sm font-bold text-amber-300">
                      {mon.solo_kill_time_sec} {t.metricSecUnit}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-sans text-slate-400">{t.pveSustainedDpsLabel}</div>
                    <div className="text-sm font-bold text-cyan-300">{mon.sustained_dps}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
