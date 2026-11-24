import { CORE_TRANSLATIONS, type TranslationDict as BaseTranslationDict } from './translationsCore';
import { EXTRA_TRANSLATIONS } from './translationsExtra';
import { ZERO_DAY_TRANSLATIONS, type ZeroDayTranslationDict } from './translationsZeroDay';
import type { LangBundleKey } from './locales';

export type TranslationDict = BaseTranslationDict & ZeroDayTranslationDict;
export { LOL_LOCALES, DEFAULT_LOCALE_CODE, getLocaleOption, type LolLocaleOption, type LangBundleKey } from './locales';

const BASE_TRANSLATIONS = {
  ...CORE_TRANSLATIONS,
  ...EXTRA_TRANSLATIONS,
};

export const TRANSLATIONS: Record<LangBundleKey, TranslationDict> = Object.fromEntries(
  (Object.keys(BASE_TRANSLATIONS) as LangBundleKey[]).map((key) => [
    key,
    {
      ...BASE_TRANSLATIONS[key],
      ...ZERO_DAY_TRANSLATIONS[key],
    },
  ])
) as Record<LangBundleKey, TranslationDict>;
