import { ShieldCheck } from "lucide-react";

import { BackendStatus } from "./BackendStatus";

export function AppHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-ink text-white">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold tracking-normal text-ink">ImciFlow</h1>
            <p className="text-sm text-slate-600">Gemma 4 clinical support with online/offline routing</p>
          </div>
        </div>
        <BackendStatus />
      </div>
    </header>
  );
}
