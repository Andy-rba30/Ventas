// Guardia anti-SSRF para las URL que el servidor va a descargar: solo https, solo hosts de una
// lista blanca, sin credenciales en la URL, sin IP literales privadas y re-validando cada
// redirección. La resolución DNS se inyecta para poder probarla sin red.

export type ResultadoValidacion = { ok: true; url: URL } | { ok: false; motivo: string };

export function listaHosts(valor: string | undefined): string[] {
  return (valor ?? "")
    .split(",")
    .map((h) => h.trim().toLowerCase())
    .filter((h) => h.length > 0);
}

export function hostPermitido(host: string, permitidos: string[]): boolean {
  const h = host.toLowerCase();
  return permitidos.some((p) => (p.startsWith("*.") ? h.endsWith(p.slice(1)) && h !== p.slice(2) : h === p));
}

export function esIpPrivada(ip: string): boolean {
  const limpio = ip.replace(/^\[|\]$/g, "").toLowerCase();
  // IPv4 mapeada en IPv6 (::ffff:10.0.0.1)
  const mapeada = /^::ffff:(\d+\.\d+\.\d+\.\d+)$/.exec(limpio);
  if (mapeada) return esIpPrivada(mapeada[1] ?? "");
  const v4 = /^(\d+)\.(\d+)\.(\d+)\.(\d+)$/.exec(limpio);
  if (v4) {
    const [a, b] = [Number(v4[1]), Number(v4[2])];
    if (a === 0 || a === 10 || a === 127) return true;
    if (a === 169 && b === 254) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 192 && b === 168) return true;
    if (a === 100 && b >= 64 && b <= 127) return true;
    if (a >= 224) return true; // multicast y reservadas
    return false;
  }
  if (limpio.includes(":")) {
    if (limpio === "::" || limpio === "::1") return true;
    if (limpio.startsWith("fc") || limpio.startsWith("fd")) return true; // fc00::/7
    if (/^fe[89ab]/.test(limpio)) return true; // fe80::/10
    if (limpio.startsWith("ff")) return true; // multicast
    return false;
  }
  return true; // no es una IP reconocible: se trata como insegura
}

export function validarUrlRemota(entrada: string, permitidos: string[]): ResultadoValidacion {
  if (permitidos.length === 0) return { ok: false, motivo: "La descarga desde URL no está habilitada en este servidor." };
  let url: URL;
  try {
    url = new URL(entrada.trim());
  } catch {
    return { ok: false, motivo: "La URL no es válida." };
  }
  if (url.protocol !== "https:") return { ok: false, motivo: "Solo se admiten direcciones https://." };
  if (url.username || url.password) return { ok: false, motivo: "La URL no puede incluir credenciales." };
  if (/^[\d.]+$/.test(url.hostname) || url.hostname.includes(":")) {
    return { ok: false, motivo: "No se admiten direcciones IP literales." };
  }
  if (!hostPermitido(url.hostname, permitidos)) {
    return { ok: false, motivo: `El dominio ${url.hostname} no está en la lista de orígenes autorizados.` };
  }
  return { ok: true, url };
}

export type Resolver = (host: string) => Promise<{ address: string }[]>;

export async function comprobarDns(url: URL, resolver: Resolver): Promise<void> {
  let direcciones: { address: string }[];
  try {
    direcciones = await resolver(url.hostname);
  } catch {
    throw new Error(`No se pudo resolver el dominio ${url.hostname}.`);
  }
  if (direcciones.length === 0) throw new Error(`El dominio ${url.hostname} no resuelve.`);
  for (const { address } of direcciones) {
    if (esIpPrivada(address)) throw new Error("El destino apunta a una red privada y se bloqueó.");
  }
}

export interface OpcionesTraer {
  permitidos: string[];
  resolver: Resolver;
  hacerFetch?: typeof fetch;
  maxRedirecciones?: number;
  signal?: AbortSignal;
}

/** fetch con redirecciones manuales: cada salto se valida de nuevo contra la lista y el DNS. */
export async function traerConRedirecciones(entrada: string, opciones: OpcionesTraer): Promise<Response> {
  const hacerFetch = opciones.hacerFetch ?? fetch;
  const max = opciones.maxRedirecciones ?? 3;
  let actual = entrada;
  for (let salto = 0; salto <= max; salto += 1) {
    const validacion = validarUrlRemota(actual, opciones.permitidos);
    if (!validacion.ok) throw new Error(validacion.motivo);
    await comprobarDns(validacion.url, opciones.resolver);
    const respuesta = await hacerFetch(validacion.url.toString(), {
      redirect: "manual",
      signal: opciones.signal,
      headers: { "user-agent": "Sonic3DMusic/1.0 (+descarga autorizada)", accept: "audio/*,*/*;q=0.5" },
    });
    if (respuesta.status >= 300 && respuesta.status < 400) {
      const destino = respuesta.headers.get("location");
      if (!destino) throw new Error("Redirección sin destino.");
      actual = new URL(destino, validacion.url).toString();
      continue;
    }
    return respuesta;
  }
  throw new Error("Demasiadas redirecciones.");
}
