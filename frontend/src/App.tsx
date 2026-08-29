import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import Dashboard from "./pages/Dashboard";
import CaseList from "./pages/CaseList";
import CaseDetail from "./pages/CaseDetail";
import StudentWorkspace from "./pages/StudentWorkspace";
import PracticeMode from "./pages/PracticeMode";
import { StudentProvider } from "./context/StudentContext";
import { SignedIn, SignedOut, RedirectToSignIn } from "@clerk/clerk-react";

export default function App() {
  return (
    <StudentProvider>
      <SignedIn>
        <div className="min-h-screen bg-surface-0">
          <NavBar />
          <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/cases" element={<CaseList />} />
              <Route path="/cases/:caseId" element={<CaseDetail />} />
              <Route path="/workspace" element={<StudentWorkspace />} />
              <Route path="/practice/:caseId" element={<PracticeMode />} />
              <Route
                path="*"
                element={
                  <div className="py-16 text-center text-ink-muted">Page not found.</div>
                }
              />
            </Routes>
          </main>
          <footer className="border-t border-surface-border py-6 text-center text-[11px] text-ink-muted">
            NetSage AI - a course project. AI diagnoses are suggestions only; nothing here executes
            configuration changes on real or simulated devices.
          </footer>
        </div>
      </SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </StudentProvider>
  );
}
