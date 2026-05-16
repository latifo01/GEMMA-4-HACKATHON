import type { HTMLAttributes } from "react";

import { cn } from "../../lib/cn";

type AlertTone = "info" | "warning" | "error" | "success";

const tones: Record<AlertTone, string> = {
  info: "border-blue-200 bg-blue-50 text-blue-900",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  error: "border-red-200 bg-red-50 text-red-900",
  success: "border-green-200 bg-green-50 text-green-900",
};

type AlertProps = HTMLAttributes<HTMLDivElement> & {
  tone?: AlertTone;
};

export function Alert({ className, tone = "info", ...props }: AlertProps) {
  return <div className={cn("rounded-md border px-4 py-3 text-sm leading-6", tones[tone], className)} {...props} />;
}
