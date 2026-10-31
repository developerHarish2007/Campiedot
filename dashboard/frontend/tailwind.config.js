/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        palette: {
          coral: '#ec9665',
          peach: '#f4aa7f',
          espresso: '#523624',
          caramel: '#9c6c4c',
          sand: '#d8bca4',
          umber: '#5f493b',
          darkest: '#180f0a',
          dark: '#24160f',
          surface: '#331f16',
          card: 'rgba(82, 54, 36, 0.60)',
          cardHover: 'rgba(95, 73, 59, 0.75)',
          glass: 'rgba(82, 54, 36, 0.45)',
          glassBorder: 'rgba(216, 188, 164, 0.22)',
        },
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        bounce: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
      },
    },
  },
  plugins: [],
}
