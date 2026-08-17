import Link from "next/link";
import { PageCard } from "@/components/ui/page-card";
import { Badge } from "@/components/ui/badge";
import { ENDPOINT_MAPPINGS } from "@/lib/endpoints";

export function ApiCoverageMap() {
  return (
    <PageCard title="Frontend ↔ Backend Coverage" subtitle="All 7 API endpoints mapped">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b-2 border-black text-muted-foreground">
              <th className="pb-2 pr-3 font-head">API</th>
              <th className="pb-2 pr-3 font-head">Frontend Page</th>
              <th className="pb-2 font-head">Description</th>
            </tr>
          </thead>
          <tbody>
            {ENDPOINT_MAPPINGS.map((mapping) => (
              <tr key={`${mapping.method}-${mapping.path}`} className="border-b border-black/20">
                <td className="py-3 pr-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={mapping.method === "GET" ? "info" : "warning"}>
                      {mapping.method}
                    </Badge>
                    <span className="font-mono text-xs">{mapping.path}</span>
                  </div>
                </td>
                <td className="py-3 pr-3">
                  <Link
                    href={mapping.frontendRoute.replace(/\[.*?\]/g, "")}
                    className="font-head text-base hover:underline"
                  >
                    {mapping.frontendLabel}
                  </Link>
                  <p className="font-mono text-xs text-muted-foreground">{mapping.frontendRoute}</p>
                </td>
                <td className="py-3 text-muted-foreground">{mapping.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PageCard>
  );
}
