import { Cloud, Laptop, Route } from "lucide-react";
import type { UseFormRegister } from "react-hook-form";

import { cn } from "../../lib/cn";
import type { HealthData } from "../../types/health";
import type { ModelMode } from "../../types/triage";
import type { TriageFormValues } from "../../features/triage/TriageWorkspace";

type ModeSelectorProps = {
  health?: HealthData;
  isCheckingHealth: boolean;
  value: ModelMode;
  register: UseFormRegister<TriageFormValues>;
};

const modes: Array<{
  value: ModelMode;
  label: string;
  description: string;
  icon: typeof Route;
}> = [
  {
    value: "auto",
    label: "Auto",
    description: "Use Gemma 4 online when available, then fallback.",
    icon: Route,
  },
  {
    value: "online",
    label: "Online Gemma 4",
    description: "Force Gemma 4 for the main demo path.",
    icon: Cloud,
  },
  {
    value: "offline",
    label: "Offline local",
    description: "Validate the low-connectivity field architecture.",
    icon: Laptop,
  },
];

export function ModeSelector({ health, isCheckingHealth, register, value }: ModeSelectorProps) {
  return (
    <fieldset className="grid gap-3">
      <legend className="text-sm font-semibold text-slate-800">Model mode</legend>
      <div className="grid gap-2 md:grid-cols-3">
        {modes.map((mode) => {
          const Icon = mode.icon;
          const selected = value === mode.value;
          const warning = getWarning(mode.value, health, isCheckingHealth);

          return (
            <label
              key={mode.value}
              className={cn(
                "flex min-h-28 cursor-pointer flex-col gap-2 rounded-md border bg-white p-3 transition",
                selected ? "border-blue-500 ring-2 ring-blue-100" : "border-slate-200 hover:border-slate-300",
              )}
            >
              <input className="sr-only" type="radio" value={mode.value} {...register("model_mode")} />
              <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                <Icon className="h-4 w-4" aria-hidden="true" />
                {mode.label}
              </span>
              <span className="text-xs leading-5 text-slate-600">{mode.description}</span>
              {warning ? <span className="text-xs font-semibold leading-5 text-clinical-amber">{warning}</span> : null}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function getWarning(value: ModelMode, health: HealthData | undefined, isCheckingHealth: boolean) {
  if (isCheckingHealth || !health) {
    return value === "auto" ? null : "Checking availability...";
  }

  if (value === "online" && !health.online_model_available) {
    return "Online model is not currently available.";
  }

  if (value === "offline" && !health.offline_model_available) {
    return "Offline model is not currently available.";
  }

  return null;
}
