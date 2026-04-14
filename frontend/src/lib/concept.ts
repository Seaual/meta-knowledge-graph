import { getLanguage } from '../i18n';

export interface Concept {
  id: string;
  text: string;
  text_en?: string;
  text_zh?: string;
  concept?: string;
  category?: string;
  paper_count?: number;
  [key: string]: unknown;
}

export function getConceptDisplayName(concept: Concept): string {
  const lang = getLanguage();
  if (lang === 'en' && concept.text_en) {
    return concept.text_en;
  }
  return concept.concept || concept.text || 'Unnamed Concept';
}
