import { NavLink, useNavigate } from "react-router-dom";
import { Activity, GraduationCap, LayoutDashboard, ListChecks, ShieldCheck } from "lucide-react";
import { useStudent } from "../context/StudentContext";
import ThemeToggle from "./ThemeToggle";
import { UserButton } from "@clerk/clerk-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/cases", label: "Cases", icon: ListChecks, end: false },
  { to: "/workspace", label: "Workspace", icon: GraduationCap, end: false },
];

export default function NavBar() {
  const { viewMode, setViewMode } = useStudent();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-30 border-b border-surface-border bg-surface-1/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <NavLink to="/" className="flex items-center gap-2.5 group">
          <span className="relative flex h-8 w-8 items-center justify-center rounded-md bg-signal-passDim">
            <Activity className="text-signal-pass" size={18} strokeWidth={2.25} />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-signal-pass shadow-[0_0_6px_1px_rgba(47,217,138,0.7)]" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-mono text-[15px] font-semibold tracking-tight text-ink-primary">
              NetSage<span className="text-signal-pass">AI</span>
            </span>
            <span className="mt-0.5 text-[10px] uppercase tracking-[0.14em] text-ink-muted">
              Human-reviewed diagnostics
            </span>
          </span>
        </NavLink>

        <div className="flex items-center gap-3">
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-surface-2 text-ink-primary"
                      : "text-ink-secondary hover:bg-surface-2/60 hover:text-ink-primary"
                  }`
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </nav>

          <div
            className="flex items-center rounded-md border border-surface-border bg-surface-2 p-0.5 text-xs"
            role="group"
            aria-label="View mode"
          >
            <button
              onClick={() => { setViewMode("admin"); navigate("/"); }}
              className={`flex items-center gap-1 rounded px-2.5 py-1 font-medium transition-colors ${
                viewMode === "admin"
                  ? "bg-signal-info text-[#0A2733]"
                  : "text-ink-muted hover:text-ink-secondary"
              }`}
              title="Admin/instructor view: dashboard, case management, review log"
            >
              <ShieldCheck size={13} />
              Admin
            </button>
            <button
              onClick={() => { setViewMode("student"); navigate("/workspace"); }}
              className={`flex items-center gap-1 rounded px-2.5 py-1 font-medium transition-colors ${
                viewMode === "student"
                  ? "bg-signal-pass text-[#06231A]"
                  : "text-ink-muted hover:text-ink-secondary"
              }`}
              title="Student view: practice workspace and progress"
            >
              <GraduationCap size={13} />
              Student
            </button>
          </div>
          
          <ThemeToggle />
          <UserButton afterSignOutUrl="/" />
        </div>
      </div>
    </header>
  );
}
