import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

/** Fondo degradado con manchas de luz que se desplazan despacio. Solo decorativo. */
export const Fondo: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(135deg, #1b2a6b 0%, #2c3fb0 55%, #4a3ab3 100%)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          width: 1000,
          height: 1000,
          left: -300,
          top: -350,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(255, 209, 102, 0.38) 0%, rgba(255, 209, 102, 0) 70%)",
          translate: interpolate(
            frame,
            [0, durationInFrames],
            ["0px 0px", "80px 50px"],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          ),
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 1100,
          height: 1100,
          right: -400,
          bottom: -450,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(6, 214, 160, 0.32) 0%, rgba(6, 214, 160, 0) 70%)",
          translate: interpolate(
            frame,
            [0, durationInFrames],
            ["0px 0px", "-70px -40px"],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          ),
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 600,
          height: 600,
          right: 200,
          top: -250,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(255, 107, 107, 0.28) 0%, rgba(255, 107, 107, 0) 70%)",
          translate: interpolate(
            frame,
            [0, durationInFrames],
            ["0px 0px", "-40px 60px"],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          ),
        }}
      />
    </AbsoluteFill>
  );
};
