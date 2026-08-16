type BadgeVariant = "ok" | "warn" | "error" | "info" | "neutral";

const VARIANT_CLASS: Record<BadgeVariant, string> = {
  ok: "badge-ok",
  warn: "badge-warn",
  error: "badge-error",
  info: "badge-info",
  neutral: "badge-neutral",
};

export function RetroBadge({
  children,
  variant = "neutral",
  title,
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
  title?: string;
}) {
  return (
    <span className={`retro-badge ${VARIANT_CLASS[variant]}`} title={title}>
      {children}
    </span>
  );
}
