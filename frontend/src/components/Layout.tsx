import { NavLink, Outlet, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { Button } from "./ui";
import { useAuth } from "../store/auth";

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <div className="flex items-center gap-6">
          <span className="font-semibold text-slate-800">RAG Platform</span>
          <nav className="flex gap-1">
            {[
              { to: "/chat", label: "Chat" },
              { to: "/documents", label: "Documents" },
              ...(user?.role === "admin" ? [{ to: "/admin", label: "Admin" }] : []),
            ].map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    "rounded-md px-3 py-1.5 text-sm font-medium",
                    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <span>{user?.email}</span>
          {user?.role === "admin" && (
            <span className="rounded bg-brand-50 px-1.5 py-0.5 text-xs text-brand-700">
              admin
            </span>
          )}
          <Button
            variant="ghost"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </Button>
        </div>
      </header>
      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
