import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from './locales/en.json';
import fa from './locales/fa.json';

const resources = {
  en: { translation: en },
  fa: { translation: fa },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
  resources,
  // Persian by default; a visitor's choice from the language switcher is remembered.
  // (A fixed `lng` here would override that choice on every page load.)
  fallbackLng: 'fa',
  supportedLngs: ['fa', 'en'],
  load: 'languageOnly',
  interpolation: {
    escapeValue: false,
  },
  detection: {
    order: ['localStorage'],
    caches: ['localStorage'],
  },
  react: {
    useSuspense: false,
  },
  });

export default i18n;
