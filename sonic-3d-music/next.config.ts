import type { NextConfig } from "next";

const esProduccion = process.env.NODE_ENV === "production";

// Política de seguridad de contenido. El núcleo de FFmpeg es WebAssembly ('wasm-unsafe-eval') y
// corre en un Web Worker del mismo origen; el reproductor oficial de YouTube se incrusta como
// iframe (dominio sin cookies) y las miniaturas vienen de los dominios oficiales de imágenes.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'${esProduccion ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://i.ytimg.com https://*.ytimg.com https://yt3.ggpht.com https://*.googleusercontent.com",
  "media-src 'self' blob: data:",
  "font-src 'self' data:",
  `connect-src 'self' blob: data:${esProduccion ? "" : " ws: wss:"}`,
  "worker-src 'self' blob:",
  "frame-src https://www.youtube-nocookie.com https://www.youtube.com",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'self'",
].join("; ");

const cabecerasSeguridad = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  { key: "X-DNS-Prefetch-Control", value: "on" },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // NEXT_OUTPUT=standalone lo usa el Dockerfile; Netlify no lo necesita.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  async headers() {
    return [
      { source: "/(.*)", headers: cabecerasSeguridad },
      {
        // El núcleo de FFmpeg no cambia entre despliegues de la misma versión: caché larga.
        source: "/ffmpeg/:ruta*",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ];
  },
};

export default nextConfig;
