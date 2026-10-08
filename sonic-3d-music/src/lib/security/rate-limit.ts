// Limitador de peticiones por clave (ventana deslizante en memoria). En entornos serverless cada
// instancia tiene su propia memoria: sirve como freno básico contra abuso, no como cuota exacta.

interface Registro {
  marcas: number[];
}

export class LimitadorPeticiones {
  private registros = new Map<string, Registro>();

  constructor(
    private readonly limite: number,
    private readonly ventanaMs: number,
    private readonly ahora: () => number = Date.now,
  ) {}

  comprobar(clave: string): { permitido: boolean; restantes: number; reinicioEnMs: number } {
    const t = this.ahora();
    const desde = t - this.ventanaMs;
    const registro = this.registros.get(clave) ?? { marcas: [] };
    registro.marcas = registro.marcas.filter((m) => m > desde);
    if (registro.marcas.length >= this.limite) {
      const masAntigua = registro.marcas[0] ?? t;
      this.registros.set(clave, registro);
      return { permitido: false, restantes: 0, reinicioEnMs: Math.max(0, masAntigua + this.ventanaMs - t) };
    }
    registro.marcas.push(t);
    this.registros.set(clave, registro);
    if (this.registros.size > 5000) this.purgar(desde);
    return { permitido: true, restantes: this.limite - registro.marcas.length, reinicioEnMs: this.ventanaMs };
  }

  private purgar(desde: number) {
    for (const [clave, registro] of this.registros) {
      if (!registro.marcas.some((m) => m > desde)) this.registros.delete(clave);
    }
  }
}

/** IP del cliente detrás de Netlify / proxies habituales. */
export function ipDeCliente(cabeceras: Headers): string {
  return (
    cabeceras.get("x-nf-client-connection-ip") ??
    cabeceras.get("x-real-ip") ??
    cabeceras.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    "desconocida"
  );
}
