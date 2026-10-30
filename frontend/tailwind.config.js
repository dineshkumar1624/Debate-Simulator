/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#FAFAFC',
          elevated: '#FFFFFF',
          card: 'rgba(255, 255, 255, 0.85)',
          hover: 'rgba(241, 245, 249, 0.90)',
        },
        border: {
          subtle: 'rgba(15, 23, 42, 0.08)',
          glow: 'rgba(99, 102, 241, 0.18)',
        },
        primary: {
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
          DEFAULT: '#6366f1',
        },
        cyan: {
          50: '#ecfeff',
          400: '#22d3ee',
          500: '#06b6d4',
          DEFAULT: '#06b6d4',
        },
        debater: {
          pro: '#3b82f6',
          con: '#ec4899',
          judge: '#a855f7',
          evidence: '#10b981',
          synthesis: '#f59e0b',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow-line': 'glowLine 3s ease-in-out infinite alternate',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        glowLine: {
          '0%': { opacity: '0.3', strokeDashoffset: '0' },
          '100%': { opacity: '0.8', strokeDashoffset: '20' },
        },
      },
    },
  },
  plugins: [],
};
