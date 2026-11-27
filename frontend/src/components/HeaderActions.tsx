import { useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';
import { useTheme } from '../theme/ThemeContext';

const GITHUB_REPO_URL = 'https://github.com/burakemrealp/PatchDiff_Sandbox';

export function HeaderActions() {
  const { t } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const [activeTip, setActiveTip] = useState<'theme' | 'github' | null>(null);
  const isDark = theme === 'dark';
  const themeLabel = isDark ? t.themeSwitchToLight : t.themeSwitchToDark;

  return (
    <div className="flex items-center gap-2">
      <div
        className="relative"
        onMouseEnter={() => setActiveTip('theme')}
        onMouseLeave={() => setActiveTip((cur) => (cur === 'theme' ? null : cur))}
      >
        <button
          type="button"
          onClick={() => {
            setActiveTip(null);
            toggleTheme();
          }}
          onFocus={(e) => {
            if (e.currentTarget.matches(':focus-visible')) {
              setActiveTip('theme');
            }
          }}
          onBlur={() => setActiveTip((cur) => (cur === 'theme' ? null : cur))}
          aria-label={themeLabel}
          className="w-9 h-9 rounded-full inline-flex items-center justify-center bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-amber-500/70 text-amber-400 shadow-sm transition-all cursor-pointer"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4 text-purple-500" />}
        </button>
        <span
          role="tooltip"
          aria-hidden={activeTip !== 'theme'}
          className={`pointer-events-none transition-all duration-150 absolute end-0 top-full mt-2 px-2.5 py-1 rounded-md text-[11px] font-medium whitespace-nowrap bg-slate-900 text-slate-100 border border-slate-700 shadow-lg z-40 ${
            activeTip === 'theme' ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'
          }`}
        >
          {themeLabel}
        </span>
      </div>

      <div
        className="relative"
        onMouseEnter={() => setActiveTip('github')}
        onMouseLeave={() => setActiveTip((cur) => (cur === 'github' ? null : cur))}
      >
        <a
          href={GITHUB_REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => setActiveTip(null)}
          onFocus={(e) => {
            if (e.currentTarget.matches(':focus-visible')) {
              setActiveTip('github');
            }
          }}
          onBlur={() => setActiveTip((cur) => (cur === 'github' ? null : cur))}
          aria-label={t.githubRepoTooltip}
          className="w-9 h-9 rounded-full inline-flex items-center justify-center bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-cyan-500/70 text-slate-200 hover:text-cyan-300 shadow-sm transition-all"
        >
          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
            className="w-4 h-4 fill-current"
          >
            <path d="M12 .5a11.5 11.5 0 0 0-3.63 22.41c.57.1.78-.25.78-.55v-2.1c-3.18.69-3.85-1.35-3.85-1.35-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.75 1.18 1.75 1.18 1.02 1.75 2.68 1.24 3.33.95.1-.74.4-1.25.72-1.54-2.54-.29-5.21-1.27-5.21-5.65 0-1.25.45-2.27 1.18-3.07-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.16 1.17a10.9 10.9 0 0 1 5.76 0c2.2-1.48 3.16-1.17 3.16-1.17.62 1.58.23 2.75.11 3.04.73.8 1.18 1.82 1.18 3.07 0 4.39-2.67 5.36-5.22 5.64.41.36.78 1.06.78 2.13v3.16c0 .31.21.66.79.55A11.5 11.5 0 0 0 12 .5Z" />
          </svg>
        </a>
        <span
          role="tooltip"
          aria-hidden={activeTip !== 'github'}
          className={`pointer-events-none transition-all duration-150 absolute end-0 top-full mt-2 px-2.5 py-1 rounded-md text-[11px] font-medium whitespace-nowrap bg-slate-900 text-slate-100 border border-slate-700 shadow-lg z-40 ${
            activeTip === 'github' ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'
          }`}
        >
          {t.githubRepoTooltip}
        </span>
      </div>
    </div>
  );
}
