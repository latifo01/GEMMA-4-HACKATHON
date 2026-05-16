import type { ReactNode } from "react";

type FieldProps = {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
};

export function Field({ label, hint, error, children }: FieldProps) {
  return (
    <label className="grid gap-2 text-sm">
      <span className="font-semibold text-slate-800">{label}</span>
      {children}
      {hint ? <span className="text-xs leading-5 text-slate-500">{hint}</span> : null}
      {error ? <span className="text-xs font-medium leading-5 text-clinical-red">{error}</span> : null}
    </label>
  );
}
