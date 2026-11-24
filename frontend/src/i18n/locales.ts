export type LangBundleKey =
  | 'tr'
  | 'en'
  | 'de'
  | 'es'
  | 'fr'
  | 'it'
  | 'pt'
  | 'pl'
  | 'ru'
  | 'cs'
  | 'el'
  | 'hu'
  | 'ro'
  | 'ar'
  | 'ja'
  | 'ko'
  | 'zh-TW'
  | 'th'
  | 'vi'
  | 'id';

export interface LolLocaleOption {
  /** Riot Data Dragon official locale code (e.g., 'tr_TR', 'en_US') */
  code: string;
  /** Official leagueoflegends.com hreflang code (e.g., 'tr-tr', 'en-us') */
  webCode: string;
  /** Native display name shown in the language grid */
  nativeName: string;
  /** Regional tag matching leagueoflegends.com (e.g., 'NA', 'EUW', 'LATAM') */
  region?: string;
  /** Translation dictionary bundle key */
  langKey: LangBundleKey;
  /** Text direction ('rtl' for Arabic, 'ltr' for all others) */
  dir: 'ltr' | 'rtl';
}

/**
 * Exact 25 official language/region options from leagueoflegends.com
 * (verified 1:1 against Riot Data Dragon languages.json & leagueoflegends.com hreflang).
 */
export const LOL_LOCALES: LolLocaleOption[] = [
  { code: 'tr_TR', webCode: 'tr-tr', nativeName: 'Türkçe', region: 'TR', langKey: 'tr', dir: 'ltr' },
  { code: 'en_US', webCode: 'en-us', nativeName: 'English', region: 'NA', langKey: 'en', dir: 'ltr' },
  { code: 'en_GB', webCode: 'en-gb', nativeName: 'English', region: 'EUW', langKey: 'en', dir: 'ltr' },
  { code: 'en_AU', webCode: 'en-au', nativeName: 'English', region: 'OCE', langKey: 'en', dir: 'ltr' },
  { code: 'en_PH', webCode: 'en-ph', nativeName: 'English', region: 'PH', langKey: 'en', dir: 'ltr' },
  { code: 'en_SG', webCode: 'en-sg', nativeName: 'English', region: 'SG', langKey: 'en', dir: 'ltr' },
  { code: 'de_DE', webCode: 'de-de', nativeName: 'Deutsch', region: 'EUW', langKey: 'de', dir: 'ltr' },
  { code: 'es_ES', webCode: 'es-es', nativeName: 'Español', region: 'EUW', langKey: 'es', dir: 'ltr' },
  { code: 'es_MX', webCode: 'es-mx', nativeName: 'Español', region: 'LATAM', langKey: 'es', dir: 'ltr' },
  { code: 'fr_FR', webCode: 'fr-fr', nativeName: 'Français', region: 'EUW', langKey: 'fr', dir: 'ltr' },
  { code: 'it_IT', webCode: 'it-it', nativeName: 'Italiano', region: 'EUW', langKey: 'it', dir: 'ltr' },
  { code: 'pt_BR', webCode: 'pt-br', nativeName: 'Português', region: 'BR', langKey: 'pt', dir: 'ltr' },
  { code: 'pl_PL', webCode: 'pl-pl', nativeName: 'Polski', region: 'EUNE', langKey: 'pl', dir: 'ltr' },
  { code: 'ru_RU', webCode: 'ru-ru', nativeName: 'Русский', region: 'RU', langKey: 'ru', dir: 'ltr' },
  { code: 'cs_CZ', webCode: 'cs-cz', nativeName: 'Čeština', region: 'EUNE', langKey: 'cs', dir: 'ltr' },
  { code: 'el_GR', webCode: 'el-gr', nativeName: 'Ελληνικά', region: 'EUNE', langKey: 'el', dir: 'ltr' },
  { code: 'hu_HU', webCode: 'hu-hu', nativeName: 'Magyar', region: 'EUNE', langKey: 'hu', dir: 'ltr' },
  { code: 'ro_RO', webCode: 'ro-ro', nativeName: 'Română', region: 'EUNE', langKey: 'ro', dir: 'ltr' },
  { code: 'ar_AE', webCode: 'ar-ae', nativeName: 'العربية', region: 'MENA', langKey: 'ar', dir: 'rtl' },
  { code: 'ja_JP', webCode: 'ja-jp', nativeName: '日本語', region: 'JP', langKey: 'ja', dir: 'ltr' },
  { code: 'ko_KR', webCode: 'ko-kr', nativeName: '한국어', region: 'KR', langKey: 'ko', dir: 'ltr' },
  { code: 'zh_TW', webCode: 'zh-tw', nativeName: '繁體中文', region: 'TW', langKey: 'zh-TW', dir: 'ltr' },
  { code: 'th_TH', webCode: 'th-th', nativeName: 'ภาษาไทย', region: 'TH', langKey: 'th', dir: 'ltr' },
  { code: 'vi_VN', webCode: 'vi-vn', nativeName: 'Tiếng Việt', region: 'VN', langKey: 'vi', dir: 'ltr' },
  { code: 'id_ID', webCode: 'id-id', nativeName: 'Bahasa Indonesia', region: 'ID', langKey: 'id', dir: 'ltr' },
];

export const DEFAULT_LOCALE_CODE = 'tr_TR';

export function getLocaleOption(code: string): LolLocaleOption {
  return LOL_LOCALES.find((l) => l.code === code) || LOL_LOCALES[0];
}
