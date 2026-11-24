import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  DEFAULT_LOCALE_CODE,
  LOL_LOCALES,
  TRANSLATIONS,
  getLocaleOption,
} from './index';
import { LanguageContext } from './LanguageContext';

const STORAGE_KEY = 'patchdiff_locale';

function getInitialLocale(): string {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved && LOL_LOCALES.some((l) => l.code === saved)) {
      return saved;
    }
  } catch {
    // ignore storage errors
  }
  return DEFAULT_LOCALE_CODE;
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<string>(getInitialLocale);

  const localeInfo = useMemo(() => getLocaleOption(locale), [locale]);
  const t = useMemo(() => TRANSLATIONS[localeInfo.langKey] || TRANSLATIONS.tr, [localeInfo]);

  const setLocale = useCallback((code: string) => {
    const valid = getLocaleOption(code).code;
    setLocaleState(valid);
    try {
      window.localStorage.setItem(STORAGE_KEY, valid);
    } catch {
      // ignore storage errors
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = localeInfo.webCode;
    document.documentElement.dir = localeInfo.dir;
  }, [localeInfo]);

  const value = useMemo(
    () => ({ locale, localeInfo, setLocale, t }),
    [locale, localeInfo, setLocale, t]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
