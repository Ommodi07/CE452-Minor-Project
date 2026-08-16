"use client";

import { useEffect, useState } from "react";
import { RetroBadge } from "@/components/ui/RetroBadge";
import type { GraphStatus } from "@/lib/types";

const STEPS: { key: GraphStatus; label: string }[] = [
  { key: "planning", label: "Planner" },
  { key: "researching", label: "Researcher" },
  { key: "critiquing", label: "Critic" },
  { key: "writing", label: "Writer" },
  { key: "done", label: "Complete" },
];

const STATUS_ORDER: GraphStatus[] = ["planning", "researching", "critiquing", "writing", "done"];

interface ResearchProgressProps {
  active?: boolean;
  query?: string;
}

export function ResearchProgress({ active = true, query }: ResearchProgressProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!active) return;

    const stepTimer = setInterval(() => {
      setStepIndex((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 8000);

    const elapsedTimer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    return () => {
      clearInterval(stepTimer);
      clearInterval(elapsedTimer);
    };
  }, [active]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="retro-panel-inset loading-pulse p-4 sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <p className="font-terminal text-lg text-retro-amber blink-cursor">
          Running research pipeline...
        </p>
        <RetroBadge variant="info">{formatTime(elapsed)} elapsed</RetroBadge>
      </div>

      {query && (
        <p className="mb-4 truncate text-sm text-retro-text-dim">
          Query: <span className="text-retro-text">{query}</span>
        </p>
      )}

      <div className="flex flex-col items-center gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
        {STEPS.map((step, index) => {
          const currentIndex = STATUS_ORDER.indexOf(STEPS[stepIndex].key);
          const thisIndex = STATUS_ORDER.indexOf(step.key);
          const isActive = thisIndex === currentIndex && active;
          const isDone = thisIndex < currentIndex;

          return (
            <div key={step.key} className="flex items-center gap-2">
              <div
                className={`graph-node min-w-[100px] ${
                  isActive ? "active" : isDone ? "done" : ""
                }`}
              >
                {step.label}
              </div>
              {index < STEPS.length - 1 && (
                <span className="graph-arrow hidden sm:inline" aria-hidden="true">
                  →
                </span>
              )}
            </div>
          );
        })}
      </div>

      <p className="mt-4 text-center text-xs text-retro-text-dim">
        Research runs synchronously — this may take several minutes depending on query complexity.
      </p>
    </div>
  );
}
