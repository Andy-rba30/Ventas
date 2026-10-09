import React from "react";
import {
  Easing,
  Interactive,
  interpolate,
  useCurrentFrame,
  type InteractivitySchema,
} from "remotion";

type Props = {
  readonly titulo: string;
  readonly detalle: string;
  readonly color: string;
  /** libro | corazon | escudo | dialogo */
  readonly icono: string;
  readonly style?: React.CSSProperties;
};

/** Trazos de los íconos (Feather Icons, MIT), en un viewBox de 24 x 24. */
const TRAZOS: Record<string, string> = {
  libro:
    "M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
  corazon:
    "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",
  escudo: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  dialogo:
    "M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z",
};

const TarjetaDerechoInterna: React.FC<Props> = ({
  titulo,
  detalle,
  color,
  icono,
  style,
}) => {
  // El cuadro 0 es el momento en que la tarjeta aparece en la escena.
  const frame = useCurrentFrame();

  return (
    <Interactive.Div
      style={{
        position: "absolute",
        width: 800,
        height: 280,
        display: "flex",
        alignItems: "center",
        gap: 36,
        padding: "0 44px",
        boxSizing: "border-box",
        borderRadius: 32,
        backgroundColor: "rgba(255, 255, 255, 0.10)",
        border: "2px solid rgba(255, 255, 255, 0.18)",
        color: "white",
        fontFamily: "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        opacity: interpolate(frame, [0, 15], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
        translate: interpolate(frame, [0, 30], ["0px 50px", "0px 0px"], {
          easing: Easing.spring({ damping: 200 }),
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
        scale: interpolate(frame, [0, 30], [0.92, 1], {
          easing: Easing.spring({ damping: 200 }),
          output: "perceptual-scale",
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
        ...style,
      }}
    >
      <div
        style={{
          flexShrink: 0,
          width: 150,
          height: 150,
          borderRadius: "50%",
          backgroundColor: color,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg
          width={84}
          height={84}
          viewBox="0 0 24 24"
          fill="none"
          stroke="#1b2a6b"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d={TRAZOS[icono] ?? TRAZOS.libro} />
        </svg>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 66, fontWeight: 800, lineHeight: 1.1 }}>
          {titulo}
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: 500,
            lineHeight: 1.25,
            color: "rgba(255, 255, 255, 0.85)",
          }}
        >
          {detalle}
        </div>
      </div>
    </Interactive.Div>
  );
};

const esquema = {
  titulo: { type: "text-content", default: "", description: "Derecho" },
  detalle: { type: "text-content", default: "", description: "Detalle" },
  color: { type: "color", default: "#ffd166", description: "Color del ícono" },
  icono: {
    type: "enum",
    default: "libro",
    description: "Ícono",
    variants: { libro: {}, corazon: {}, escudo: {}, dialogo: {} },
  },
} as const satisfies InteractivitySchema;

export const TarjetaDerecho = Interactive.withSchema({
  Component: TarjetaDerechoInterna,
  componentName: "<TarjetaDerecho>",
  schema: esquema,
  wrapInSequence: true,
});
