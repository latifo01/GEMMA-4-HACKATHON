import { useCallback, useRef, useState } from "react";

import type { SourceLanguage } from "../../types/triage";

type SpeechRecognitionAlternative = {
  transcript: string;
};

type SpeechRecognitionResult = {
  readonly isFinal: boolean;
  readonly length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
};

type SpeechRecognitionResultList = {
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
};

type SpeechRecognitionEventLike = Event & {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
};

type SpeechRecognitionErrorEventLike = Event & {
  readonly error?: string;
};

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  abort: () => void;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

type SpeechWindow = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

type UseSpeechDictationOptions = {
  onFinalText: (text: string) => void;
};

export function useSpeechDictation({ onFinalText }: UseSpeechDictationOptions) {
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [interimText, setInterimText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isSupported = typeof window !== "undefined" && Boolean(getSpeechRecognitionConstructor());

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setIsListening(false);
    setInterimText("");
  }, []);

  const start = useCallback(
    (sourceLanguage: SourceLanguage) => {
      const SpeechRecognition = getSpeechRecognitionConstructor();
      if (!SpeechRecognition) {
        setError("Live dictation is not supported in this browser. You can still upload an audio file.");
        return;
      }

      recognitionRef.current?.abort();
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = toSpeechLanguage(sourceLanguage);
      recognition.onresult = (event) => {
        let finalText = "";
        let interim = "";

        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const transcript = event.results[index][0]?.transcript ?? "";
          if (event.results[index].isFinal) {
            finalText += transcript;
          } else {
            interim += transcript;
          }
        }

        if (finalText.trim()) {
          onFinalText(finalText.trim());
        }
        setInterimText(interim.trim());
      };
      recognition.onerror = (event) => {
        setError(toDictationError(event.error));
        setIsListening(false);
      };
      recognition.onend = () => {
        setIsListening(false);
        setInterimText("");
        recognitionRef.current = null;
      };

      setError(null);
      setInterimText("");
      setIsListening(true);
      recognitionRef.current = recognition;
      recognition.start();
    },
    [onFinalText],
  );

  return {
    error,
    interimText,
    isListening,
    isSupported,
    start,
    stop,
  };
}

function getSpeechRecognitionConstructor() {
  const speechWindow = window as SpeechWindow;
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

function toSpeechLanguage(sourceLanguage: SourceLanguage) {
  if (sourceLanguage === "fr") return "fr-FR";
  if (sourceLanguage === "ar-SD") return "ar-SD";
  return "en-US";
}

function toDictationError(error?: string) {
  if (error === "not-allowed") {
    return "Microphone access was blocked by the browser.";
  }
  if (error === "no-speech") {
    return "No speech was detected. Try again closer to the microphone.";
  }
  return "Live dictation stopped unexpectedly.";
}
