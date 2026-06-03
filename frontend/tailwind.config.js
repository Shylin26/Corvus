/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'monospace'],
        display: ['"Share Tech Mono"', 'monospace'],
      },
      colors: {
        bg:      '#080A0C',
        surface: '#0D1117',
        border:  '#1C2128',
        dim:     '#21262D',
        muted:   '#484F58',
        text:    '#CDD9E5',
        subtle:  '#768390',
        green:   '#3FB950',
        amber:   '#D29922',
        red:     '#F85149',
        blue:    '#58A6FF',
        purple:  '#BC8CFF',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'blink': 'blink 1s step-end infinite',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0' },
        },
      },
    },
  },
  plugins: [],
}
