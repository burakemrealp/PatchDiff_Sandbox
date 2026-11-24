import { useState } from 'react';
import { Package } from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';
import type { TranslationDict } from '../i18n';

function getStatLabels(t: TranslationDict): Record<string, string> {
  return {
    ap: t.statAp,
    ad: t.statAd,
    hp: t.statHp,
    mana: t.statMana,
    armor: t.statArmor,
    mr: t.statMr,
    ability_haste: t.statAh,
    attack_speed: t.statAs,
    crit_chance: t.statCrit,
    lethality: t.statLethality,
    magic_pen_flat: t.statMpenFlat,
    magic_pen_percent: t.statMpenPct,
    armor_pen_percent: t.statApenPct,
    lifesteal: t.statLifesteal,
    move_speed: t.statMs,
  };
}

function formatTooltip(
  t: TranslationDict,
  name: string,
  gold?: number,
  stats?: Record<string, number>
): string {
  const statLabels = getStatLabels(t);
  const lines: string[] = [gold ? `${name} (${gold} ${t.goldUnit})` : name];
  if (stats) {
    const statParts: string[] = [];
    for (const [k, v] of Object.entries(stats)) {
      if (k.startsWith('_') || !v) continue;
      const label = statLabels[k];
      if (!label) continue;
      const isPct =
        k.includes('percent') ||
        k === 'attack_speed' ||
        k === 'crit_chance' ||
        k === 'lifesteal';
      const valStr = isPct ? `${Math.round(v * 100)}%` : `${Math.round(v)}`;
      statParts.push(`+${valStr} ${label}`);
    }
    if (statParts.length > 0) {
      lines.push(statParts.slice(0, 5).join(' · '));
    }
  }
  return lines.join('\n');
}

interface ItemIconProps {
  iconUrl?: string | null;
  name: string;
  gold?: number;
  stats?: Record<string, number>;
  size?: 'sm' | 'md' | 'lg';
  highlight?: 'boot' | 'selected' | 'default';
}

export function ItemIcon({
  iconUrl,
  name,
  gold,
  stats,
  size = 'md',
  highlight = 'default',
}: ItemIconProps) {
  const { t } = useLanguage();
  const [failed, setFailed] = useState(false);

  const dims =
    size === 'sm'
      ? 'w-5 h-5 rounded'
      : size === 'lg'
        ? 'w-9 h-9 rounded-md'
        : 'w-7 h-7 rounded-md';

  const border =
    highlight === 'boot'
      ? 'border-cyan-400/60'
      : highlight === 'selected'
        ? 'border-amber-400/70'
        : 'border-slate-700/90';

  const tooltip = formatTooltip(t, name, gold, stats);

  if (!iconUrl || failed) {
    return (
      <span
        title={tooltip}
        className={`${dims} border ${border} bg-slate-900 flex items-center justify-center shrink-0 text-slate-500`}
      >
        <Package className={size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'} />
      </span>
    );
  }

  return (
    <img
      src={iconUrl}
      alt={name}
      title={tooltip}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`${dims} border ${border} object-cover shrink-0 bg-slate-950 shadow-sm`}
    />
  );
}
