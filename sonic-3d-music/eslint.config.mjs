import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  globalIgnores([".next/**", "out/**", "public/**", "test-results/**", "playwright-report/**", "next-env.d.ts"]),
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // Las miniaturas de YouTube se muestran con <img> para no depender del optimizador de imágenes.
      "@next/next/no-img-element": "off",
    },
  },
]);
