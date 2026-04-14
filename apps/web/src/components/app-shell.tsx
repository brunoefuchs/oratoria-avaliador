"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactNode } from "react";

interface AppShellProps {
  children: ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "7xl";
  showBack?: boolean;
  backHref?: string;
  backLabel?: string;
  sticky?: boolean;
}

const MAX_WIDTHS: Record<string, string> = {
  sm: "max-w-md",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-3xl",
  "2xl": "max-w-4xl",
  "3xl": "max-w-5xl",
  "7xl": "max-w-7xl",
};

export function AppShell({
  children,
  maxWidth = "lg",
  showBack,
  backHref,
  backLabel = "Voltar",
  sticky = true,
}: AppShellProps) {
  const router = useRouter();
  const containerClass = MAX_WIDTHS[maxWidth];

  const handleBack = () => {
    if (backHref) router.push(backHref);
    else router.back();
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header
        className={`${
          sticky ? "sticky top-0 z-40" : ""
        } glass-low ghost-border border-b border-outline-variant/10`}
      >
        <div
          className={`mx-auto ${containerClass} px-4 md:px-6 flex items-center justify-between h-14 md:h-16`}
        >
          <div className="flex items-center gap-3 min-w-0">
            {showBack ? (
              <button
                onClick={handleBack}
                className="flex items-center gap-2 text-on-surface-variant hover:text-secondary transition-colors py-1 px-2 -ml-2 rounded-lg"
                aria-label={backLabel}
              >
                <span className="material-symbols-outlined text-xl">
                  arrow_back
                </span>
                <span className="hidden sm:inline text-sm font-medium">
                  {backLabel}
                </span>
              </button>
            ) : (
              <Link
                href="/"
                className="flex items-center gap-2 text-on-surface hover:text-secondary transition-colors"
              >
                <span
                  className="material-symbols-outlined text-secondary text-2xl"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  graphic_eq
                </span>
                <span className="font-headline text-base md:text-lg font-bold tracking-tight">
                  Oratória
                </span>
              </Link>
            )}
          </div>

          <nav className="flex items-center gap-1">
            <Link
              href="/"
              className="flex items-center gap-2 px-3 py-2 rounded-full text-on-surface-variant hover:text-secondary hover:bg-surface-container-high transition-colors text-sm"
              aria-label="Início"
            >
              <span className="material-symbols-outlined text-xl">home</span>
              <span className="hidden md:inline">Início</span>
            </Link>
            <Link
              href="/evolution"
              className="flex items-center gap-2 px-3 py-2 rounded-full text-on-surface-variant hover:text-secondary hover:bg-surface-container-high transition-colors text-sm"
              aria-label="Evolução"
            >
              <span className="material-symbols-outlined text-xl">
                insights
              </span>
              <span className="hidden md:inline">Evolução</span>
            </Link>
          </nav>
        </div>
      </header>

      <main
        className={`flex-1 mx-auto w-full ${containerClass} px-4 md:px-6 py-6 md:py-10`}
      >
        {children}
      </main>
    </div>
  );
}
