import { Flame, Shield } from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';
import type { AramModifiers, MapKey } from '../types/api';

interface AramModifiersBarProps {
  modifiers?: AramModifiers | null;
  gameMap?: MapKey | string | null;
}

interface ModifierPill {
  key: string;
  label: string;
  valueText: string;
  isBuff: boolean;
}

function buildModifierPills(
  modifiers: AramModifiers,
  labels: {
    dmgDealt: string;
    dmgTaken: string;
    healing: string;
    shielding: string;
    abilityHaste: string;
    attackSpeed: string;
    tenacity: string;
    energyRegen: string;
  }
): ModifierPill[] {
  const pills: ModifierPill[] = [];

  const pushPct = (key: string, label: string, mult: number, invertPolarity = false) => {
    const pct = Math.round((mult - 1) * 100);
    if (pct === 0) return;
    const isBuff = invertPolarity ? pct < 0 : pct > 0;
    pills.push({
      key,
      label,
      valueText: `${pct > 0 ? '+' : ''}${pct}%`,
      isBuff,
    });
  };

  pushPct('dmg_dealt', labels.dmgDealt, modifiers.dmg_dealt, false);
  pushPct('dmg_taken', labels.dmgTaken, modifiers.dmg_taken, true);
  pushPct('healing', labels.healing, modifiers.healing, false);
  pushPct('shielding', labels.shielding, modifiers.shielding, false);
  if (Math.round(modifiers.ability_haste) !== 0) {
    const ah = Math.round(modifiers.ability_haste);
    pills.push({
      key: 'ability_haste',
      label: labels.abilityHaste,
      valueText: `${ah > 0 ? '+' : ''}${ah}`,
      isBuff: ah > 0,
    });
  }
  pushPct('total_as', labels.attackSpeed, modifiers.total_as, false);
  pushPct('tenacity', labels.tenacity, modifiers.tenacity, false);
  pushPct('energyregen_mod', labels.energyRegen, modifiers.energyregen_mod, false);

  return pills;
}

export function AramModifiersBar({ modifiers, gameMap }: AramModifiersBarProps) {
  const { t } = useLanguage();

  if (gameMap !== 'aram' || !modifiers) {
    return null;
  }

  const pills = buildModifierPills(modifiers, {
    dmgDealt: t.aramDmgDealt,
    dmgTaken: t.aramDmgTaken,
    healing: t.aramHealing,
    shielding: t.aramShielding,
    abilityHaste: t.aramAbilityHaste,
    attackSpeed: t.aramAttackSpeed,
    tenacity: t.aramTenacity,
    energyRegen: t.aramEnergyRegen,
  });

  return (
    <div className="rounded-lg bg-cyan-950/25 border border-cyan-500/30 px-3.5 py-2.5 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-300">
          <Flame className="w-3.5 h-3.5 text-cyan-400" />
          {t.aramModifiersTitle}
        </span>
        {!modifiers.has_modifiers || pills.length === 0 ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-900 text-cyan-200 border border-cyan-500/30">
            <Shield className="w-3 h-3" /> {t.aramModifiersNeutral}
          </span>
        ) : null}
      </div>

      {pills.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {pills.map((p) => (
            <span
              key={p.key}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${
                p.isBuff
                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
                  : 'bg-rose-500/15 text-rose-300 border-rose-500/40'
              }`}
            >
              <span>{p.label}:</span>
              <span className="font-mono font-bold">{p.valueText}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
