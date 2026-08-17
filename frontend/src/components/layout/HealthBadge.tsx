"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { getHealth } from "@/lib/api";

export function HealthBadge() {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [appName, setAppName] = useState("");

  useEffect(() => {
    async function check() {
      try {
        const health = await getHealth();
        setAppName(health.app);
        setStatus(health.status === "ok" ? "ok" : "error");
      } catch {
        setStatus("error");
      }
    }

    void check();
  }, []);

  if (status === "loading") {
    return <Badge variant="info">Checking...</Badge>;
  }

  if (status === "error") {
    return <Badge variant="destructive">Offline</Badge>;
  }

  return (
    <Badge variant="success" title={appName}>
      Online
    </Badge>
  );
}
