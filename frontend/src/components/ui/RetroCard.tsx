import type { ReactNode } from "react";

interface RetroCardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  badge?: ReactNode;
}

export function RetroCard({ title, subtitle, children, className = "", badge }: RetroCardProps) {
  return (
    <section className={`retro-panel p-4 sm:p-6 ${className}`}>
      {(title || badge) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-2 border-b border-retro-border pb-3">
          <div>
            {title && (
              <h2 className="font-terminal text-xl text-retro-text-bright sm:text-2xl">{title}</h2>
            )}
            {subtitle && <p className="mt-1 text-sm text-retro-text-dim">{subtitle}</p>}
          </div>
          {badge}
        </div>
      )}
      {children}
    </section>
  );
}
