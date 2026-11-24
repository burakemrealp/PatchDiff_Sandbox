import { CORE_TRANSLATIONS, type TranslationDict } from './translationsCore';
import { EXTRA_TRANSLATIONS } from './translationsExtra';
import type { LangBundleKey } from './locales';

export type { TranslationDict } from './translationsCore';
export { LOL_LOCALES, DEFAULT_LOCALE_CODE, getLocaleOption, type LolLocaleOption, type LangBundleKey } from './locales';

export const TRANSLATIONS: Record<LangBundleKey, TranslationDict> = {
  ...CORE_TRANSLATIONS,
  ...EXTRA_TRANSLATIONS,
};
