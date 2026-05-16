export const audioAccept = "audio/webm,audio/wav,audio/mpeg,audio/mp4";
export const videoAccept = "video/mp4,video/webm,video/quicktime";

const maxAudioBytes = 25 * 1024 * 1024;
const maxVideoBytes = 80 * 1024 * 1024;
const audioTypes = new Set(["audio/webm", "audio/wav", "audio/mpeg", "audio/mp4"]);
const videoTypes = new Set(["video/mp4", "video/webm", "video/quicktime"]);

export function validateAudioFile(file: File): string | null {
  return validateFile(file, audioTypes, maxAudioBytes, "audio");
}

export function validateVideoFile(file: File): string | null {
  return validateFile(file, videoTypes, maxVideoBytes, "video");
}

function validateFile(file: File, allowedTypes: Set<string>, maxBytes: number, label: string) {
  if (!allowedTypes.has(file.type)) {
    return `Unsupported ${label} type: ${file.type || "unknown"}.`;
  }

  if (file.size > maxBytes) {
    return `${label[0].toUpperCase()}${label.slice(1)} file is too large.`;
  }

  return null;
}
