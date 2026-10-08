// Análisis de enlaces de YouTube. No hace red: solo valida la URL y extrae identificadores.

export type EnlaceYouTube =
  | { tipo: "video"; videoId: string; listaId?: string; inicio?: number }
  | { tipo: "playlist"; listaId: string };

const HOSTS_PERMITIDOS = new Set([
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "gaming.youtube.com",
  "youtu.be",
  "www.youtu.be",
  "youtube-nocookie.com",
  "www.youtube-nocookie.com",
]);

export const RE_VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
export const RE_LISTA_ID = /^[A-Za-z0-9_-]{10,}$/;

/** Convierte "1h2m3s", "90s" o "90" en segundos. Devuelve undefined si no es válido. */
export function analizarTiempo(valor: string | null): number | undefined {
  if (!valor) return undefined;
  const limpio = valor.trim().toLowerCase();
  if (/^\d+s?$/.test(limpio)) return Number.parseInt(limpio, 10);
  const partes = limpio.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/);
  if (!partes || limpio === "") return undefined;
  const [, h, m, s] = partes;
  const total = Number(h ?? 0) * 3600 + Number(m ?? 0) * 60 + Number(s ?? 0);
  return Number.isFinite(total) && total > 0 ? total : undefined;
}

function normalizarEntrada(entrada: string): URL | null {
  let texto = entrada.trim();
  if (texto === "") return null;
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(texto)) texto = `https://${texto}`;
  let url: URL;
  try {
    url = new URL(texto);
  } catch {
    return null;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return null;
  if (!HOSTS_PERMITIDOS.has(url.hostname.toLowerCase())) return null;
  return url;
}

/**
 * Interpreta un enlace de YouTube (watch, youtu.be, shorts, live, embed, playlist, con o sin
 * parámetros extra). Devuelve null si el enlace no es de YouTube o no contiene un identificador.
 */
export function analizarEnlace(entrada: string): EnlaceYouTube | null {
  const url = normalizarEntrada(entrada);
  if (!url) return null;

  const host = url.hostname.toLowerCase();
  const segmentos = url.pathname.split("/").filter(Boolean);
  const listaParam = url.searchParams.get("list");
  const listaId = listaParam && RE_LISTA_ID.test(listaParam) ? listaParam : undefined;
  const inicio = analizarTiempo(url.searchParams.get("t") ?? url.searchParams.get("start"));

  let videoId: string | undefined;
  if (host === "youtu.be" || host === "www.youtu.be") {
    videoId = segmentos[0];
  } else if (segmentos[0] === "watch") {
    videoId = url.searchParams.get("v") ?? undefined;
  } else if (
    segmentos.length >= 2 &&
    ["shorts", "embed", "live", "v", "e"].includes(segmentos[0] ?? "")
  ) {
    videoId = segmentos[1];
  } else if (segmentos[0] === "attribution_link") {
    const interno = url.searchParams.get("u");
    if (interno) return analizarEnlace(`https://www.youtube.com${interno}`);
  }

  if (videoId && RE_VIDEO_ID.test(videoId)) {
    const resultado: EnlaceYouTube = { tipo: "video", videoId };
    if (listaId) resultado.listaId = listaId;
    if (inicio !== undefined) resultado.inicio = inicio;
    return resultado;
  }
  if (listaId && (segmentos[0] === "playlist" || segmentos[0] === "watch" || segmentos.length === 0)) {
    return { tipo: "playlist", listaId };
  }
  if (listaId && segmentos[0] === "embed" && segmentos[1] === "videoseries") {
    return { tipo: "playlist", listaId };
  }
  return null;
}

export function urlCanonicaVideo(videoId: string): string {
  return `https://www.youtube.com/watch?v=${videoId}`;
}

export function urlCanonicaPlaylist(listaId: string): string {
  return `https://www.youtube.com/playlist?list=${listaId}`;
}

export function urlEmbed(videoId: string, opciones: { inicio?: number; listaId?: string } = {}): string {
  const params = new URLSearchParams({ rel: "0", enablejsapi: "1" });
  if (opciones.inicio) params.set("start", String(Math.floor(opciones.inicio)));
  if (opciones.listaId) params.set("list", opciones.listaId);
  return `https://www.youtube-nocookie.com/embed/${videoId}?${params.toString()}`;
}

export function urlEmbedPlaylist(listaId: string): string {
  const params = new URLSearchParams({ list: listaId, rel: "0", enablejsapi: "1" });
  return `https://www.youtube-nocookie.com/embed/videoseries?${params.toString()}`;
}

/** Las listas "RD..." son mezclas generadas por YouTube para cada usuario y la API no las expone. */
export function esMezclaAutomatica(listaId: string): boolean {
  return listaId.startsWith("RD");
}
