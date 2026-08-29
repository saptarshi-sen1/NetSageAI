import { createContext, useContext, useEffect, useState } from "react";

const STUDENT_NAME_KEY = "netsage.studentName";
const VIEW_MODE_KEY = "netsage.viewMode";

export type ViewMode = "admin" | "student";

interface StudentContextValue {
  studentName: string;
  setStudentName: (name: string) => void;
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}

const StudentContext = createContext<StudentContextValue | null>(null);

/**
 * This is intentionally NOT an authentication system - per the
 * project's explicit "don't add unnecessary auth" instruction, a
 * "student" here is just a free-text display name the person enters
 * once, persisted in localStorage so their attempt history survives a
 * page reload. Same lightweight-identity pattern the backend already
 * uses for review_service.py's `reviewer` field. Nothing here gates
 * access to any data - the admin dashboard and student workspace are
 * both reachable by anyone; the toggle just changes which view is shown.
 */
export function StudentProvider({ children }: { children: React.ReactNode }) {
  const [studentName, setStudentNameState] = useState<string>(() => {
    try {
      return localStorage.getItem(STUDENT_NAME_KEY) ?? "";
    } catch {
      return "";
    }
  });
  const [viewMode, setViewModeState] = useState<ViewMode>(() => {
    try {
      return (localStorage.getItem(VIEW_MODE_KEY) as ViewMode) ?? "admin";
    } catch {
      return "admin";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STUDENT_NAME_KEY, studentName);
    } catch {
      // localStorage unavailable (private browsing, etc.) - non-fatal,
      // the name just won't persist across reloads this session.
    }
  }, [studentName]);

  useEffect(() => {
    try {
      localStorage.setItem(VIEW_MODE_KEY, viewMode);
    } catch {
      // same as above
    }
  }, [viewMode]);

  return (
    <StudentContext.Provider
      value={{
        studentName,
        setStudentName: setStudentNameState,
        viewMode,
        setViewMode: setViewModeState,
      }}
    >
      {children}
    </StudentContext.Provider>
  );
}

export function useStudent(): StudentContextValue {
  const ctx = useContext(StudentContext);
  if (!ctx) {
    throw new Error("useStudent must be used within a StudentProvider");
  }
  return ctx;
}
