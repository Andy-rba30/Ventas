// Validación de archivos subidos por la usuaria antes de convertirlos (en el navegador).
import { extensionDe } from "@/lib/utils/filename";

export const EXTENSIONES_PERMITIDAS = new Set([
  "mp3", "wav", "flac", "m4a", "aac", "ogg", "oga", "opus", "wma", "aiff", "aif", "alac", "amr", "mka",
  // contenedores de video: se extrae solo la pista de audio
  "mp4", "m4v", "mov", "webm", "mkv", "avi",
]);

export const TIPOS_MIME_PERMITIDOS = /^(audio\/|video\/|application\/ogg|application\/octet-stream)/;

export const ACEPTAR_INPUT = [...EXTENSIONES_PERMITIDAS].map((e) => `.${e}`).join(",") + ",audio/*,video/*";

export function limiteTamanoBytes(): number {
  const mb = Number(process.env.NEXT_PUBLIC_MAX_FILE_MB ?? 300);
  return (Number.isFinite(mb) && mb > 0 ? mb : 300) * 1024 * 1024;
}

export function limiteDuracionSeg(): number {
  const min = Number(process.env.NEXT_PUBLIC_MAX_DURATION_MIN ?? 180);
  return (Number.isFinite(min) && min > 0 ? min : 180) * 60;
}

export type ResultadoValidacionArchivo = { ok: true } | { ok: false; motivo: string };

export function validarArchivo(archivo: { name: string; size: number; type: string }): ResultadoValidacionArchivo {
  const ext = extensionDe(archivo.name);
  if (!EXTENSIONES_PERMITIDAS.has(ext)) {
    return { ok: false, motivo: `Formato .${ext || "?"} no admitido.` };
  }
  if (archivo.type && !TIPOS_MIME_PERMITIDOS.test(archivo.type)) {
    return { ok: false, motivo: `Tipo de archivo ${archivo.type} no admitido.` };
  }
  if (archivo.size <= 0) return { ok: false, motivo: "El archivo está vacío." };
  const limite = limiteTamanoBytes();
  if (archivo.size > limite) {
    return { ok: false, motivo: `Supera el máximo de ${Math.round(limite / 1024 / 1024)} MB.` };
  }
  return { ok: true };
}

/** Duración en segundos leyendo solo los metadatos con un elemento <audio> (sin decodificar). */
export function medirDuracion(archivo: Blob, tiempoMaximoMs = 8000): Promise<number | null> {
  if (typeof document === "undefined") return Promise.resolve(null);
  return new Promise((resolver) => {
    const url = URL.createObjectURL(archivo);
    const audio = document.createElement("audio");
    audio.preload = "metadata";
    const terminar = (valor: number | null) => {
      clearTimeout(temporizador);
      audio.removeAttribute("src");
      audio.load();
      URL.revokeObjectURL(url);
      resolver(valor);
    };
    const temporizador = setTimeout(() => terminar(null), tiempoMaximoMs);
    audio.onloadedmetadata = () => terminar(Number.isFinite(audio.duration) ? audio.duration : null);
    audio.onerror = () => terminar(null);
    audio.src = url;
  });
}
