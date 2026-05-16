import type { UseFormRegister } from "react-hook-form";

import { Field } from "../ui/Field";
import type { TriageFormValues } from "../../features/triage/TriageWorkspace";

type LanguageSelectorProps = {
  register: UseFormRegister<TriageFormValues>;
};

export function LanguageSelector({ register }: LanguageSelectorProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label="Source language">
        <select
          className="min-h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          {...register("source_language")}
        >
          <option value="auto">Auto detect</option>
          <option value="en">English</option>
          <option value="fr">French</option>
          <option value="ar-SD">Sudanese Arabic</option>
        </select>
      </Field>
      <Field label="Output language">
        <select
          className="min-h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          {...register("target_language")}
        >
          <option value="en">English</option>
          <option value="fr">French</option>
          <option value="ar-SD">Sudanese Arabic</option>
        </select>
      </Field>
    </div>
  );
}
