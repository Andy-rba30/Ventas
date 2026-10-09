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
  readonly pregunta: string;
  readonly afirmacion: string;
  readonly colorAcento: string;
  readonly style?: React.CSSProperties;
};

const ImportanciaInterna: React.FC<Props> = ({
  pregunta,
  afirmacion,
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
        name="Pregunta"
        style={{
          position: "relative",
          color: colorAcento,
          fontFamily: "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          fontSize: 64,
          fontWeight: 700,
          letterSpacing: 6,
          textTransform: "uppercase",
          opacity: interpolate(frame, [0, 18], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          translate: interpolate(frame, [0, 30], ["0px -30px", "0px 0px"], {
            easing: Easing.spring({ damping: 200 }),
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {pregunta}
      </Interactive.Div>
      <Interactive.Div
        name="Afirmación"
        style={{
          position: "relative",
          marginTop: 48,
          maxWidth: 1640,
          textAlign: "center",
          color: "white",
          fontFamily: "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          fontSize: 104,
          fontWeight: 800,
          lineHeight: 1.12,
          letterSpacing: -1,
          textWrap: "balance",
          opacity: interpolate(frame, [15, 40], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          scale: interpolate(frame, [15, 60], [0.9, 1], {
            easing: Easing.spring({ damping: 200 }),
            output: "perceptual-scale",
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {afirmacion}
      </Interactive.Div>
    </AbsoluteFill>
  );
};

const esquema = {
  pregunta: { type: "text-content", default: "", description: "Pregunta" },
  afirmacion: { type: "text-content", default: "", description: "Afirmación" },
  colorAcento: {
    type: "color",
    default: "#ffd166",
    description: "Color de acento",
  },
} as const satisfies InteractivitySchema;

export const Importancia = Interactive.withSchema({
  Component: ImportanciaInterna,
  componentName: "<Importancia>",
  schema: esquema,
  wrapInSequence: true,
});
