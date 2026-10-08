export type FuenteMetadatos = "data-api" | "oembed";

export interface VideoInfo {
  tipo: "video";
  id: string;
  url: string;
  titulo: string;
  canal: string;
  canalUrl?: string;
  miniatura: string;
  duracionSeg: number | null;
  descripcion: string;
  publicado?: string;
  vistas?: number;
  embebible: boolean;
  privacidad?: "public" | "unlisted" | "private";
  enVivo: boolean;
  licencia?: "youtube" | "creativeCommon";
  restriccionRegional: boolean;
  fuente: FuenteMetadatos;
  listaId?: string;
  inicio?: number;
}

export interface ElementoPlaylist {
  videoId: string;
  titulo: string;
  canal: string;
  miniatura: string;
  duracionSeg: number | null;
  posicion: number;
  disponible: boolean;
}

export interface PlaylistInfo {
  tipo: "playlist";
  id: string;
  url: string;
  titulo: string;
  canal: string;
  miniatura: string;
  descripcion: string;
  cantidad: number;
  elementos: ElementoPlaylist[];
  truncado: boolean;
  fuente: FuenteMetadatos;
}

export type ResultadoAnalisis = VideoInfo | PlaylistInfo;

export type CodigoErrorYouTube =
  | "enlace_invalido"
  | "no_encontrado"
  | "privado"
  | "mezcla_no_soportada"
  | "cuota"
  | "api"
  | "red"
  | "limite";

export interface RespuestaError {
  error: string;
  codigo: CodigoErrorYouTube;
}
