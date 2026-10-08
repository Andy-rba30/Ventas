// Nombres de archivo limpios y válidos en Windows, macOS y Linux.

const RESERVADOS_WINDOWS = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i;

export function quitarExtension(nombre: string): string {
  const i = nombre.lastIndexOf(".");
  return i > 0 ? nombre.slice(0, i) : nombre;
}

export function limpiarNombre(nombre: string, extension: string, maxLargo = 120): string {
  let base = quitarExtension(nombre.split(/[\\/]/).pop() ?? "")
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u001f\u007f<>:"|?*]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^[. ]+|[. ]+$/g, "");
  if (base === "" || RESERVADOS_WINDOWS.test(base)) base = "audio";
  if (base.length > maxLargo) base = base.slice(0, maxLargo).trim();
  const ext = extension.replace(/^\./, "").toLowerCase();
  return ext ? `${base}.${ext}` : base;
}

export function extensionDe(nombre: string): string {
  const i = nombre.lastIndexOf(".");
  return i >= 0 ? nombre.slice(i + 1).toLowerCase() : "";
}
