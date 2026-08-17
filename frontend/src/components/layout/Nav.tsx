"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FlaskConical, Layers, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";

const NAV_ITEMS = [
  { href: "/", label: "Research", icon: FlaskConical },
  { href: "/sessions", label: "Sessions", icon: Layers },
  { href: "/status", label: "Status", icon: Activity },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="relative z-10 border-b-2 border-black bg-card shadow-md">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <Link href="/" className="group flex items-center gap-3 no-underline">
          <span className="flex h-11 w-11 items-center justify-center border-2 border-black bg-primary font-head text-sm font-bold text-primary-foreground shadow-sm">
            AI
          </span>
          <div>
            <p className="font-head text-base leading-tight sm:text-lg">Research Analyst</p>
            <p className="text-sm text-muted-foreground">Multi-agent research platform</p>
          </div>
        </Link>

        <nav className="flex flex-wrap gap-2" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  buttonVariants({ variant: active ? "default" : "outline", size: "sm" }),
                  "gap-2"
                )}
              >
                <Icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
