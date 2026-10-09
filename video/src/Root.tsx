import React from "react";
import { Composition, Folder } from "remotion";
import { DerechosNinez } from "./DerechosNinez";
import { Apertura } from "./escenas/Apertura";
import { Cierre } from "./escenas/Cierre";
import { Derechos } from "./escenas/Derechos";
import { Importancia } from "./escenas/Importancia";
import { TarjetaDerecho } from "./escenas/TarjetaDerecho";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="DerechosNinez"
        component={DerechosNinez}
        durationInFrames={600}
        fps={30}
        width={1920}
        height={1080}
      />
      <Folder name="Escenas">
        <Composition
          id="Apertura"
          component={Apertura}
          durationInFrames={120}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            titulo: "Los derechos de niños, niñas y adolescentes",
            subtitulo: "importan hoy y siempre",
            colorAcento: "#ffd166",
          }}
        />
        <Composition
          id="Importancia"
          component={Importancia}
          durationInFrames={150}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            pregunta: "¿Por qué importan?",
            afirmacion:
              "Porque cada niño, niña y adolescente merece crecer seguro, sano y feliz.",
            colorAcento: "#ffd166",
          }}
        />
        <Composition
          id="Derechos"
          component={Derechos}
          durationInFrames={240}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{ titulo: "Algunos de sus derechos" }}
        />
        <Composition
          id="Cierre"
          component={Cierre}
          durationInFrames={135}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            titulo: "Protegerlos es tarea de todos.",
            llamado: "Infórmate · Escucha · Actúa",
            fuente:
              "Convención sobre los Derechos del Niño (ONU, 1989) · Código de los Niños y Adolescentes del Perú",
            colorAcento: "#ffd166",
          }}
        />
      </Folder>
      <Folder name="Elementos">
        <Composition
          id="TarjetaDerecho"
          component={TarjetaDerecho}
          durationInFrames={90}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            titulo: "Educación",
            detalle: "Aprender e ir a la escuela",
            color: "#ffd166",
            icono: "libro",
            style: { left: 560, top: 400 },
          }}
        />
      </Folder>
    </>
  );
};
