"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Research", icon: "▶" },
  { href: "/sessions", label: "Sessions", icon: "◈" },
  { href: "/status", label: "Status", icon: "◎" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="relative z-10 border-b-2 border-retro-border bg-retro-panel/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <Link href="/" className="group flex items-center gap-3 no-underline">
          <span className="flex h-10 w-10 items-center justify-center border-2 border-retro-border-bright bg-retro-bg text-lg text-retro-amber shadow-[0_0_12px_rgba(251,191,36,0.3)]">
            AI
          </span>
          <div>
            <p className="font-display text-[0.55rem] leading-tight tracking-wider text-retro-text-bright sm:text-[0.65rem]">
              RESEARCH ANALYST
            </p>
            <p className="font-terminal text-sm text-retro-text-dim sm:text-base">
              v1.0 // retro terminal
            </p>
          </div>
        </Link>

        <nav className="flex flex-wrap gap-2" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`retro-btn px-3 py-2 text-sm sm:px-4 ${
                  active ? "border-retro-amber text-retro-amber" : ""
                }`}
                aria-current={active ? "page" : undefined}
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
