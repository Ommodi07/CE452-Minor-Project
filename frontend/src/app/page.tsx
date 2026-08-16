import { ResearchForm } from "@/components/research/ResearchForm";
import { HealthBadge } from "@/components/layout/HealthBadge";

export default function HomePage() {
  return (
    <div className="space-y-6">
      <section className="retro-panel p-4 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-display text-[0.55rem] leading-relaxed tracking-wider text-retro-amber sm:text-[0.65rem]">
              WELCOME OPERATOR
            </p>
            <h1 className="mt-2 font-terminal text-2xl text-retro-text-bright sm:text-4xl">
              AI Research Analyst
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-retro-text-dim sm:text-base">
              Submit a research query and let the multi-agent pipeline plan, research, critique, and
              write a comprehensive report with verified claims and citations.
            </p>
          </div>
          <HealthBadge />
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <FeatureCard icon="◈" title="Planner" desc="Decomposes queries into sub-questions" />
          <FeatureCard icon="◎" title="Researcher" desc="Web search & source verification" />
          <FeatureCard icon="▣" title="Writer" desc="Generates cited research reports" />
        </div>
      </section>

      <ResearchForm />
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="retro-panel-inset p-3 text-center sm:p-4">
      <span className="font-terminal text-2xl text-retro-amber">{icon}</span>
      <h2 className="mt-2 font-terminal text-lg text-retro-text-bright">{title}</h2>
      <p className="mt-1 text-xs text-retro-text-dim">{desc}</p>
    </div>
  );
}
