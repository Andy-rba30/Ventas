// Consulta de metadatos mediante medios oficiales: YouTube Data API v3 (con clave en el servidor)
// o, sin clave, el endpoint público oEmbed de YouTube. Solo se piden identificadores ya validados;
// nunca se descarga ni se extrae contenido multimedia.
import { duracionISOaSegundos } from "./duration";
import { esMezclaAutomatica, urlCanonicaPlaylist, urlCanonicaVideo } from "./parse";
import type { CodigoErrorYouTube, ElementoPlaylist, PlaylistInfo, VideoInfo } from "./types";

export class ErrorYouTube extends Error {
  constructor(
    mensaje: string,
    public readonly codigo: CodigoErrorYouTube,
    public readonly estado: number,
  ) {
    super(mensaje);
    this.name = "ErrorYouTube";
  }
}

export type Fetch = typeof fetch;

export interface OpcionesApi {
  apiKey?: string;
  fetch?: Fetch;
  maxElementosLista?: number;
}

const BASE = "https://www.googleapis.com/youtube/v3";
const OEMBED = "https://www.youtube.com/oembed";
const TIEMPO_MAXIMO_MS = 10_000;

interface Miniaturas {
  maxres?: { url: string };
  standard?: { url: string };
  high?: { url: string };
  medium?: { url: string };
  default?: { url: string };
}

function mejorMiniatura(m: Miniaturas | undefined, videoId?: string): string {
  const url = m?.maxres?.url ?? m?.standard?.url ?? m?.high?.url ?? m?.medium?.url ?? m?.default?.url;
  if (url) return url;
  return videoId ? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg` : "";
}

async function pedirJson<T>(url: string, hacerFetch: Fetch): Promise<{ estado: number; datos: T | null }> {
  const controlador = new AbortController();
  const temporizador = setTimeout(() => controlador.abort(), TIEMPO_MAXIMO_MS);
  try {
    const respuesta = await hacerFetch(url, {
      signal: controlador.signal,
      headers: { accept: "application/json" },
    });
    let datos: T | null = null;
    try {
      datos = (await respuesta.json()) as T;
    } catch {
      datos = null;
    }
    return { estado: respuesta.status, datos };
  } catch (error) {
    const motivo = error instanceof Error && error.name === "AbortError" ? "tiempo de espera agotado" : "sin conexión";
    throw new ErrorYouTube(`No se pudo contactar con YouTube (${motivo}).`, "red", 502);
  } finally {
    clearTimeout(temporizador);
  }
}

interface ErrorDataApi {
  error?: { code?: number; message?: string; errors?: { reason?: string }[] };
}

function interpretarErrorDataApi(estado: number, datos: ErrorDataApi | null): ErrorYouTube {
  const razon = datos?.error?.errors?.[0]?.reason ?? "";
  if (estado === 403 && /quota/i.test(razon)) {
    return new ErrorYouTube("La cuota diaria de la YouTube Data API se agotó. Inténtalo más tarde.", "cuota", 503);
  }
  if (estado === 400 || estado === 403) {
    return new ErrorYouTube("La clave de YouTube Data API no es válida o no tiene permisos.", "api", 502);
  }
  if (estado === 404) {
    return new ErrorYouTube("El contenido no existe o no está disponible.", "no_encontrado", 404);
  }
  return new ErrorYouTube(`YouTube respondió con un error (${estado}).`, "api", 502);
}

// ---- Data API -------------------------------------------------------------------------------

interface VideoDataApi {
  id: string;
  snippet?: {
    title?: string;
    description?: string;
    channelTitle?: string;
    channelId?: string;
    publishedAt?: string;
    thumbnails?: Miniaturas;
    liveBroadcastContent?: string;
  };
  contentDetails?: {
    duration?: string;
    regionRestriction?: { blocked?: string[]; allowed?: string[] };
  };
  status?: { embeddable?: boolean; privacyStatus?: string; license?: string };
  statistics?: { viewCount?: string };
}

export async function obtenerVideoDataApi(videoId: string, apiKey: string, hacerFetch: Fetch): Promise<VideoInfo> {
  const params = new URLSearchParams({
    part: "snippet,contentDetails,status,statistics",
    id: videoId,
    key: apiKey,
  });
  const { estado, datos } = await pedirJson<{ items?: VideoDataApi[] } & ErrorDataApi>(
    `${BASE}/videos?${params}`,
    hacerFetch,
  );
  if (estado !== 200) throw interpretarErrorDataApi(estado, datos);
  const item = datos?.items?.[0];
  if (!item) {
    throw new ErrorYouTube("El video no existe, es privado o fue eliminado.", "no_encontrado", 404);
  }
  const snippet = item.snippet ?? {};
  const privacidad = item.status?.privacyStatus as VideoInfo["privacidad"];
  const restriccion = item.contentDetails?.regionRestriction;
  return {
    tipo: "video",
    id: item.id,
    url: urlCanonicaVideo(item.id),
    titulo: snippet.title ?? "(sin título)",
    canal: snippet.channelTitle ?? "",
    canalUrl: snippet.channelId ? `https://www.youtube.com/channel/${snippet.channelId}` : undefined,
    miniatura: mejorMiniatura(snippet.thumbnails, item.id),
    duracionSeg: duracionISOaSegundos(item.contentDetails?.duration),
    descripcion: snippet.description ?? "",
    publicado: snippet.publishedAt,
    vistas: item.statistics?.viewCount ? Number(item.statistics.viewCount) : undefined,
    embebible: item.status?.embeddable !== false,
    privacidad,
    enVivo: snippet.liveBroadcastContent === "live",
    licencia: item.status?.license === "creativeCommon" ? "creativeCommon" : "youtube",
    restriccionRegional: Boolean(restriccion?.blocked?.length || restriccion?.allowed?.length),
    fuente: "data-api",
  };
}

interface PlaylistDataApi {
  id: string;
  snippet?: { title?: string; description?: string; channelTitle?: string; thumbnails?: Miniaturas };
  contentDetails?: { itemCount?: number };
}

interface PlaylistItemDataApi {
  snippet?: {
    title?: string;
    position?: number;
    thumbnails?: Miniaturas;
    videoOwnerChannelTitle?: string;
    resourceId?: { videoId?: string };
  };
  status?: { privacyStatus?: string };
}

export async function obtenerPlaylistDataApi(
  listaId: string,
  apiKey: string,
  hacerFetch: Fetch,
  maxElementos = 200,
): Promise<PlaylistInfo> {
  if (esMezclaAutomatica(listaId)) {
    throw new ErrorYouTube(
      "Las mezclas automáticas de YouTube (listas RD...) son personales y la API no las expone. Pega una lista de reproducción pública.",
      "mezcla_no_soportada",
      422,
    );
  }
  const paramsLista = new URLSearchParams({ part: "snippet,contentDetails", id: listaId, key: apiKey });
  const lista = await pedirJson<{ items?: PlaylistDataApi[] } & ErrorDataApi>(
    `${BASE}/playlists?${paramsLista}`,
    hacerFetch,
  );
  if (lista.estado !== 200) throw interpretarErrorDataApi(lista.estado, lista.datos);
  const cabecera = lista.datos?.items?.[0];
  if (!cabecera) {
    throw new ErrorYouTube("La lista de reproducción no existe o es privada.", "no_encontrado", 404);
  }

  const elementos: ElementoPlaylist[] = [];
  let pageToken: string | undefined;
  let truncado = false;
  do {
    const params = new URLSearchParams({
      part: "snippet,status",
      playlistId: listaId,
      maxResults: "50",
      key: apiKey,
    });
    if (pageToken) params.set("pageToken", pageToken);
    const pagina = await pedirJson<
      { items?: PlaylistItemDataApi[]; nextPageToken?: string } & ErrorDataApi
    >(`${BASE}/playlistItems?${params}`, hacerFetch);
    if (pagina.estado !== 200) throw interpretarErrorDataApi(pagina.estado, pagina.datos);
    for (const item of pagina.datos?.items ?? []) {
      const videoId = item.snippet?.resourceId?.videoId;
      if (!videoId) continue;
      const titulo = item.snippet?.title ?? "";
      const disponible =
        item.status?.privacyStatus !== "private" && titulo !== "Deleted video" && titulo !== "Private video";
      elementos.push({
        videoId,
        titulo: titulo || "(sin título)",
        canal: item.snippet?.videoOwnerChannelTitle ?? "",
        miniatura: mejorMiniatura(item.snippet?.thumbnails, videoId),
        duracionSeg: null,
        posicion: item.snippet?.position ?? elementos.length,
        disponible,
      });
    }
    pageToken = pagina.datos?.nextPageToken;
    if (pageToken && elementos.length >= maxElementos) {
      truncado = true;
      break;
    }
  } while (pageToken);

  // Duraciones: la API las da por video, en lotes de 50.
  const ids = elementos.filter((e) => e.disponible).map((e) => e.videoId);
  for (let i = 0; i < ids.length; i += 50) {
    const lote = ids.slice(i, i + 50);
    const params = new URLSearchParams({ part: "contentDetails", id: lote.join(","), key: apiKey });
    const videos = await pedirJson<{ items?: VideoDataApi[] } & ErrorDataApi>(
      `${BASE}/videos?${params}`,
      hacerFetch,
    );
    if (videos.estado !== 200) throw interpretarErrorDataApi(videos.estado, videos.datos);
    const duraciones = new Map<string, number | null>();
    for (const v of videos.datos?.items ?? []) {
      duraciones.set(v.id, duracionISOaSegundos(v.contentDetails?.duration));
    }
    for (const e of elementos) {
      if (duraciones.has(e.videoId)) e.duracionSeg = duraciones.get(e.videoId) ?? null;
    }
  }

  return {
    tipo: "playlist",
    id: cabecera.id,
    url: urlCanonicaPlaylist(cabecera.id),
    titulo: cabecera.snippet?.title ?? "(sin título)",
    canal: cabecera.snippet?.channelTitle ?? "",
    miniatura: mejorMiniatura(cabecera.snippet?.thumbnails, elementos[0]?.videoId),
    descripcion: cabecera.snippet?.description ?? "",
    cantidad: cabecera.contentDetails?.itemCount ?? elementos.length,
    elementos,
    truncado,
    fuente: "data-api",
  };
}

// ---- oEmbed (sin clave) ----------------------------------------------------------------------

interface RespuestaOEmbed {
  title?: string;
  author_name?: string;
  author_url?: string;
  thumbnail_url?: string;
}

async function pedirOEmbed(urlContenido: string, hacerFetch: Fetch): Promise<RespuestaOEmbed> {
  const params = new URLSearchParams({ url: urlContenido, format: "json" });
  const { estado, datos } = await pedirJson<RespuestaOEmbed>(`${OEMBED}?${params}`, hacerFetch);
  if (estado === 200 && datos) return datos;
  if (estado === 401 || estado === 403) {
    throw new ErrorYouTube("El contenido es privado o no permite incrustarse.", "privado", 403);
  }
  if (estado === 404 || estado === 400) {
    throw new ErrorYouTube("El contenido no existe o no está disponible.", "no_encontrado", 404);
  }
  throw new ErrorYouTube(`YouTube respondió con un error (${estado}).`, "api", 502);
}

export async function obtenerVideoOEmbed(videoId: string, hacerFetch: Fetch): Promise<VideoInfo> {
  const datos = await pedirOEmbed(urlCanonicaVideo(videoId), hacerFetch);
  return {
    tipo: "video",
    id: videoId,
    url: urlCanonicaVideo(videoId),
    titulo: datos.title ?? "(sin título)",
    canal: datos.author_name ?? "",
    canalUrl: datos.author_url,
    miniatura: datos.thumbnail_url ?? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
    duracionSeg: null,
    descripcion: "",
    embebible: true,
    enVivo: false,
    restriccionRegional: false,
    fuente: "oembed",
  };
}

export async function obtenerPlaylistOEmbed(listaId: string, hacerFetch: Fetch): Promise<PlaylistInfo> {
  if (esMezclaAutomatica(listaId)) {
    throw new ErrorYouTube(
      "Las mezclas automáticas de YouTube (listas RD...) son personales y no se pueden consultar.",
      "mezcla_no_soportada",
      422,
    );
  }
  const datos = await pedirOEmbed(urlCanonicaPlaylist(listaId), hacerFetch);
  return {
    tipo: "playlist",
    id: listaId,
    url: urlCanonicaPlaylist(listaId),
    titulo: datos.title ?? "(sin título)",
    canal: datos.author_name ?? "",
    miniatura: datos.thumbnail_url ?? "",
    descripcion: "",
    cantidad: 0,
    elementos: [],
    truncado: false,
    fuente: "oembed",
  };
}

// ---- Punto de entrada ------------------------------------------------------------------------

export async function obtenerVideo(videoId: string, opciones: OpcionesApi = {}): Promise<VideoInfo> {
  const hacerFetch = opciones.fetch ?? fetch;
  return opciones.apiKey
    ? obtenerVideoDataApi(videoId, opciones.apiKey, hacerFetch)
    : obtenerVideoOEmbed(videoId, hacerFetch);
}

export async function obtenerPlaylist(listaId: string, opciones: OpcionesApi = {}): Promise<PlaylistInfo> {
  const hacerFetch = opciones.fetch ?? fetch;
  return opciones.apiKey
    ? obtenerPlaylistDataApi(listaId, opciones.apiKey, hacerFetch, opciones.maxElementosLista)
    : obtenerPlaylistOEmbed(listaId, hacerFetch);
}
