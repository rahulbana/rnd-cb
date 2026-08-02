import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import Login from "./pages/Login";
import Home from "./pages/Home";
import Organizations from "./pages/Organizations";
import OrganizationDetail from "./pages/OrganizationDetail";
import Dashboards from "./pages/Dashboards";
import DashboardDetail from "./pages/DashboardDetail";
import Users from "./pages/Users";
import type { ReactNode } from "react";

function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Spinner label="Starting…" />;
  if (!me) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireSuperadmin({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  if (!me?.is_superadmin) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Home />} />
        <Route path="/organizations" element={<Organizations />} />
        <Route path="/organizations/:orgId" element={<OrganizationDetail />} />
        <Route path="/dashboards" element={<Dashboards />} />
        <Route path="/dashboards/:dashboardId" element={<DashboardDetail />} />
        <Route
          path="/users"
          element={
            <RequireSuperadmin>
              <Users />
            </RequireSuperadmin>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
