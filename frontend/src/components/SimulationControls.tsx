import { useState } from 'react';
import { Crosshair, Play, Loader2, Shield, Package, Search } from 'lucide-react';
import type { ItemSummary } from '../types/api';
import { ItemIcon } from './ItemIcon';
import { useLanguage } from '../i18n/LanguageContext';

interface SimulationControlsProps {
  items: ItemSummary[];
  selectedItemIds: string[];
  onToggleItem: (itemId: string) => void;
  onClearItems: () => void;
  targetProfile: 'squishy' | 'bruiser' | 'tank';
  onChangeTarget: (profile: 'squishy' | 'bruiser' | 'tank') => void;
  onSimulate: () => void;
  isSimulating: boolean;
  disabled: boolean;
}

export function SimulationControls({
  items,
  selectedItemIds,
  onToggleItem,
  onClearItems,
  targetProfile,
  onChangeTarget,
  onSimulate,
  isSimulating,
  disabled,
}: SimulationControlsProps) {
  const { t } = useLanguage();
  const [itemSearch, setItemSearch] = useState('');

  const targets: { key: 'squishy' | 'bruiser' | 'tank'; label: string; desc: string }[] = [
    { key: 'squishy', label: t.targetSquishy, desc: t.targetSquishyDesc },
    { key: 'bruiser', label: t.targetBruiser, desc: t.targetBruiserDesc },
    { key: 'tank', label: t.targetTank, desc: t.targetTankDesc },
  ];

  const filteredItems = items.filter((item) => {
    if (!itemSearch.trim()) return true;
    const q = itemSearch.toLowerCase();
    return item.name.toLowerCase().includes(q) || item.item_id.includes(q);
  });

  return (
    <section className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-5">
      <div className="flex items-center gap-2">
        <Crosshair className="w-5 h-5 text-cyan-400" />
        <h2 className="text-base font-semibold text-white">{t.simControlsHeading}</h2>
      </div>

      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase text-slate-400 flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5" /> {t.targetEnemyLabel}
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {targets.map((tg) => {
            const active = targetProfile === tg.key;
            return (
              <button
                key={tg.key}
                type="button"
                onClick={() => onChangeTarget(tg.key)}
                className={`p-3 rounded-lg border text-left transition cursor-pointer ${
                  active
                    ? 'bg-cyan-500/15 border-cyan-500/50 text-white'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="text-sm font-semibold">{tg.label}</div>
                <div className="text-xs text-slate-400 mt-0.5">{tg.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="text-xs font-semibold uppercase text-slate-400 flex items-center gap-1.5">
            <Package className="w-3.5 h-3.5" /> {t.itemBuildLabel} ({selectedItemIds.length}{' '}
            {t.selectedLabel} / {items.length} {t.itemsUnit})
          </label>
          <div className="flex items-center gap-3">
            {selectedItemIds.length > 0 && (
              <button
                type="button"
                onClick={onClearItems}
                className="text-xs text-slate-400 hover:text-rose-300 underline-offset-4 hover:underline transition cursor-pointer"
              >
                {t.clearSelectedBtn}
              </button>
            )}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute start-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={itemSearch}
                onChange={(e) => setItemSearch(e.target.value)}
                placeholder={t.searchItemPlaceholder}
                className="ps-8 pe-3 py-1 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-56"
              />
            </div>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-60 overflow-y-auto pe-1">
          {filteredItems.map((item) => {
            const selected = selectedItemIds.includes(item.item_id);
            return (
              <button
                key={item.item_id}
                type="button"
                onClick={() => onToggleItem(item.item_id)}
                className={`flex items-center justify-between p-2.5 rounded-lg border text-xs transition cursor-pointer ${
                  selected
                    ? 'bg-amber-500/15 border-amber-500/50 text-amber-200'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0 pe-2">
                  <ItemIcon
                    iconUrl={item.icon_url}
                    name={item.name}
                    gold={item.gold_total}
                    stats={item.stats}
                    size="md"
                    highlight={selected ? 'selected' : 'default'}
                  />
                  <span className="font-medium truncate">{item.name}</span>
                </div>
                <span className="text-amber-400 font-mono shrink-0">{item.gold_total}g</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onSimulate}
          disabled={disabled || isSimulating}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 transition cursor-pointer"
        >
          {isSimulating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {isSimulating ? t.calculatingBtn : t.startSimBtn}
        </button>
      </div>
    </section>
  );
}
