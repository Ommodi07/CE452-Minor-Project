import Link from "next/link";
import { RetroCard } from "@/components/ui/RetroCard";
import { RetroBadge } from "@/components/ui/RetroBadge";
import { ENDPOINT_MAPPINGS } from "@/lib/endpoints";

export function ApiCoverageMap() {
  return (
    <RetroCard title="Frontend ↔ Backend Coverage" subtitle="All 7 API endpoints mapped">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-retro-border text-retro-text-dim">
              <th className="pb-2 pr-3 font-terminal text-base">API</th>
              <th className="pb-2 pr-3 font-terminal text-base">Frontend Page</th>
              <th className="pb-2 font-terminal text-base">Description</th>
            </tr>
          </thead>
          <tbody>
            {ENDPOINT_MAPPINGS.map((mapping) => (
              <tr
                key={`${mapping.method}-${mapping.path}`}
                className="border-b border-retro-border/50"
              >
                <td className="py-3 pr-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <RetroBadge variant={mapping.method === "GET" ? "info" : "ok"}>
                      {mapping.method}
                    </RetroBadge>
                    <span className="font-mono text-xs text-retro-cyan">{mapping.path}</span>
                  </div>
                </td>
                <td className="py-3 pr-3">
                  <Link
                    href={mapping.frontendRoute.replace(/\[.*?\]/g, "")}
                    className="font-terminal text-base text-retro-amber hover:text-retro-text-bright"
                  >
                    {mapping.frontendLabel}
                  </Link>
                  <p className="font-mono text-xs text-retro-text-dim">{mapping.frontendRoute}</p>
                </td>
                <td className="py-3 text-retro-text-dim">{mapping.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </RetroCard>
  );
}
