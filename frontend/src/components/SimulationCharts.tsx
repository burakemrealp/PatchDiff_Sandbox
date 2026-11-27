import { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { BarChart3, Clock, Flame, Zap } from 'lucide-react';
import type { SimulateResponse } from '../types/api';
import { useLanguage } from '../i18n/LanguageContext';
import { useTheme } from '../theme/ThemeContext';
import { AramModifiersBar } from './AramModifiersBar';

interface SimulationChartsProps {
  simResponse: SimulateResponse;
}

type ChartTab = 'burst' | 'dps' | 'ttk';

export function SimulationCharts({ simResponse }: SimulationChartsProps) {
  const { t } = useLanguage();
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const [activeTab, setActiveTab] = useState<ChartTab>('burst');
  const { result, cached } = simResponse;

  const phaseRows = [
    { label: t.phaseEarly6, data: result.summary.early_game_lvl6 },
    { label: t.phaseMid11, data: result.summary.mid_game_lvl11 },
    { label: t.phaseLate18, data: result.summary.late_game_lvl18 },
    ...(result.summary.late_game_lvl20
      ? [{ label: t.phaseTop20, data: result.summary.late_game_lvl20 }]
      : []),
  ];

  return (
    <section className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-cyan-400" />
          <h2 className="text-base font-semibold text-white">
            {t.simChartsHeading} {result.champion_key} vs {result.target_label}
          </h2>
        </div>

        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
            cached
              ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
              : 'bg-slate-800 text-slate-300 border-slate-700'
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          {cached ? t.fastCacheBadge : t.liveCalcBadge}
        </span>
      </div>

      <AramModifiersBar
        modifiers={result.game_context?.aram_modifiers}
        gameMap={result.game_context?.game_map}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
          <div className="text-xs text-slate-400">{t.cardBurstDelta}</div>
          <div
            className={`text-2xl font-bold mt-1 ${
              result.summary.avg_burst_delta_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {result.summary.avg_burst_delta_pct > 0 ? '+' : ''}
            {result.summary.avg_burst_delta_pct}%
          </div>
        </div>

        <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
          <div className="text-xs text-slate-400">{t.cardDpsDelta}</div>
          <div
            className={`text-2xl font-bold mt-1 ${
              result.summary.avg_dps_delta_pct >= 0 ? 'text-cyan-400' : 'text-rose-400'
            }`}
          >
            {result.summary.avg_dps_delta_pct > 0 ? '+' : ''}
            {result.summary.avg_dps_delta_pct}%
          </div>
        </div>

        <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
          <div className="text-xs text-slate-400">{t.cardPhysEhpDelta}</div>
          <div
            className={`text-2xl font-bold mt-1 ${
              result.summary.avg_ehp_delta_pct > 0
                ? 'text-emerald-400'
                : result.summary.avg_ehp_delta_pct < 0
                  ? 'text-rose-400'
                  : 'text-slate-300'
            }`}
          >
            {result.summary.avg_ehp_delta_pct > 0 ? '+' : ''}
            {result.summary.avg_ehp_delta_pct}%
          </div>
        </div>

        <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
          <div className="text-xs text-slate-400">{t.cardMagicEhpDelta}</div>
          <div
            className={`text-2xl font-bold mt-1 ${
              (result.summary.avg_magic_ehp_delta_pct ?? 0) > 0
                ? 'text-emerald-400'
                : (result.summary.avg_magic_ehp_delta_pct ?? 0) < 0
                  ? 'text-rose-400'
                  : 'text-slate-300'
            }`}
          >
            {(result.summary.avg_magic_ehp_delta_pct ?? 0) > 0 ? '+' : ''}
            {result.summary.avg_magic_ehp_delta_pct ?? 0}%
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
        <button
          type="button"
          onClick={() => setActiveTab('burst')}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
            activeTab === 'burst'
              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
              : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
          }`}
        >
          <Flame className="w-3.5 h-3.5" /> {t.chartTabBurst}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('dps')}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
            activeTab === 'dps'
              ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40'
              : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
          }`}
        >
          <Zap className="w-3.5 h-3.5" /> {t.chartTabDps}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('ttk')}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
            activeTab === 'ttk'
              ? 'bg-amber-500/15 text-amber-300 border-amber-500/40'
              : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
          }`}
        >
          <Clock className="w-3.5 h-3.5" /> {t.chartTabTtk}
        </button>
      </div>

      <div className="h-80 w-full bg-slate-950 rounded-lg border border-slate-800 p-4" dir="ltr">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={result.level_curves} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={isLight ? '#cbd5e1' : '#1e3557'} />
            <XAxis
              dataKey="level"
              stroke={isLight ? '#334155' : '#9eb3d1'}
              tick={{ fontSize: 12 }}
              tickFormatter={(lvl) => `${t.levelShort} ${lvl}`}
            />
            <YAxis stroke={isLight ? '#334155' : '#9eb3d1'} tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: isLight ? '#ffffff' : '#10203a',
                borderColor: isLight ? '#b5c4dc' : '#2c4a75',
                color: isLight ? '#0a1628' : '#eef2f8',
                borderRadius: '0.5rem',
                fontSize: '12px',
              }}
              labelFormatter={(lvl) => `${t.levelWord} ${lvl}`}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />

            {activeTab === 'burst' && (
              <>
                <Line
                  type="monotone"
                  dataKey="old_burst"
                  name={t.legendOldBurst}
                  stroke="#f43f5e"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="new_burst"
                  name={t.legendNewBurst}
                  stroke="#10b981"
                  strokeWidth={3}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="target_hp"
                  name={t.legendTargetHp}
                  stroke="#f59e0b"
                  strokeWidth={1.5}
                  strokeDasharray="3 3"
                  dot={false}
                />
              </>
            )}

            {activeTab === 'dps' && (
              <>
                <Line
                  type="monotone"
                  dataKey="old_dps"
                  name={t.legendOldDps}
                  stroke="#f43f5e"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="new_dps"
                  name={t.legendNewDps}
                  stroke="#06b6d4"
                  strokeWidth={3}
                  dot={{ r: 3 }}
                />
              </>
            )}

            {activeTab === 'ttk' && (
              <>
                <Line
                  type="monotone"
                  dataKey="old_ttk_sec"
                  name={t.legendOldTtk}
                  stroke="#f43f5e"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="new_ttk_sec"
                  name={t.legendNewTtk}
                  stroke="#f59e0b"
                  strokeWidth={3}
                  dot={{ r: 3 }}
                />
              </>
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-start text-xs">
          <thead className="bg-slate-950 text-slate-400 uppercase">
            <tr>
              <th className="px-4 py-3">{t.colPhase}</th>
              <th className="px-4 py-3">{t.colTargetHp}</th>
              <th className="px-4 py-3">{t.colBurst}</th>
              <th className="px-4 py-3">{t.colDps}</th>
              <th className="px-4 py-3">{t.colTtk}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 font-mono">
            {phaseRows.map(({ label, data }) => (
              <tr key={label} className="bg-slate-900/60 hover:bg-slate-800/40">
                <td className="px-4 py-3 font-sans font-medium text-white">{label}</td>
                <td className="px-4 py-3 text-amber-300">{data.target_hp} HP</td>
                <td className="px-4 py-3">
                  <span className="text-slate-400">{data.old_burst}</span> →{' '}
                  <span className="text-emerald-400 font-semibold">{data.new_burst}</span>{' '}
                  <span className="text-slate-500">
                    ({data.burst_delta_pct > 0 ? '+' : ''}
                    {data.burst_delta_pct}%)
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-slate-400">{data.old_dps}</span> →{' '}
                  <span className="text-cyan-400 font-semibold">{data.new_dps}</span>{' '}
                  <span className="text-slate-500">
                    ({data.dps_delta_pct > 0 ? '+' : ''}
                    {data.dps_delta_pct}%)
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-slate-400">
                    {data.old_ttk_sec}
                    {t.metricSecUnit}
                  </span>{' '}
                  →{' '}
                  <span className="text-amber-400 font-semibold">
                    {data.new_ttk_sec}
                    {t.metricSecUnit}
                  </span>{' '}
                  <span className="text-slate-500">
                    ({data.ttk_diff_sec > 0 ? '+' : ''}
                    {data.ttk_diff_sec}
                    {t.metricSecUnit})
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
