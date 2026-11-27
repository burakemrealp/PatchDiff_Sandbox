import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Globe } from 'lucide-react';
import { LOL_LOCALES } from '../i18n';
import { useLanguage } from '../i18n/LanguageContext';

interface PopoverGeometry {
  width: number;
  leftOffset: number;
}

export function LanguageSelector() {
  const { locale, localeInfo, setLocale, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [geometry, setGeometry] = useState<PopoverGeometry>({ width: 544, leftOffset: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  const computeGeometry = (): PopoverGeometry => {
    const vw = typeof window !== 'undefined' ? window.innerWidth : 1024;
    const width = Math.max(260, Math.min(vw - 24, 544));
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) {
      return { width, leftOffset: 0 };
    }
    const isRtl = localeInfo.dir === 'rtl';
    const idealLeft = isRtl ? rect.left : rect.right - width;
    const clampedLeft = Math.max(12, Math.min(idealLeft, vw - width - 12));
    return {
      width,
      leftOffset: Math.round(clampedLeft - rect.left),
    };
  };

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
    const handleResize = () => {
      const vw = window.innerWidth;
      const width = Math.max(260, Math.min(vw - 24, 544));
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const isRtl = localeInfo.dir === 'rtl';
      const idealLeft = isRtl ? rect.left : rect.right - width;
      const clampedLeft = Math.max(12, Math.min(idealLeft, vw - width - 12));
      setGeometry({ width, leftOffset: Math.round(clampedLeft - rect.left) });
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleResize);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleResize);
    };
  }, [open, localeInfo.dir]);

  const handleToggle = () => {
    if (!open) {
      setGeometry(computeGeometry());
    }
    setOpen((prev) => !prev);
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 hover:border-cyan-500/60 transition cursor-pointer whitespace-nowrap"
      >
        <Globe className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
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
          style={{ width: `${geometry.width}px`, left: `${geometry.leftOffset}px` }}
          className="absolute top-full mt-2 rounded-xl bg-slate-900/98 backdrop-blur-md border border-slate-700 shadow-2xl shadow-black/60 p-4 z-50 space-y-3"
        >
          <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
            <div className="flex items-center gap-2 min-w-0">
              <Globe className="w-4 h-4 text-cyan-400 shrink-0" />
              <span className="text-sm font-semibold text-white truncate">{t.languagesModalTitle}</span>
            </div>
            <span className="text-[11px] text-slate-400 shrink-0">{t.languagesModalHint}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 max-h-80 overflow-y-auto pe-1">
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
                  className={`flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg text-start text-xs border transition cursor-pointer ${
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
