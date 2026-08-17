"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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
    <Card className="loading-pulse">
      <CardContent className="space-y-4 pt-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-head text-lg blink-cursor">Running research pipeline...</p>
          <Badge variant="info">{formatTime(elapsed)} elapsed</Badge>
        </div>

        {query && (
          <p className="truncate text-sm text-muted-foreground">
            Query: <span className="font-medium text-foreground">{query}</span>
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
                <div className={`graph-node min-w-[100px] ${isActive ? "active" : isDone ? "done" : ""}`}>
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

        <p className="text-center text-xs text-muted-foreground">
          Research runs synchronously — this may take several minutes depending on query complexity.
        </p>
      </CardContent>
    </Card>
  );
}
