// Formatos y calidades del convertidor y su traducción a argumentos de FFmpeg. La conversión
// nunca mejora la calidad original: recodificar con más bitrate solo conserva lo que ya había.

export type Formato = "mp3" | "wav" | "flac" | "m4a" | "ogg";

export interface OpcionCalidad {
  id: string;
  etiqueta: string;
  detalle: string;
}

export interface DefinicionFormato {
  id: Formato;
  etiqueta: string;
  extension: string;
  mime: string;
  descripcion: string;
  conPerdida: boolean;
  calidades: OpcionCalidad[];
  calidadPorDefecto: string;
}

export const FORMATOS: Record<Formato, DefinicionFormato> = {
  mp3: {
    id: "mp3",
    etiqueta: "MP3",
    extension: "mp3",
    mime: "audio/mpeg",
    descripcion: "Compatible con todo. Codificador LAME.",
    conPerdida: true,
    calidadPorDefecto: "320",
    calidades: [
      { id: "128", etiqueta: "128 kbps", detalle: "Ligero, ideal para voz" },
      { id: "192", etiqueta: "192 kbps", detalle: "Equilibrado" },
      { id: "256", etiqueta: "256 kbps", detalle: "Alta calidad" },
      { id: "320", etiqueta: "320 kbps", detalle: "Máxima calidad MP3" },
    ],
  },
  wav: {
    id: "wav",
    etiqueta: "WAV",
    extension: "wav",
    mime: "audio/wav",
    descripcion: "PCM sin compresión. Archivos grandes.",
    conPerdida: false,
    calidadPorDefecto: "16-44100",
    calidades: [
      { id: "16-44100", etiqueta: "16 bits · 44.1 kHz", detalle: "Calidad CD" },
      { id: "16-48000", etiqueta: "16 bits · 48 kHz", detalle: "Estándar de video" },
      { id: "24-48000", etiqueta: "24 bits · 48 kHz", detalle: "Estudio" },
      { id: "24-96000", etiqueta: "24 bits · 96 kHz", detalle: "Alta resolución" },
    ],
  },
  flac: {
    id: "flac",
    etiqueta: "FLAC",
    extension: "flac",
    mime: "audio/flac",
    descripcion: "Sin pérdida y comprimido.",
    conPerdida: false,
    calidadPorDefecto: "5",
    calidades: [
      { id: "0", etiqueta: "Nivel 0", detalle: "Más rápido, menos compresión" },
      { id: "5", etiqueta: "Nivel 5", detalle: "Equilibrado (recomendado)" },
      { id: "8", etiqueta: "Nivel 8", detalle: "Máxima compresión, más lento" },
    ],
  },
  m4a: {
    id: "m4a",
    etiqueta: "AAC / M4A",
    extension: "m4a",
    mime: "audio/mp4",
    descripcion: "AAC en contenedor MP4. Apple y móviles.",
    conPerdida: true,
    calidadPorDefecto: "192",
    calidades: [
      { id: "128", etiqueta: "128 kbps", detalle: "Ligero" },
      { id: "192", etiqueta: "192 kbps", detalle: "Equilibrado" },
      { id: "256", etiqueta: "256 kbps", detalle: "Alta calidad" },
    ],
  },
  ogg: {
    id: "ogg",
    etiqueta: "OGG Vorbis",
    extension: "ogg",
    mime: "audio/ogg",
    descripcion: "Libre y eficiente. Calidad variable (VBR).",
    conPerdida: true,
    calidadPorDefecto: "6",
    calidades: [
      { id: "4", etiqueta: "q4 (~128 kbps)", detalle: "Ligero" },
      { id: "6", etiqueta: "q6 (~192 kbps)", detalle: "Equilibrado" },
      { id: "8", etiqueta: "q8 (~256 kbps)", detalle: "Alta calidad" },
      { id: "10", etiqueta: "q10 (~500 kbps)", detalle: "Máxima" },
    ],
  },
};

export const LISTA_FORMATOS: DefinicionFormato[] = Object.values(FORMATOS);

export function esFormato(valor: string): valor is Formato {
  return valor in FORMATOS;
}

export function calidadValida(formato: Formato, calidad: string): string {
  const def = FORMATOS[formato];
  return def.calidades.some((c) => c.id === calidad) ? calidad : def.calidadPorDefecto;
}

/** Argumentos de FFmpeg que van entre `-i entrada` y el nombre de salida. */
export function argumentosFFmpeg(formato: Formato, calidad: string): string[] {
  const c = calidadValida(formato, calidad);
  const comunes = ["-vn", "-map_metadata", "0"];
  switch (formato) {
    case "mp3":
      return [...comunes, "-c:a", "libmp3lame", "-b:a", `${c}k`, "-id3v2_version", "3"];
    case "wav": {
      const [bits, frecuencia] = c.split("-");
      return [...comunes, "-c:a", bits === "24" ? "pcm_s24le" : "pcm_s16le", "-ar", frecuencia ?? "44100"];
    }
    case "flac":
      return [...comunes, "-c:a", "flac", "-compression_level", c];
    case "m4a":
      return [...comunes, "-c:a", "aac", "-b:a", `${c}k`, "-movflags", "+faststart"];
    case "ogg":
      return [...comunes, "-c:a", "libvorbis", "-q:a", c];
  }
}

export function etiquetaCalidad(formato: Formato, calidad: string): string {
  const def = FORMATOS[formato];
  return def.calidades.find((c) => c.id === calidad)?.etiqueta ?? calidad;
}
