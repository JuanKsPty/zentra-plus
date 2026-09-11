// Tailwind v4 se enchufa por PostCSS con su propio plugin.
// NO es el plugin `tailwindcss` de siempre: ese es el de la v3 y aqui falla.
export default {
  plugins: ['@tailwindcss/postcss'],
};
