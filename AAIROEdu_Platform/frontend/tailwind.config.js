/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f5f0ff',
          100: '#e9ddff',
          200: '#d4bdff',
          300: '#b792ff',
          400: '#995fff',
          500: '#7b35ff',
          600: '#5e16f5',
          700: '#4d00ef',
          800: '#3d00bd',
          900: '#2b0084',
        },
        navy: {
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
