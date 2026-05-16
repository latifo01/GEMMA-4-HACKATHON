import { AppShell } from "./layouts/AppShell";
import { SessionPage } from "./pages/SessionPage";
import { TriagePage } from "./pages/TriagePage";

export default function App() {
  const sessionMatch = window.location.pathname.match(/^\/sessions?\/([^/]+)$/);

  return (
    <AppShell>
      {sessionMatch ? <SessionPage sessionId={sessionMatch[1]} /> : <TriagePage />}
    </AppShell>
  );
}
