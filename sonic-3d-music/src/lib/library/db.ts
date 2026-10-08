// Biblioteca local en IndexedDB: guarda los archivos convertidos (como Blob) y sus metadatos en
// el navegador de la usuaria. Nada sale del dispositivo.
import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import type { Formato } from "@/lib/audio/presets";

export interface PistaBiblioteca {
  id: string;
  nombre: string;
  formato: Formato;
  mime: string;
  tamano: number;
  duracionSeg: number | null;
  creadoEn: number;
  origen: "conversion" | "subida";
  nombreOrigen: string;
  calidad: string;
  blob: Blob;
}

export type PistaResumen = Omit<PistaBiblioteca, "blob">;

interface EsquemaSonic extends DBSchema {
  pistas: {
    key: string;
    value: PistaBiblioteca;
    indexes: { porFecha: number; porNombre: string };
  };
}

const NOMBRE_BD = "sonic-3d-music";
const VERSION = 1;
let bd: Promise<IDBPDatabase<EsquemaSonic>> | null = null;

export function bibliotecaDisponible(): boolean {
  return typeof indexedDB !== "undefined";
}

function abrir(): Promise<IDBPDatabase<EsquemaSonic>> {
  if (!bd) {
    bd = openDB<EsquemaSonic>(NOMBRE_BD, VERSION, {
      upgrade(db) {
        const pistas = db.createObjectStore("pistas", { keyPath: "id" });
        pistas.createIndex("porFecha", "creadoEn");
        pistas.createIndex("porNombre", "nombre");
      },
    });
  }
  return bd;
}

function sinBlob(p: PistaBiblioteca): PistaResumen {
  const { blob: _blob, ...resto } = p;
  void _blob;
  return resto;
}

export async function guardarPista(pista: PistaBiblioteca): Promise<void> {
  const db = await abrir();
  await db.put("pistas", pista);
}

export async function listarPistas(): Promise<PistaResumen[]> {
  const db = await abrir();
  const todas = await db.getAllFromIndex("pistas", "porFecha");
  return todas.reverse().map(sinBlob);
}

export async function obtenerPista(id: string): Promise<PistaBiblioteca | undefined> {
  const db = await abrir();
  return db.get("pistas", id);
}

export async function eliminarPista(id: string): Promise<void> {
  const db = await abrir();
  await db.delete("pistas", id);
}

export async function vaciarBiblioteca(): Promise<void> {
  const db = await abrir();
  await db.clear("pistas");
}

export async function usoAlmacenamiento(): Promise<{ usado: number; cuota: number } | null> {
  if (typeof navigator === "undefined" || !navigator.storage?.estimate) return null;
  try {
    const { usage, quota } = await navigator.storage.estimate();
    return { usado: usage ?? 0, cuota: quota ?? 0 };
  } catch {
    return null;
  }
}
