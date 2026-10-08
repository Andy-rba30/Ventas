// Cliente de FFmpeg (WebAssembly) en el navegador. Carga el build UMD de @ffmpeg/ffmpeg desde
// /ffmpeg (mismo origen) para que su Web Worker clásico pueda importar el núcleo de un solo hilo.
// Una sola instancia: los trabajos se procesan en serie; cancelar termina el worker y se
// vuelve a cargar en el siguiente trabajo.
import type { FFmpeg } from "@ffmpeg/ffmpeg";
import { argumentosFFmpeg, FORMATOS, type Formato } from "./presets";
import { extensionDe } from "@/lib/utils/filename";

export type EstadoFFmpeg = "inactivo" | "cargando" | "listo" | "error";

export interface OpcionesConversion {
  archivo: Blob;
  nombreEntrada: string;
  formato: Formato;
  calidad: string;
  onProgreso?: (progreso: number, tiempoSeg: number) => void;
  onLog?: (linea: string) => void;
  signal?: AbortSignal;
}

export class ErrorCancelado extends Error {
  constructor() {
    super("Conversión cancelada.");
    this.name = "ErrorCancelado";
  }
}

function baseFFmpeg(): string {
  const base = process.env.NEXT_PUBLIC_FFMPEG_BASE_URL || "/ffmpeg";
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

function cargarScript(src: string): Promise<void> {
  return new Promise((resolver, rechazar) => {
    if (typeof document === "undefined") {
      rechazar(new Error("FFmpeg solo está disponible en el navegador."));
      return;
    }
    const existente = document.querySelector<HTMLScriptElement>(`script[data-sonic-ffmpeg]`);
    if (existente && window.FFmpegWASM) {
      resolver();
      return;
    }
    const script = existente ?? document.createElement("script");
    script.addEventListener("load", () => resolver(), { once: true });
    script.addEventListener("error", () => rechazar(new Error("No se pudo descargar el cargador de FFmpeg.")), {
      once: true,
    });
    if (!existente) {
      script.src = src;
      script.async = true;
      script.dataset.sonicFfmpeg = "1";
      document.head.appendChild(script);
    }
  });
}

class ClienteFFmpeg {
  private instancia: FFmpeg | null = null;
  private carga: Promise<FFmpeg> | null = null;
  private ocupado = false;
  private oyentes = new Set<(estado: EstadoFFmpeg) => void>();
  estado: EstadoFFmpeg = "inactivo";

  suscribir(oyente: (estado: EstadoFFmpeg) => void): () => void {
    this.oyentes.add(oyente);
    oyente(this.estado);
    return () => this.oyentes.delete(oyente);
  }

  private fijarEstado(estado: EstadoFFmpeg) {
    this.estado = estado;
    for (const o of this.oyentes) o(estado);
  }

  get disponible(): boolean {
    return typeof window !== "undefined" && typeof Worker !== "undefined" && typeof WebAssembly !== "undefined";
  }

  /** Descarga y arranca el núcleo (≈31 MB la primera vez; luego queda en caché del navegador). */
  cargar(): Promise<FFmpeg> {
    if (this.instancia) return Promise.resolve(this.instancia);
    if (this.carga) return this.carga;
    this.fijarEstado("cargando");
    const base = baseFFmpeg();
    const absoluta = (ruta: string) => new URL(`${base}/${ruta}`, window.location.href).href;
    this.carga = (async () => {
      try {
        await cargarScript(absoluta("ffmpeg.js"));
        const Clase = window.FFmpegWASM?.FFmpeg;
        if (!Clase) throw new Error("El cargador de FFmpeg no expuso la clase FFmpeg.");
        const ffmpeg = new Clase();
        await ffmpeg.load({ coreURL: absoluta("ffmpeg-core.js"), wasmURL: absoluta("ffmpeg-core.wasm") });
        this.instancia = ffmpeg;
        this.fijarEstado("listo");
        return ffmpeg;
      } catch (error) {
        this.carga = null;
        this.fijarEstado("error");
        throw error instanceof Error ? error : new Error("No se pudo cargar FFmpeg.");
      }
    })();
    return this.carga;
  }

  /** Termina el worker actual (cancela cualquier trabajo en curso). */
  terminar() {
    if (this.instancia) {
      try {
        this.instancia.terminate();
      } catch {
        // el worker ya no existía
      }
    }
    this.instancia = null;
    this.carga = null;
    this.ocupado = false;
    this.fijarEstado("inactivo");
  }

  async convertir(opciones: OpcionesConversion): Promise<{ datos: Uint8Array; nombreSalida: string }> {
    if (this.ocupado) throw new Error("FFmpeg ya está procesando otro archivo.");
    if (opciones.signal?.aborted) throw new ErrorCancelado();
    this.ocupado = true;
    const ffmpeg = await this.cargar();
    const def = FORMATOS[opciones.formato];
    const extEntrada = extensionDe(opciones.nombreEntrada) || "bin";
    const sello = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const entrada = `entrada_${sello}.${extEntrada}`;
    const salida = `salida_${sello}.${def.extension}`;
    const registro: string[] = [];

    const alRegistrar = ({ message }: { message: string }) => {
      registro.push(message);
      if (registro.length > 60) registro.shift();
      opciones.onLog?.(message);
    };
    const alProgresar = ({ progress, time }: { progress: number; time: number }) => {
      const p = Number.isFinite(progress) ? Math.min(1, Math.max(0, progress)) : 0;
      opciones.onProgreso?.(p, Number.isFinite(time) ? time / 1_000_000 : 0);
    };
    ffmpeg.on("log", alRegistrar);
    ffmpeg.on("progress", alProgresar);

    let cancelado = false;
    const alCancelar = () => {
      cancelado = true;
      this.terminar();
    };
    opciones.signal?.addEventListener("abort", alCancelar, { once: true });

    try {
      const bytes = new Uint8Array(await opciones.archivo.arrayBuffer());
      await ffmpeg.writeFile(entrada, bytes);
      const codigo = await ffmpeg.exec(["-hide_banner", "-y", "-i", entrada, ...argumentosFFmpeg(opciones.formato, opciones.calidad), salida]);
      if (cancelado) throw new ErrorCancelado();
      if (codigo !== 0) {
        const detalle = registro.filter((l) => /error|invalid|unsupported|not found|could not/i.test(l)).slice(-2).join(" · ");
        throw new Error(detalle ? `FFmpeg falló: ${detalle}` : `FFmpeg terminó con código ${codigo}.`);
      }
      const resultado = await ffmpeg.readFile(salida);
      const datos = typeof resultado === "string" ? new TextEncoder().encode(resultado) : resultado;
      if (datos.byteLength === 0) throw new Error("La conversión produjo un archivo vacío.");
      return { datos, nombreSalida: salida };
    } catch (error) {
      if (cancelado || opciones.signal?.aborted) throw new ErrorCancelado();
      throw error;
    } finally {
      opciones.signal?.removeEventListener("abort", alCancelar);
      if (!cancelado && this.instancia === ffmpeg) {
        ffmpeg.off("log", alRegistrar);
        ffmpeg.off("progress", alProgresar);
        for (const nombre of [entrada, salida]) {
          try {
            await ffmpeg.deleteFile(nombre);
          } catch {
            // ya no existe (p. ej. la conversión falló antes de escribir la salida)
          }
        }
      }
      this.ocupado = false;
    }
  }
}

export const clienteFFmpeg = new ClienteFFmpeg();
