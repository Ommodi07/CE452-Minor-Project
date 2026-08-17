import { ResearchForm } from "@/components/research/ResearchForm";
import { HealthBadge } from "@/components/layout/HealthBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Brain, Search, FileText } from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-6">
      <Card className="overflow-hidden">
        <CardContent className="space-y-6 pt-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <Badge variant="warning" className="mb-3">
                Welcome
              </Badge>
              <h1 className="font-head text-3xl sm:text-4xl">AI Research Analyst</h1>
              <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">
                Submit a research query and let the multi-agent pipeline plan, research, critique,
                and write a comprehensive report with verified claims and citations.
              </p>
            </div>
            <HealthBadge />
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <FeatureCard
              icon={Brain}
              title="Planner"
              desc="Decomposes queries into sub-questions"
              color="bg-[#74b9ff]"
            />
            <FeatureCard
              icon={Search}
              title="Researcher"
              desc="Web search & source verification"
              color="bg-[#88d498]"
            />
            <FeatureCard
              icon={FileText}
              title="Writer"
              desc="Generates cited research reports"
              color="bg-[#ffdc58]"
            />
          </div>
        </CardContent>
      </Card>

      <ResearchForm />
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  desc,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  desc: string;
  color: string;
}) {
  return (
    <div className="inset-panel rounded p-4 text-center">
      <div
        className={`mx-auto mb-3 flex h-12 w-12 items-center justify-center border-2 border-black shadow-sm ${color}`}
      >
        <Icon className="size-6" />
      </div>
      <h2 className="font-head text-lg">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
    </div>
  );
}
