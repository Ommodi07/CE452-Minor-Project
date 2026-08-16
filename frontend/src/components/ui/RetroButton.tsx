import type { ButtonHTMLAttributes, ReactNode } from "react";

interface RetroButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  children: ReactNode;
}

export function RetroButton({
  variant = "primary",
  children,
  className = "",
  ...props
}: RetroButtonProps) {
  return (
    <button
      className={`retro-btn ${variant === "secondary" ? "retro-btn-secondary" : ""} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
