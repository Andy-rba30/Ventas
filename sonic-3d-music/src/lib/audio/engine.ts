// Motor de audio para archivos propios: un HTMLAudioElement conectado a un AnalyserNode de la
// Web Audio API. Los visualizadores leen datos reales de frecuencia; si no hay señal (no hay
// contexto, está suspendido o nada se reproduce) `tieneSenal()` devuelve false y los
// visualizadores muestran su estado de reposo en lugar de simular una reacción.

export class MotorAudio {
  readonly audio: HTMLAudioElement;
  private contexto: AudioContext | null = null;
  private analizador: AnalyserNode | null = null;
  private fuente: MediaElementAudioSourceNode | null = null;
  private frecuencias = new Uint8Array(0);
  private onda = new Uint8Array(0);

  constructor() {
    this.audio = new Audio();
    this.audio.preload = "metadata";
    this.audio.crossOrigin = "anonymous";
  }

  /** Crea el contexto de audio (debe llamarse tras un gesto de la usuaria). */
  activarAnalisis(): boolean {
    if (this.analizador) {
      void this.reanudar();
      return true;
    }
    const Contexto =
      window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Contexto) return false;
    try {
      this.contexto = new Contexto();
      this.analizador = this.contexto.createAnalyser();
      this.analizador.fftSize = 2048;
      this.analizador.smoothingTimeConstant = 0.82;
      this.fuente = this.contexto.createMediaElementSource(this.audio);
      this.fuente.connect(this.analizador);
      this.analizador.connect(this.contexto.destination);
      this.frecuencias = new Uint8Array(this.analizador.frequencyBinCount);
      this.onda = new Uint8Array(this.analizador.fftSize);
      void this.reanudar();
      return true;
    } catch {
      this.contexto = null;
      this.analizador = null;
      return false;
    }
  }

  async reanudar() {
    if (this.contexto && this.contexto.state === "suspended") {
      try {
        await this.contexto.resume();
      } catch {
        // el navegador exige otro gesto de la usuaria
      }
    }
  }

  tieneSenal(): boolean {
    return Boolean(this.analizador && this.contexto?.state === "running" && !this.audio.paused && !this.audio.ended);
  }

  leerFrecuencias(): Uint8Array {
    if (this.analizador) this.analizador.getByteFrequencyData(this.frecuencias);
    return this.frecuencias;
  }

  leerOnda(): Uint8Array {
    if (this.analizador) this.analizador.getByteTimeDomainData(this.onda);
    return this.onda;
  }

  /** Nivel 0..1 ponderado hacia graves y medios (lo que "se siente" del ritmo). */
  nivel(): number {
    if (!this.tieneSenal()) return 0;
    const datos = this.leerFrecuencias();
    const n = Math.min(datos.length, 96);
    if (n === 0) return 0;
    let suma = 0;
    for (let i = 0; i < n; i += 1) suma += datos[i] ?? 0;
    return Math.min(1, suma / n / 200);
  }

  /** Nivel por bandas (graves, medios, agudos) 0..1. */
  bandas(): [number, number, number] {
    if (!this.tieneSenal()) return [0, 0, 0];
    const d = this.leerFrecuencias();
    const promedio = (desde: number, hasta: number) => {
      let s = 0;
      const fin = Math.min(hasta, d.length);
      for (let i = desde; i < fin; i += 1) s += d[i] ?? 0;
      return fin > desde ? s / (fin - desde) / 255 : 0;
    };
    return [promedio(1, 24), promedio(24, 160), promedio(160, 512)];
  }
}

let motor: MotorAudio | null = null;

export function obtenerMotor(): MotorAudio | null {
  if (typeof window === "undefined") return null;
  if (!motor) motor = new MotorAudio();
  return motor;
}
