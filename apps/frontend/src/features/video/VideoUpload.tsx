import { Upload, Video } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { validateVideoFile, videoAccept } from "../../lib/files";

type VideoUploadProps = {
  file: File | null;
  isLoading: boolean;
  onFileChange: (file: File | null, error?: string) => void;
  onAnalyze: () => void;
};

export function VideoUpload({ file, isLoading, onAnalyze, onFileChange }: VideoUploadProps) {
  return (
    <section className="grid gap-3 rounded-md border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink">
        <Video className="h-4 w-4" aria-hidden="true" />
        Respiratory video
      </div>
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <label className="flex min-h-10 cursor-pointer items-center gap-2 rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-700 hover:border-blue-400">
          <Upload className="h-4 w-4" aria-hidden="true" />
          <span className="truncate">{file ? file.name : "Choose video file"}</span>
          <input
            className="sr-only"
            type="file"
            accept={videoAccept}
            onChange={(event) => {
              const nextFile = event.target.files?.[0] ?? null;
              const error = nextFile ? validateVideoFile(nextFile) : undefined;
              onFileChange(error ? null : nextFile, error ?? undefined);
              event.currentTarget.value = "";
            }}
          />
        </label>
        <Button type="button" onClick={onAnalyze} disabled={!file || isLoading} variant="secondary">
          {isLoading ? <Spinner label="Analyzing video" /> : "Analyze"}
        </Button>
      </div>
    </section>
  );
}
