import React, { createContext, useContext, useState, useCallback } from "react";
import { zh, Translation } from "./zh";
import { en } from "./en";

type Language = "zh" | "en";

const translations: Record<Language, Translation> = { zh, en };

interface I18nContextType {
  language: Language;
  t: Translation;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

const LANGUAGE_KEY = "mkg_language";

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    // Try to get saved language from localStorage
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(LANGUAGE_KEY) as Language | null;
      if (saved && (saved === "zh" || saved === "en")) {
        return saved;
      }
    }
    // Default to browser language or Chinese
    if (typeof window !== "undefined") {
      const browserLang = navigator.language.toLowerCase();
      if (browserLang.startsWith("zh")) {
        return "zh";
      }
    }
    return "en";
  });

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem(LANGUAGE_KEY, lang);
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguage(language === "zh" ? "en" : "zh");
  }, [language, setLanguage]);

  const t = translations[language];

  return (
    <I18nContext.Provider value={{ language, t, setLanguage, toggleLanguage }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useTranslation must be used within an I18nProvider");
  }
  return context;
}

export { I18nContext };

export function getLanguage(): string {
  return typeof window !== "undefined"
    ? (localStorage.getItem(LANGUAGE_KEY) || "zh")
    : "zh";
}
