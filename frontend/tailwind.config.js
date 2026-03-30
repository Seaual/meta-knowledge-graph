/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'display': ['Playfair Display', 'Georgia', 'serif'],
        'body': ['Source Sans 3', 'system-ui', 'sans-serif'],
        'mono': ['IBM Plex Mono', 'monospace'],
        'quote': ['Crimson Pro', 'Georgia', 'serif'],
      },
      colors: {
        // Academic Warm Palette
        academic: {
          // Backgrounds - cream, paper, canvas tones
          cream: '#faf8f5',
          paper: '#f5f0e8',
          canvas: '#ebe5d8',
          vellum: '#fffef9',

          // Text - ink, sepia tones
          ink: '#2c1810',
          sepia: '#6b4423',
          muted: '#8a7a6a',
          faint: '#a89a8a',

          // Accent - amber, gold, terracotta
          amber: '#b8860b',
          gold: '#d4a012',
          terracotta: '#c2410c',
          copper: '#9a6b3c',

          // Borders
          border: '#e8dfd0',
          'border-medium': '#d4c4b0',
          'border-dark': '#b8a890',
        },
        // Semantic colors for status
        status: {
          pending: '#b8860b',      // amber
          processing: '#6b4423',   // sepia
          success: '#2d5a27',      // forest green
          error: '#a33b3b',        // warm red
          info: '#4a6b8a',         // slate blue
        },
        // Graph node colors (warm palette)
        graph: {
          field: '#6b4423',        // sepia
          direction: '#b8860b',    // amber
          subdirection: '#9a6b3c', // copper
          task: '#4a6b8a',         // slate
          method: '#c2410c',       // terracotta
          technique: '#2d5a27',    // forest
          paper: '#2c1810',        // ink
          center: '#d4a012',       // gold
        },
      },
      boxShadow: {
        'paper': '0 1px 3px rgba(44, 24, 16, 0.04), 0 1px 2px rgba(44, 24, 16, 0.06)',
        'card': '0 2px 8px rgba(44, 24, 16, 0.06), 0 1px 3px rgba(44, 24, 16, 0.08)',
        'elevated': '0 8px 24px rgba(44, 24, 16, 0.08), 0 4px 12px rgba(44, 24, 16, 0.10)',
        'modal': '0 16px 48px rgba(44, 24, 16, 0.12), 0 8px 24px rgba(44, 24, 16, 0.14)',
        'inner-soft': 'inset 0 1px 2px rgba(44, 24, 16, 0.04)',
        'glow-amber': '0 0 12px rgba(184, 134, 11, 0.24)',
        'glow-gold': '0 0 16px rgba(212, 160, 18, 0.28)',
      },
      borderRadius: {
        'soft': '6px',
        'medium': '10px',
        'large': '14px',
        'xlarge': '20px',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      backgroundImage: {
        'paper-texture': "url(\"data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E\")",
        'paper-lines': "repeating-linear-gradient(0deg, transparent, transparent 27px, rgba(44, 24, 16, 0.02) 27px, rgba(44, 24, 16, 0.02) 28px)",
        'gradient-warm': 'linear-gradient(135deg, #faf8f5 0%, #f5f0e8 50%, #ebe5d8 100%)',
        'gradient-amber': 'linear-gradient(135deg, #b8860b 0%, #d4a012 100%)',
        'gradient-sepia': 'linear-gradient(135deg, #6b4423 0%, #9a6b3c 100%)',
      },
    },
  },
  plugins: [],
}