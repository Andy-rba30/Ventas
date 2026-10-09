import React from "react";
import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  useCurrentFrame,
  type InteractivitySchema,
} from "remotion";
import { Fondo } from "./Fondo";

type Props = {
  readonly titulo: string;
  readonly llamado: string;
  readonly fuente: string;
  readonly colorAcento: string;
  readonly style?: React.CSSProperties;
};

const CierreInterna: React.FC<Props> = ({
  titulo,
  llamado,
  fuente,
  colorAcento,
  style,
}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: "0 140px",
        ...style,
      }}
    >
      <Fondo />
      <Interactive.Div
        name="Título"
        style={{
          position: "relative",
          maxWidth: 1640,
          textAlign: "center",
          color: "white",
          fontFamily: "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          fontSize: 128,
          fontWeight: 800,
          lineHeight: 1.08,
          letterSpacing: -2,
          textWrap: "balance",
          opacity: interpolate(frame, [0, 20], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          scale: interpolate(frame, [0, 40], [0.9, 1], {
            easing: Easing.spring({ damping: 200 }),
            output: "perceptual-scale",
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {titulo}
      </Interactive.Div>
      <Interactive.Div
        name="Llamado"
        style={{
          position: "relative",
          marginTop: 44,
          textAlign: "center",
          color: colorAcento,
          fontFamily: "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          fontSize: 72,
          fontWeight: 700,
          letterSpacing: 2,
          opacity: interpolate(frame, [20, 40], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          translate: interpolate(frame, [20, 50], ["0px 40px", "0px 0px"], {
            easing: Easing.spring({ damping: 200 }),
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {llamado}
      </Interactive.Div>
      <Interactive.Div
        name="Fuente"
        style={{
          position: "absolute",
          bottom: 100,
          left: 140,
          right: 140,
          textAlign: "center",
          color: "rgba(255, 255, 255, 0.7)",
          fontFamily: "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          fontSize: 38,
          fontWeight: 500,
          opacity: interpolate(frame, [40, 60], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {fuente}
      </Interactive.Div>
    </AbsoluteFill>
  );
};

const esquema = {
  titulo: { type: "text-content", default: "", description: "Título" },
  llamado: {
    type: "text-content",
    default: "",
    description: "Llamado a la acción",
  },
  fuente: { type: "text-content", default: "", description: "Fuente" },
  colorAcento: {
    type: "color",
    default: "#ffd166",
    description: "Color de acento",
  },
} as const satisfies InteractivitySchema;

export const Cierre = Interactive.withSchema({
  Component: CierreInterna,
  componentName: "<Cierre>",
  schema: esquema,
  wrapInSequence: true,
});
