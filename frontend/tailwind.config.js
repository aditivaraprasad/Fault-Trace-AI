/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        control: {
          bg: '#0B1120',
          panel: '#0F172A',
          card: '#1E293B',
          hover: '#283548',
          border: '#334155',
        },
        bescom: {
          orange: '#F97316',
          orangeDark: '#EA580C',
          blue: '#0284C7',
          navy: '#0B1120',
          amber: '#F59E0B',
          red: '#EF4444',
          green: '#10B981',
          slate: '#1E293B'
        }
      }
    },
  },
  plugins: [],
}
