"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { RetroCard } from "@/components/ui/RetroCard";
import { RetroButton } from "@/components/ui/RetroButton";
import { RetroBadge } from "@/components/ui/RetroBadge";
import { downloadReport } from "@/lib/api";
import type { Report, ResearchResponse } from "@/lib/types";

interface ReportViewerProps {
  data: ResearchResponse;
}

export function ReportViewer({ data }: ReportViewerProps) {
  const router = useRouter();
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"markdown" | "structured" | "sources">("markdown");

  const report = data.report;

  const handleExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      await downloadReport(data.session_id);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  if (!report) {
    return (
      <RetroCard title="No Report Generated" badge={<RetroBadge variant="warn">{data.status}</RetroBadge>}>
        <p className="text-retro-text-dim">
          Research completed with status <strong className="text-retro-amber">{data.status}</strong> but no
          report was produced.
        </p>
        {data.errors.length > 0 && (
          <ul className="mt-4 space-y-1 text-sm text-retro-red">
            {data.errors.map((err) => (
              <li key={err}>• {err}</li>
            ))}
          </ul>
        )}
      </RetroCard>
    );
  }

  const citations = Object.values(report.citations);

  return (
    <div className="space-y-6">
      <RetroCard
        title={report.title}
        subtitle={`Session: ${data.session_id} · Generated ${new Date(report.generated_at).toLocaleString()}`}
        badge={<RetroBadge variant="ok">Complete</RetroBadge>}
      >
        <p className="mb-4 leading-relaxed text-retro-text">{report.executive_summary}</p>

        <div className="flex flex-wrap gap-2">
          <RetroButton onClick={handleExport} disabled={exporting}>
            {exporting ? "Exporting..." : "⬇ Download DOCX"}
          </RetroButton>
          <RetroButton
            variant="secondary"
            onClick={() => router.push(`/sessions/${data.session_id}`)}
          >
            View Session State
          </RetroButton>
          <Link href={`/stream/${data.session_id}`} className="retro-btn retro-btn-secondary">
            Stream Status
          </Link>
        </div>

        {exportError && <p className="mt-3 text-sm text-retro-red">{exportError}</p>}
      </RetroCard>

      {(data.errors.length > 0 || data.open_questions.length > 0 || report.limitations.length > 0) && (
        <RetroCard title="Warnings & Limitations">
          {data.errors.length > 0 && (
            <div className="mb-4">
              <h3 className="mb-2 font-terminal text-lg text-retro-red">Errors</h3>
              <ul className="space-y-1 text-sm">
                {data.errors.map((err) => (
                  <li key={err} className="text-retro-red">
                    • {err}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {data.open_questions.length > 0 && (
            <div className="mb-4">
              <h3 className="mb-2 font-terminal text-lg text-retro-amber">Open Questions</h3>
              <ul className="space-y-1 text-sm text-retro-text">
                {data.open_questions.map((q) => (
                  <li key={q}>? {q}</li>
                ))}
              </ul>
            </div>
          )}
          {report.limitations.length > 0 && (
            <div>
              <h3 className="mb-2 font-terminal text-lg text-retro-text-dim">Limitations</h3>
              <ul className="space-y-1 text-sm text-retro-text-dim">
                {report.limitations.map((lim) => (
                  <li key={lim}>— {lim}</li>
                ))}
              </ul>
            </div>
          )}
        </RetroCard>
      )}

      <RetroCard title="Report Content">
        <div className="mb-4 flex flex-wrap gap-2 border-b border-retro-border pb-3">
          {(["markdown", "structured", "sources"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`retro-btn px-3 py-1.5 text-xs ${
                activeTab === tab ? "border-retro-amber text-retro-amber" : ""
              }`}
            >
              {tab === "markdown" ? "Markdown" : tab === "structured" ? "Sections" : "Sources"}
            </button>
          ))}
        </div>

        {activeTab === "markdown" && (
          <div className="markdown-report retro-panel-inset max-h-[70vh] overflow-y-auto p-4 sm:p-6">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.markdown || report.title}</ReactMarkdown>
          </div>
        )}

        {activeTab === "structured" && (
          <div className="space-y-4">
            {report.sections.map((section) => (
              <article key={section.heading} className="retro-panel-inset p-4">
                <h3 className="font-terminal text-lg text-retro-amber">{section.heading}</h3>
                <div className="markdown-report mt-2">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
                </div>
              </article>
            ))}
          </div>
        )}

        {activeTab === "sources" && (
          <div className="space-y-3">
            {citations.length === 0 ? (
              <p className="text-retro-text-dim">No citations recorded.</p>
            ) : (
              citations.map((source) => (
                <SourceCard key={source.id} source={source} />
              ))
            )}
          </div>
        )}
      </RetroCard>
    </div>
  );
}

function SourceCard({ source }: { source: Report["citations"][string] }) {
  return (
    <article className="retro-panel-inset p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="font-terminal text-base text-retro-text-bright">{source.title}</h4>
        <RetroBadge variant="neutral">{source.source_type}</RetroBadge>
      </div>
      <p className="mt-2 text-sm text-retro-text-dim line-clamp-2">{source.snippet}</p>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-retro-text-dim">
        {source.credibility_score != null && (
          <span>Credibility: {(source.credibility_score * 100).toFixed(0)}%</span>
        )}
        {source.author && <span>Author: {source.author}</span>}
        {source.published_date && <span>Date: {source.published_date}</span>}
      </div>
      {source.quality_flags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {source.quality_flags.map((flag) => (
            <RetroBadge key={flag} variant="warn">
              {flag}
            </RetroBadge>
          ))}
        </div>
      )}
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-block text-sm text-retro-cyan hover:text-retro-text-bright"
      >
        {source.url}
      </a>
    </article>
  );
}
