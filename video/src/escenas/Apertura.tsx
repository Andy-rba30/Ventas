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
  readonly subtitulo: string;
  readonly colorAcento: string;
  readonly style?: React.CSSProperties;
};

const AperturaInterna: React.FC<Props> = ({
  titulo,
  subtitulo,
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
          fontSize: 136,
          fontWeight: 800,
          lineHeight: 1.08,
          letterSpacing: -2,
          textWrap: "balance",
          opacity: interpolate(frame, [0, 20], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          translate: interpolate(frame, [0, 35], ["0px 70px", "0px 0px"], {
            easing: Easing.spring({ damping: 200 }),
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {titulo}
      </Interactive.Div>
      <Interactive.Div
        name="Subtítulo"
        style={{
          position: "relative",
          marginTop: 40,
          textAlign: "center",
          color: colorAcento,
          fontFamily: "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          fontSize: 76,
          fontWeight: 600,
          opacity: interpolate(frame, [22, 42], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          translate: interpolate(frame, [22, 55], ["0px 40px", "0px 0px"], {
            easing: Easing.spring({ damping: 200 }),
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {subtitulo}
      </Interactive.Div>
    </AbsoluteFill>
  );
};

const esquema = {
  titulo: { type: "text-content", default: "", description: "Título" },
  subtitulo: { type: "text-content", default: "", description: "Subtítulo" },
  colorAcento: {
    type: "color",
    default: "#ffd166",
    description: "Color de acento",
  },
} as const satisfies InteractivitySchema;

export const Apertura = Interactive.withSchema({
  Component: AperturaInterna,
  componentName: "<Apertura>",
  schema: esquema,
  wrapInSequence: true,
});
