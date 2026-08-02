import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Dashboard, DashboardAccess } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, Empty, ErrorText, Spinner } from "../components/ui";

export default function DashboardDetail() {
  const { dashboardId } = useParams();
  const id = Number(dashboardId);
  const { me } = useAuth();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setDashboard(await api.getDashboard(id));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // Capabilities derived from the current user's roles.
  const { canManage, canEdit } = useMemo(() => {
    if (!me || !dashboard) return { canManage: false, canEdit: false };
    const isOrgAdmin =
      me.is_superadmin ||
      me.admin_organizations.some(
        (o) => o.organization_id === dashboard.organization_id,
      );
    const grant = me.dashboard_access.find((d) => d.dashboard_id === dashboard.id);
    const isDeveloper = grant?.role === "developer";
    return { canManage: isOrgAdmin, canEdit: isOrgAdmin || isDeveloper };
  }, [me, dashboard]);

  if (loading) return <Spinner />;
  if (error && !dashboard) return <ErrorText message={error} />;
  if (!dashboard) return <Empty>Dashboard not found.</Empty>;

  const onDelete = async () => {
    if (!confirm(`Delete dashboard "${dashboard.name}"?`)) return;
    try {
      await api.deleteDashboard(id);
      navigate("/dashboards");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  };

  return (
    <div className="stack">
      <div className="page-head row">
        <div>
          <Link to="/dashboards" className="back-link">
            ← Dashboards
          </Link>
          <h1>{dashboard.name}</h1>
        </div>
        {canManage && (
          <button className="btn btn-danger" onClick={onDelete}>
            Delete dashboard
          </button>
        )}
      </div>

      <div className="grid-2">
        <DashboardInfo
          dashboard={dashboard}
          canEdit={canEdit}
          onSaved={load}
        />
        {canManage ? (
          <AccessPanel dashboardId={id} />
        ) : (
          <Card title="Access">
            <p className="muted">
              Access management is available to organization admins.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}

function DashboardInfo({
  dashboard,
  canEdit,
  onSaved,
}: {
  dashboard: Dashboard;
  canEdit: boolean;
  onSaved: () => void;
}) {
  const [name, setName] = useState(dashboard.name);
  const [description, setDescription] = useState(dashboard.description ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.updateDashboard(dashboard.id, {
        name,
        description: description || null,
      });
      setSaved(true);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (!canEdit) {
    return (
      <Card title="Details">
        <dl className="detail-list">
          <div>
            <dt>Name</dt>
            <dd>{dashboard.name}</dd>
          </div>
          <div>
            <dt>Description</dt>
            <dd>{dashboard.description || "—"}</dd>
          </div>
        </dl>
        <p className="muted small">You have read-only access to this dashboard.</p>
      </Card>
    );
  }

  return (
    <Card title="Details">
      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
          />
        </label>
        <div className="form-actions">
          <ErrorText message={error} />
          {saved && <span className="ok-text">Saved</span>}
          <button className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </Card>
  );
}

function AccessPanel({ dashboardId }: { dashboardId: number }) {
  const [grants, setGrants] = useState<DashboardAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"viewer" | "developer">("viewer");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [showNewUser, setShowNewUser] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setGrants(await api.listAccess(dashboardId));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load access");
    } finally {
      setLoading(false);
    }
  }, [dashboardId]);

  useEffect(() => {
    load();
  }, [load]);

  const onGrant = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.grantAccess(dashboardId, {
        email,
        role,
        full_name: showNewUser ? fullName : undefined,
        password: showNewUser ? password : undefined,
      });
      setEmail("");
      setFullName("");
      setPassword("");
      setShowNewUser(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to grant access");
    } finally {
      setSaving(false);
    }
  };

  const onChangeRole = async (userId: number, newRole: string) => {
    try {
      await api.updateAccess(dashboardId, userId, newRole);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update");
    }
  };

  const onRevoke = async (userId: number) => {
    if (!confirm("Revoke this user's access?")) return;
    try {
      await api.revokeAccess(dashboardId, userId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to revoke");
    }
  };

  return (
    <Card title="Access grants">
      {loading ? (
        <Spinner />
      ) : grants.length === 0 ? (
        <Empty>No developers or viewers assigned yet.</Empty>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {grants.map((g) => (
              <tr key={g.id}>
                <td>
                  <div>{g.user.full_name}</div>
                  <div className="muted small">{g.user.email}</div>
                </td>
                <td>
                  <select
                    value={g.role}
                    onChange={(e) => onChangeRole(g.user.id, e.target.value)}
                  >
                    <option value="viewer">viewer</option>
                    <option value="developer">developer</option>
                  </select>
                </td>
                <td className="right">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => onRevoke(g.user.id)}
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="inline-form" onSubmit={onGrant}>
        <input
          type="email"
          placeholder="user@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as "viewer" | "developer")}
        >
          <option value="viewer">viewer</option>
          <option value="developer">developer</option>
        </select>
        {showNewUser && (
          <>
            <input
              placeholder="Full name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Temp password (min 8)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </>
        )}
        <button className="btn btn-primary btn-sm" disabled={saving}>
          Grant
        </button>
      </form>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={showNewUser}
          onChange={(e) => setShowNewUser(e.target.checked)}
        />
        Create a new user (if this email isn't registered yet)
      </label>
      <ErrorText message={error} />
    </Card>
  );
}
