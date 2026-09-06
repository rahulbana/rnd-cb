import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "../components/Layout";
import { AuthPage } from "../features/auth/AuthPage";
import { ChatPage } from "../features/chat/ChatPage";
import { DocumentsPage } from "../features/documents/DocumentsPage";
import { useAuth } from "../store/auth";
import type { ReactNode } from "react";

function Protected({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuth((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}
