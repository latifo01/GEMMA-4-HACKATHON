export type AudioTranscriptionData = {
  transcript: string;
  detected_language: string;
  duration_seconds: number;
  segments: Array<Record<string, unknown>>;
};

export type VideoAnalysisData = {
  respiratory_rate_bpm: number | null;
  confidence: number;
  frames_analyzed: number;
  duration_seconds: number;
  quality_flags: string[];
  notes: string;
};
