import { useState, type ReactNode } from 'react';
import { Brain, CloudDownload, FileText, Info, Sparkles } from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';

export type NavSourceMode = 'ai-lab' | 'zero-day' | 'auto' | 'manual';

interface FeatureShowcaseNavProps {
  activeMode: NavSourceMode;
  onSelectMode: (mode: NavSourceMode) => void;
}

interface NavCardItem {
  mode: NavSourceMode;
  title: string;
  tag: string;
  shortDesc: string;
  tooltip: string;
  icon: ReactNode;
  activeBorder: string;
  activeBadge: string;
  iconWrapActive: string;
}

export function FeatureShowcaseNav({
  activeMode,
  onSelectMode,
}: FeatureShowcaseNavProps) {
  const { t } = useLanguage();
  const [openTipMode, setOpenTipMode] = useState<NavSourceMode | null>(null);

  const items: NavCardItem[] = [
    {
      mode: 'ai-lab',
      title: t.navBuildTitle,
      tag: t.navBuildTag,
      shortDesc: t.navBuildShort,
      tooltip: t.navBuildTooltip,
      icon: <Brain className="w-4 h-4" />,
      activeBorder: 'border-purple-500/70 bg-purple-500/10 shadow-sm',
      activeBadge: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
      iconWrapActive: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
    },
    {
      mode: 'zero-day',
      title: t.navRadarTitle,
      tag: t.navRadarTag,
      shortDesc: t.navRadarShort,
      tooltip: t.navRadarTooltip,
      icon: <Sparkles className="w-4 h-4" />,
      activeBorder: 'border-amber-500/70 bg-amber-500/10 shadow-sm',
      activeBadge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      iconWrapActive: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    },
    {
      mode: 'auto',
      title: t.navDiffTitle,
      tag: t.navDiffTag,
      shortDesc: t.navDiffShort,
      tooltip: t.navDiffTooltip,
      icon: <CloudDownload className="w-4 h-4" />,
      activeBorder: 'border-cyan-500/70 bg-cyan-500/10 shadow-sm',
      activeBadge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
      iconWrapActive: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
    },
    {
      mode: 'manual',
      title: t.navSimTitle,
      tag: t.navSimTag,
      shortDesc: t.navSimShort,
      tooltip: t.navSimTooltip,
      icon: <FileText className="w-4 h-4" />,
      activeBorder: 'border-emerald-500/70 bg-emerald-500/10 shadow-sm',
      activeBadge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      iconWrapActive: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    },
  ];

  return (
    <nav
      aria-label="Primary Features"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"
    >
      {items.map((item) => {
        const isActive = activeMode === item.mode;
        const isTipOpen = openTipMode === item.mode;

        return (
          <div
            key={item.mode}
            className="relative"
            onMouseEnter={() => setOpenTipMode(item.mode)}
            onMouseLeave={() => setOpenTipMode((cur) => (cur === item.mode ? null : cur))}
          >
            <button
              type="button"
              onClick={() => {
                setOpenTipMode(null);
                onSelectMode(item.mode);
              }}
              onFocus={(e) => {
                if (e.currentTarget.matches(':focus-visible')) {
                  setOpenTipMode(item.mode);
                }
              }}
              onBlur={() => setOpenTipMode((cur) => (cur === item.mode ? null : cur))}
              aria-current={isActive ? 'page' : undefined}
              aria-describedby={isTipOpen ? `nav-tip-${item.mode}` : undefined}
              className={`w-full h-full text-start rounded-xl border px-3.5 py-3 transition-all cursor-pointer flex flex-col justify-between gap-2 ${
                isActive
                  ? item.activeBorder
                  : 'bg-slate-900 border-slate-800 hover:border-slate-600'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`w-7 h-7 rounded-lg border inline-flex items-center justify-center shrink-0 ${
                      isActive
                        ? item.iconWrapActive
                        : 'bg-slate-950 border-slate-800 text-slate-300'
                    }`}
                  >
                    {item.icon}
                  </span>
                  <span className="text-xs font-bold text-slate-100 truncate">
                    {item.title}
                  </span>
                </div>
                <span
                  className={`px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wider border shrink-0 ${
                    isActive
                      ? item.activeBadge
                      : 'bg-slate-950 text-slate-400 border-slate-800'
                  }`}
                >
                  {item.tag}
                </span>
              </div>

              <div className="flex items-center justify-between gap-2 text-[11px] text-slate-400">
                <span className="truncate">{item.shortDesc}</span>
                <Info
                  className={`w-3.5 h-3.5 shrink-0 transition-colors ${
                    isTipOpen ? 'text-cyan-400' : 'text-slate-500'
                  }`}
                />
              </div>
            </button>

            <div
              id={`nav-tip-${item.mode}`}
              role="tooltip"
              aria-hidden={!isTipOpen}
              className={`pointer-events-none hidden sm:block absolute start-0 end-0 top-full mt-2 p-3 rounded-xl bg-slate-900 border border-amber-500/45 shadow-xl shadow-black/60 text-xs text-slate-200 leading-relaxed z-40 transition-all duration-150 ${
                isTipOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'
              }`}
            >
              {item.tooltip}
            </div>
          </div>
        );
      })}
    </nav>
  );
}
