"use client";

import { useEffect, useState } from "react";
import { RetroBadge } from "@/components/ui/RetroBadge";
import { getHealth, ApiClientError } from "@/lib/api";

export function HealthBadge() {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [appName, setAppName] = useState("");

  useEffect(() => {
    async function check() {
      try {
        const health = await getHealth();
        setAppName(health.app);
        setStatus(health.status === "ok" ? "ok" : "error");
      } catch (err) {
        if (err instanceof ApiClientError && err.status === 0) {
          setStatus("error");
        } else {
          setStatus("error");
        }
      }
    }

    void check();
  }, []);

  if (status === "loading") {
    return <RetroBadge variant="info">Checking...</RetroBadge>;
  }

  if (status === "error") {
    return <RetroBadge variant="error">Offline</RetroBadge>;
  }

  return (
    <RetroBadge variant="ok" title={appName}>
      Online
    </RetroBadge>
  );
}
