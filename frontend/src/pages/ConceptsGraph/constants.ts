// frontend/src/pages/ConceptsGraph/constants.ts

// Category colors - Academic Warm Palette
export const CATEGORY_COLORS: Record<string, string> = {
  field: '#6b4423',        // sepia
  direction: '#b8860b',    // amber
  subdirection: '#9a6b3c', // copper
  task: '#4a6b8a',         // slate blue
  method: '#c2410c',       // terracotta
  technique: '#2d5a27',    // forest green
  dataset: '#5c4d7d',      // purple
  finding: '#d4a012',      // gold
}

export const PAPER_COLOR = '#4a6b8a'
export const CENTER_COLOR = '#d4a012'

// Category-based sizes (decreasing by hierarchy level)
export const CATEGORY_SIZES: Record<string, number> = {
  field: 16,        // largest
  direction: 14,
  subdirection: 12,
  dataset: 12,      // medium (same as subdirection)
  finding: 12,      // medium (same as subdirection)
  task: 10,
  method: 8,
  technique: 6,     // smallest
}

// Category-based collision radius
export const CATEGORY_RADII: Record<string, number> = {
  field: 20,
  direction: 18,
  subdirection: 16,
  dataset: 16,
  finding: 16,
  task: 14,
  method: 12,
  technique: 10,
}

export const DEFAULT_CATEGORIES = [
  'field', 'direction', 'subdirection', 'task', 'method', 'technique', 'dataset', 'finding'
]