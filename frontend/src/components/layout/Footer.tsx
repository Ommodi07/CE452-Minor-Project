import { API_URL } from "@/lib/api";

export function Footer() {
  return (
    <footer className="relative z-10 mt-auto border-t-2 border-black bg-card shadow-[0_-3px_0_0_#000]">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="font-head text-base text-foreground">AI Research Analyst</p>
        <p className="font-mono text-xs">
          API: <span className="font-medium text-foreground">{API_URL}</span>
        </p>
      </div>
    </footer>
  );
}
