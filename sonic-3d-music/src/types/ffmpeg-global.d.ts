import type { FFmpeg } from "@ffmpeg/ffmpeg";

declare global {
  interface Window {
    /** Expuesto por /ffmpeg/ffmpeg.js (build UMD de @ffmpeg/ffmpeg). */
    FFmpegWASM?: { FFmpeg: new () => FFmpeg };
  }
}

export {};
