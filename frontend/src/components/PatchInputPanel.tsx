import { FileText, Sparkles, Loader2 } from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';

interface PatchInputPanelProps {
  rawText: string;
  setRawText: (val: string) => void;
  patchVersion: string;
  setPatchVersion: (val: string) => void;
  onParse: () => void;
  isParsing: boolean;
}

const SAMPLE_PATCH_TR = `Ahri
Taban Zırh: 21 -> 18
Q - Aldatıcı Küre: Taban Hasar: 80/130/180/230/280 -> 90/145/200/255/310
Q - Aldatıcı Küre: AP Oranı: %90 -> %105
Q - Bekleme Süresi: 7 saniye -> 6.5 saniye

Zed
Taban Saldırı Gücü: 63 -> 60
Q - Keskin Shuriken İlave SG Oranı: %110 -> %125`;

const SAMPLE_PATCH_EN = `Ahri
Base Armor: 21 -> 18
Q - Orb of Deception: Base Damage: 80/130/180/230/280 -> 90/145/200/255/310
Q - Orb of Deception: AP Ratio: 90% -> 105%
Q - Cooldown: 7 seconds -> 6.5 seconds

Zed
Base Attack Damage: 63 -> 60
Q - Razor Shuriken Bonus AD Ratio: 110% -> 125%`;

export function PatchInputPanel({
  rawText,
  setRawText,
  patchVersion,
  setPatchVersion,
  onParse,
  isParsing,
}: PatchInputPanelProps) {
  const { t, localeInfo } = useLanguage();
  const sampleText = localeInfo.langKey === 'tr' ? SAMPLE_PATCH_TR : SAMPLE_PATCH_EN;

  return (
    <section className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-cyan-400" />
          <h2 className="text-base font-semibold text-white">{t.manualInputHeading}</h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setRawText(sampleText)}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer"
          >
            {t.loadSampleBtn}
          </button>
          <input
            type="text"
            value={patchVersion}
            onChange={(e) => setPatchVersion(e.target.value)}
            placeholder="26.23"
            className="w-20 px-2.5 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-700 text-slate-200 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      <textarea
        rows={7}
        value={rawText}
        onChange={(e) => setRawText(e.target.value)}
        placeholder={t.manualInputPlaceholder}
        className="w-full rounded-lg bg-slate-950 border border-slate-800 p-3 text-sm font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
      />

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onParse}
          disabled={isParsing || rawText.trim().length < 5}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 transition cursor-pointer"
        >
          {isParsing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {isParsing ? t.parsingBtn : t.parseBtn}
        </button>
      </div>
    </section>
  );
}
