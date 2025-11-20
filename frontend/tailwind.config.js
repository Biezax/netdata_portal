/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        netdata: {
          bg: '#272b30',
          'bg-panel': '#35393e',
          border: '#404448',
          'border-dark': '#4a4e52',
          accent: '#8CC63F',
          'accent-bright': '#44c442',
          'accent-light': '#bbf3bb',
          'accent-dim': 'rgba(140, 198, 63, 0.1)',
          warning: '#ffc107',
          critical: '#ed1c5e',
          'text-primary': '#ffffff',
          'text-secondary': '#c8c8c8',
          'text-muted': '#aaaaaa',
          'text-dim': '#888888',
          'alert-critical': '#4a1a1a',
          'alert-warning': '#4a3a00',
          'alert-info': '#2a2e33',
          'panel-bg': '#2a2e33',
        },
      },
    },
  },
  plugins: [],
};
