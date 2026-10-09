import React from "react";
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { useVideoConfig } from "remotion";
import { Apertura } from "./escenas/Apertura";
import { Cierre } from "./escenas/Cierre";
import { Derechos } from "./escenas/Derechos";
import { Importancia } from "./escenas/Importancia";

/**
 * Video de 20 s (600 cuadros a 30 fps) sobre la importancia de los derechos de
 * niños, niñas y adolescentes. Cuatro escenas unidas por fundidos de 15 cuadros:
 * 120 + 150 + 240 + 135 - 3 x 15 = 600.
 */
export const DerechosNinez: React.FC = () => {
  const { fps } = useVideoConfig();

  return (
    <TransitionSeries>
      <TransitionSeries.Sequence
        name="Apertura"
        durationInFrames={120}
        premountFor={fps}
      >
        <Apertura
          titulo="Los derechos de niños, niñas y adolescentes"
          subtitulo="importan hoy y siempre"
          colorAcento="#ffd166"
        />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: 15 })}
      />
      <TransitionSeries.Sequence
        name="Importancia"
        durationInFrames={150}
        premountFor={fps}
      >
        <Importancia
          pregunta="¿Por qué importan?"
          afirmacion="Porque cada niño, niña y adolescente merece crecer seguro, sano y feliz."
          colorAcento="#ffd166"
        />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: 15 })}
      />
      <TransitionSeries.Sequence
        name="Derechos"
        durationInFrames={240}
        premountFor={fps}
      >
        <Derechos titulo="Algunos de sus derechos" />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: 15 })}
      />
      <TransitionSeries.Sequence
        name="Cierre"
        durationInFrames={135}
        premountFor={fps}
      >
        <Cierre
          titulo="Protegerlos es tarea de todos."
          llamado="Infórmate · Escucha · Actúa"
          fuente="Convención sobre los Derechos del Niño (ONU, 1989) · Código de los Niños y Adolescentes del Perú"
          colorAcento="#ffd166"
        />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
