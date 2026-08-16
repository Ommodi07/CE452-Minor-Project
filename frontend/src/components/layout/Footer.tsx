import { API_URL } from "@/lib/api";

export function Footer() {
  return (
    <footer className="relative z-10 mt-auto border-t-2 border-retro-border bg-retro-panel/80">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-4 text-sm text-retro-text-dim sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="font-terminal text-base">
          <span className="text-retro-border-bright">●</span> AI Research Analyst Terminal
        </p>
        <p className="font-mono text-xs">
          API: <span className="text-retro-cyan">{API_URL}</span>
        </p>
      </div>
    </footer>
  );
}
