import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Card, Empty, RoleBadge } from "../components/ui";

export default function Home() {
  const { me } = useAuth();
  if (!me) return null;

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Welcome, {me.user.full_name.split(" ")[0]}</h1>
        <p className="muted">
          Your access level: <RoleBadge role={me.primary_role} />
        </p>
      </div>

      <div className="grid-3">
        <Card title="Administered organizations">
          {me.is_superadmin ? (
            <p>
              You are a <strong>superadmin</strong> — you can manage every
              organization, user and dashboard.
            </p>
          ) : me.admin_organizations.length === 0 ? (
            <Empty>You don't administer any organizations.</Empty>
          ) : (
            <ul className="list">
              {me.admin_organizations.map((o) => (
                <li key={o.organization_id}>
                  <Link to={`/organizations/${o.organization_id}`}>
                    {o.organization_name}
                  </Link>
                  <RoleBadge role={o.role} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Dashboard access">
          {me.dashboard_access.length === 0 ? (
            <Empty>No direct dashboard grants.</Empty>
          ) : (
            <ul className="list">
              {me.dashboard_access.map((d) => (
                <li key={d.dashboard_id}>
                  <Link to={`/dashboards/${d.dashboard_id}`}>
                    {d.dashboard_name}
                  </Link>
                  <span className="muted small">{d.organization_name}</span>
                  <RoleBadge role={d.role} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Your permissions">
          <ul className="perm-list">
            {me.permissions.map((p) => (
              <li key={p}>
                <code>{p}</code>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
