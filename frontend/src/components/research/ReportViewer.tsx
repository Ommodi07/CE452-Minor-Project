"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, ExternalLink } from "lucide-react";
import { PageCard } from "@/components/ui/page-card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { downloadReport } from "@/lib/api";
import type { Report, ResearchResponse } from "@/lib/types";

interface ReportViewerProps {
  data: ResearchResponse;
}

export function ReportViewer({ data }: ReportViewerProps) {
  const router = useRouter();
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

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
      <PageCard title="No Report Generated" badge={<Badge variant="warning">{data.status}</Badge>}>
        <p className="text-muted-foreground">
          Research completed with status <strong className="text-foreground">{data.status}</strong> but
          no report was produced.
        </p>
        {data.errors.length > 0 && (
          <ul className="mt-4 space-y-1 text-sm text-destructive">
            {data.errors.map((err) => (
              <li key={err}>• {err}</li>
            ))}
          </ul>
        )}
      </PageCard>
    );
  }

  const citations = Object.values(report.citations);

  return (
    <div className="space-y-6">
      <PageCard
        title={report.title}
        subtitle={`Session: ${data.session_id} · Generated ${new Date(report.generated_at).toLocaleString()}`}
        badge={<Badge variant="success">Complete</Badge>}
      >
        <p className="mb-4 leading-relaxed">{report.executive_summary}</p>

        <div className="flex flex-wrap gap-2">
          <Button onClick={handleExport} disabled={exporting}>
            <Download className="size-4" />
            {exporting ? "Exporting..." : "Download DOCX"}
          </Button>
          <Button variant="secondary" onClick={() => router.push(`/sessions/${data.session_id}`)}>
            View Session State
          </Button>
          <Link
            href={`/stream/${data.session_id}`}
            className={cn(buttonVariants({ variant: "outline", size: "default" }))}
          >
            Stream Status
          </Link>
        </div>

        {exportError && <p className="mt-3 text-sm text-destructive">{exportError}</p>}
      </PageCard>

      {(data.errors.length > 0 || data.open_questions.length > 0 || report.limitations.length > 0) && (
        <PageCard title="Warnings & Limitations">
          {data.errors.length > 0 && (
            <div className="mb-4">
              <h3 className="mb-2 font-head text-base text-destructive">Errors</h3>
              <ul className="space-y-1 text-sm text-destructive">
                {data.errors.map((err) => (
                  <li key={err}>• {err}</li>
                ))}
              </ul>
            </div>
          )}
          {data.open_questions.length > 0 && (
            <div className="mb-4">
              <h3 className="mb-2 font-head text-base">Open Questions</h3>
              <ul className="space-y-1 text-sm">
                {data.open_questions.map((q) => (
                  <li key={q}>? {q}</li>
                ))}
              </ul>
            </div>
          )}
          {report.limitations.length > 0 && (
            <div>
              <h3 className="mb-2 font-head text-base text-muted-foreground">Limitations</h3>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {report.limitations.map((lim) => (
                  <li key={lim}>— {lim}</li>
                ))}
              </ul>
            </div>
          )}
        </PageCard>
      )}

      <PageCard title="Report Content">
        <Tabs defaultValue="markdown">
          <TabsList>
            <TabsTrigger value="markdown">Markdown</TabsTrigger>
            <TabsTrigger value="structured">Sections</TabsTrigger>
            <TabsTrigger value="sources">Sources</TabsTrigger>
          </TabsList>

          <TabsContent value="markdown">
            <div className="markdown-report inset-panel mt-3 max-h-[70vh] overflow-y-auto rounded p-4 sm:p-6">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.markdown || report.title}</ReactMarkdown>
            </div>
          </TabsContent>

          <TabsContent value="structured">
            <div className="mt-3 space-y-4">
              {report.sections.map((section) => (
                <article key={section.heading} className="inset-panel rounded p-4">
                  <h3 className="font-head text-lg">{section.heading}</h3>
                  <div className="markdown-report mt-2">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
                  </div>
                </article>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="sources">
            <div className="mt-3 space-y-3">
              {citations.length === 0 ? (
                <p className="text-muted-foreground">No citations recorded.</p>
              ) : (
                citations.map((source) => <SourceCard key={source.id} source={source} />)
              )}
            </div>
          </TabsContent>
        </Tabs>
      </PageCard>
    </div>
  );
}

function SourceCard({ source }: { source: Report["citations"][string] }) {
  return (
    <article className="inset-panel rounded p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="font-head text-base">{source.title}</h4>
        <Badge variant="outline">{source.source_type}</Badge>
      </div>
      <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{source.snippet}</p>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
        {source.credibility_score != null && (
          <span>Credibility: {(source.credibility_score * 100).toFixed(0)}%</span>
        )}
        {source.author && <span>Author: {source.author}</span>}
        {source.published_date && <span>Date: {source.published_date}</span>}
      </div>
      {source.quality_flags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {source.quality_flags.map((flag) => (
            <Badge key={flag} variant="warning">
              {flag}
            </Badge>
          ))}
        </div>
      )}
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-flex items-center gap-1 text-sm text-blue-700 hover:underline"
      >
        <ExternalLink className="size-3.5" />
        {source.url}
      </a>
    </article>
  );
}
