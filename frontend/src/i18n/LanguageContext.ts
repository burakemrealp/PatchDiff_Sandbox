import { createContext, useContext } from 'react';
import type { LolLocaleOption, TranslationDict } from './index';

export interface LanguageContextValue {
  locale: string;
  localeInfo: LolLocaleOption;
  setLocale: (code: string) => void;
  t: TranslationDict;
}

export const LanguageContext = createContext<LanguageContextValue | null>(null);

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return ctx;
}
