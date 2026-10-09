import React from "react";
import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  type InteractivitySchema,
} from "remotion";
import { Fondo } from "./Fondo";
import { TarjetaDerecho } from "./TarjetaDerecho";

type Props = {
  readonly titulo: string;
  readonly style?: React.CSSProperties;
};

const DerechosInterna: React.FC<Props> = ({ titulo, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={style}>
      <Fondo />
      <Interactive.Div
        name="Título"
        style={{
          position: "absolute",
          top: 120,
          left: 140,
          right: 140,
          textAlign: "center",
          color: "white",
          fontFamily: "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          fontSize: 88,
          fontWeight: 800,
          letterSpacing: -1,
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
        {titulo}
      </Interactive.Div>
      <TarjetaDerecho
        name="Educación"
        from={20}
        premountFor={fps}
        titulo="Educación"
        detalle="Aprender e ir a la escuela"
        color="#ffd166"
        icono="libro"
        style={{ left: 140, top: 300 }}
      />
      <TarjetaDerecho
        name="Salud"
        from={60}
        premountFor={fps}
        titulo="Salud"
        detalle="Crecer sanos y con atención médica"
        color="#06d6a0"
        icono="corazon"
        style={{ left: 980, top: 300 }}
      />
      <TarjetaDerecho
        name="Protección"
        from={100}
        premountFor={fps}
        titulo="Protección"
        detalle="Vivir libres de violencia y abuso"
        color="#ff6b6b"
        icono="escudo"
        style={{ left: 140, top: 620 }}
      />
      <TarjetaDerecho
        name="Participación"
        from={140}
        premountFor={fps}
        titulo="Participación"
        detalle="Ser escuchados en lo que les afecta"
        color="#a78bfa"
        icono="dialogo"
        style={{ left: 980, top: 620 }}
      />
    </AbsoluteFill>
  );
};

const esquema = {
  titulo: { type: "text-content", default: "", description: "Título" },
} as const satisfies InteractivitySchema;

export const Derechos = Interactive.withSchema({
  Component: DerechosInterna,
  componentName: "<Derechos>",
  schema: esquema,
  wrapInSequence: true,
});
