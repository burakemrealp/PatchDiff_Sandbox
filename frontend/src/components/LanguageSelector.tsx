import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Globe } from 'lucide-react';
import { LOL_LOCALES } from '../i18n';
import { useLanguage } from '../i18n/LanguageContext';

export function LanguageSelector() {
  const { locale, localeInfo, setLocale, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 hover:border-cyan-500/60 transition cursor-pointer"
      >
        <Globe className="w-3.5 h-3.5 text-cyan-400" />
        <span>{t.languagesBtn}</span>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
          {localeInfo.region || localeInfo.code}
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div
          role="listbox"
          aria-label={t.languagesModalTitle}
          className="absolute end-0 mt-2 w-[min(92vw,34rem)] rounded-xl bg-slate-900/98 backdrop-blur-md border border-slate-700 shadow-2xl shadow-black/60 p-4 z-50 space-y-3"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-cyan-400" />
              <span className="text-sm font-semibold text-white">{t.languagesModalTitle}</span>
            </div>
            <span className="text-[11px] text-slate-400">{t.languagesModalHint}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 max-h-80 overflow-y-auto pr-1">
            {LOL_LOCALES.map((opt) => {
              const isSelected = opt.code === locale;
              return (
                <button
                  key={opt.code}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    setLocale(opt.code);
                    setOpen(false);
                  }}
                  className={`flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg text-left text-xs border transition cursor-pointer ${
                    isSelected
                      ? 'bg-cyan-500/15 border-cyan-500/60 text-cyan-200 font-semibold'
                      : 'bg-slate-950/70 border-slate-800/90 text-slate-300 hover:border-slate-600 hover:bg-slate-800/70 hover:text-white'
                  }`}
                >
                  <div className="min-w-0 truncate">
                    <span className="truncate">{opt.nativeName}</span>
                    {opt.region && (
                      <span className="ms-1 text-[10px] font-mono text-slate-400">
                        ({opt.region})
                      </span>
                    )}
                  </div>
                  {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400 shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
