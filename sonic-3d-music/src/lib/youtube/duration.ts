// Duraciones ISO 8601 (PT1H2M3S) de la YouTube Data API y formato mm:ss / h:mm:ss.

const RE_ISO = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$/;

export function duracionISOaSegundos(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const m = RE_ISO.exec(iso.trim());
  if (!m) return null;
  const [, d, h, min, s] = m;
  const total = Number(d ?? 0) * 86400 + Number(h ?? 0) * 3600 + Number(min ?? 0) * 60 + Number(s ?? 0);
  return Number.isFinite(total) ? Math.round(total) : null;
}

export function formatearDuracion(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined || !Number.isFinite(segundos) || segundos < 0) return "--:--";
  const total = Math.floor(segundos);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m);
  return h > 0 ? `${h}:${mm}:${String(s).padStart(2, "0")}` : `${mm}:${String(s).padStart(2, "0")}`;
}
