import { Mic, Upload } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { audioAccept, validateAudioFile } from "../../lib/files";

type AudioUploadProps = {
  file: File | null;
  isLoading: boolean;
  onFileChange: (file: File | null, error?: string) => void;
  onTranscribe: () => void;
};

export function AudioUpload({ file, isLoading, onFileChange, onTranscribe }: AudioUploadProps) {
  return (
    <section className="grid gap-3 rounded-md border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink">
        <Mic className="h-4 w-4" aria-hidden="true" />
        Audio upload
      </div>
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <label className="flex min-h-10 cursor-pointer items-center gap-2 rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-700 hover:border-blue-400">
          <Upload className="h-4 w-4" aria-hidden="true" />
          <span className="truncate">{file ? file.name : "Choose audio file"}</span>
          <input
            className="sr-only"
            type="file"
            accept={audioAccept}
            onChange={(event) => {
              const nextFile = event.target.files?.[0] ?? null;
              const error = nextFile ? validateAudioFile(nextFile) : undefined;
              onFileChange(error ? null : nextFile, error ?? undefined);
              event.currentTarget.value = "";
            }}
          />
        </label>
        <Button type="button" onClick={onTranscribe} disabled={!file || isLoading} variant="secondary">
          {isLoading ? <Spinner label="Transcribing audio" /> : "Transcribe"}
        </Button>
      </div>
    </section>
  );
}
