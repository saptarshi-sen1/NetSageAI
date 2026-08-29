import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(() => {
    // Read from localStorage or default to true (since app was originally dark-mode only)
    const stored = localStorage.getItem("theme");
    if (stored) return stored === "dark";
    // Check OS preference
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return false;
    }
    return true; // Default dark
  });

  useEffect(() => {
    const root = window.document.documentElement;
    if (isDark) {
      root.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      root.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [isDark]);

  return (
    <button
      onClick={() => setIsDark(!isDark)}
      className="flex h-8 w-8 items-center justify-center rounded-md border border-surface-border bg-surface-2 text-ink-secondary transition-colors hover:bg-surface-3 hover:text-ink-primary"
      aria-label="Toggle theme"
      title={`Switch to ${isDark ? "light" : "dark"} mode`}
    >
      {isDark ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
}
