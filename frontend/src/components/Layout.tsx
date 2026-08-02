import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { RoleBadge } from "./ui";

export default function Layout() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate("/login");
  };

  const isSuperadmin = me?.is_superadmin ?? false;

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">◆</span> RBAC Platform
        </div>
        <nav>
          <NavLink to="/" end>
            Overview
          </NavLink>
          {/* Everyone browses via organization cards, then drills into
              dashboards; superadmins/admins also manage from here. */}
          <NavLink to="/organizations">Organizations</NavLink>
          <NavLink to="/dashboards">Dashboards</NavLink>
          {isSuperadmin && <NavLink to="/users">Users</NavLink>}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <div />
          <div className="user-chip">
            <div className="user-meta">
              <strong>{me?.user.full_name}</strong>
              <span>{me?.user.email}</span>
            </div>
            {me && <RoleBadge role={me.primary_role} />}
            <button className="btn btn-ghost" onClick={onLogout}>
              Sign out
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
