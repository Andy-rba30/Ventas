// Copia FFmpeg (WebAssembly) desde node_modules a public/ffmpeg para servirlo desde el mismo
// origen: el cargador UMD de @ffmpeg/ffmpeg (ffmpeg.js + su worker 814.ffmpeg.js) y el núcleo
// de un solo hilo de @ffmpeg/core (no necesita SharedArrayBuffer ni cabeceras COOP/COEP, así
// el reproductor oficial de YouTube sigue funcionando). Se ejecuta en postinstall y en build.
import { copyFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = dirname(dirname(fileURLToPath(import.meta.url)));
const destino = join(raiz, "public", "ffmpeg");
const fuentes = [
  [join(raiz, "node_modules", "@ffmpeg", "core", "dist", "umd"), ["ffmpeg-core.js", "ffmpeg-core.wasm"]],
  [join(raiz, "node_modules", "@ffmpeg", "ffmpeg", "dist", "umd"), ["ffmpeg.js", "814.ffmpeg.js"]],
];

mkdirSync(destino, { recursive: true });
for (const [origen, archivos] of fuentes) {
  if (!existsSync(origen)) {
    console.error(`[ffmpeg] No se encontró ${origen}. Ejecuta "npm install" primero.`);
    process.exit(1);
  }
  for (const nombre of archivos) {
    const desde = join(origen, nombre);
    if (!existsSync(desde)) {
      console.error(`[ffmpeg] Falta ${desde}`);
      process.exit(1);
    }
    const hacia = join(destino, nombre);
    copyFileSync(desde, hacia);
    console.log(`[ffmpeg] ${nombre} -> public/ffmpeg (${Math.round(statSync(hacia).size / 1024)} KB)`);
  }
}
