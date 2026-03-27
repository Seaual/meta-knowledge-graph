/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
      },
      boxShadow: {
        'brand': '0 2px 8px rgba(99, 102, 241, 0.08)',
        'brand-lg': '0 4px 12px rgba(99, 102, 241, 0.1)',
        'brand-xl': '0 8px 24px rgba(99, 102, 241, 0.12)',
      },
    },
  },
  plugins: [],
}