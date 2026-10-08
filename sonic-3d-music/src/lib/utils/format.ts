export function formatearBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const unidades = ["KB", "MB", "GB"];
  let valor = bytes / 1024;
  let i = 0;
  while (valor >= 1024 && i < unidades.length - 1) {
    valor /= 1024;
    i += 1;
  }
  return `${valor.toFixed(valor >= 100 ? 0 : 1)} ${unidades[i]}`;
}

export function formatearFecha(iso: string | number | Date): string {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return "—";
  return new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" }).format(fecha);
}

export function formatearNumero(n: number | undefined): string {
  if (n === undefined || !Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("es").format(n);
}

export function acortar(texto: string, max: number): string {
  if (texto.length <= max) return texto;
  return `${texto.slice(0, max - 1).trimEnd()}…`;
}
