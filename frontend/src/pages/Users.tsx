import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Dashboard, Organization, Role, User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, Empty, ErrorText, RoleBadge, Spinner } from "../components/ui";

const EMPTY = {
  email: "",
  full_name: "",
  password: "",
  role: "viewer" as Role,
  organization_id: "" as string,
  dashboard_id: "" as string,
};

export default function Users() {
  const { me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [form, setForm] = useState(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Data for the role/org/dashboard selectors.
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgDashboards, setOrgDashboards] = useState<Dashboard[]>([]);

  const load = async (q?: string) => {
    setLoading(true);
    try {
      setUsers(await api.listUsers(q));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Load organizations once (for admin/developer/viewer assignment).
  useEffect(() => {
    api.listOrganizations().then(setOrgs).catch(() => setOrgs([]));
  }, []);

  // When a developer/viewer picks an org, fetch that org's dashboards.
  const needsDashboard = form.role === "developer" || form.role === "viewer";
  useEffect(() => {
    if (needsDashboard && form.organization_id) {
      api
        .listDashboards(Number(form.organization_id))
        .then(setOrgDashboards)
        .catch(() => setOrgDashboards([]));
    } else {
      setOrgDashboards([]);
    }
  }, [needsDashboard, form.organization_id]);

  const setRole = (role: Role) =>
    setForm((f) => ({ ...f, role, dashboard_id: "" }));

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      await api.createUser({
        email: form.email,
        full_name: form.full_name,
        password: form.password,
        role: form.role,
        organization_id: form.organization_id
          ? Number(form.organization_id)
          : null,
        dashboard_id: form.dashboard_id ? Number(form.dashboard_id) : null,
      });
      setForm(EMPTY);
      setShowForm(false);
      await load(search);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (u: User) => {
    try {
      await api.updateUser(u.id, { is_active: !u.is_active });
      await load(search);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update");
    }
  };

  const toggleSuperadmin = async (u: User) => {
    try {
      await api.updateUser(u.id, { is_superadmin: !u.is_superadmin });
      await load(search);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update");
    }
  };

  const onDelete = async (u: User) => {
    if (!confirm(`Delete user ${u.email}?`)) return;
    try {
      await api.deleteUser(u.id);
      await load(search);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  };

  return (
    <div className="stack">
      <div className="page-head row">
        <div>
          <h1>Users</h1>
          <p className="muted">All accounts on the platform.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New user"}
        </button>
      </div>

      {showForm && (
        <Card title="Create user">
          <form className="form-grid" onSubmit={onCreate}>
            <label>
              Email
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </label>
            <label>
              Full name
              <input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                minLength={8}
                required
              />
            </label>
            <label>
              Role
              <select
                value={form.role}
                onChange={(e) => setRole(e.target.value as Role)}
              >
                <option value="viewer">viewer — read a dashboard</option>
                <option value="developer">developer — edit a dashboard</option>
                <option value="admin">admin — manage an organization</option>
                <option value="superadmin">superadmin — full platform access</option>
              </select>
            </label>

            {form.role !== "superadmin" && (
              <label>
                Organization{" "}
                {form.role === "admin" ? "(required)" : "(optional)"}
                <select
                  value={form.organization_id}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      organization_id: e.target.value,
                      dashboard_id: "",
                    })
                  }
                  required={form.role === "admin"}
                >
                  <option value="">— none —</option>
                  {orgs.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {needsDashboard && form.organization_id && (
              <label>
                Dashboard grant (optional)
                <select
                  value={form.dashboard_id}
                  onChange={(e) =>
                    setForm({ ...form, dashboard_id: e.target.value })
                  }
                >
                  <option value="">— grant later —</option>
                  {orgDashboards.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="form-actions">
              <ErrorText message={formError} />
              <button className="btn btn-primary" disabled={saving}>
                {saving ? "Creating…" : "Create user"}
              </button>
            </div>
          </form>
        </Card>
      )}

      <div className="toolbar">
        <input
          className="search"
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load(search)}
        />
        <button className="btn btn-ghost" onClick={() => load(search)}>
          Search
        </button>
      </div>

      <ErrorText message={error} />

      {loading ? (
        <Spinner />
      ) : users.length === 0 ? (
        <Empty>No users found.</Empty>
      ) : (
        <Card>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th className="right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isSelf = u.id === me?.user.id;
                return (
                  <tr key={u.id}>
                    <td>{u.full_name}</td>
                    <td>{u.email}</td>
                    <td>
                      <RoleBadge role={u.is_superadmin ? "superadmin" : "user"} />
                    </td>
                    <td>
                      <span className={u.is_active ? "ok-text" : "muted"}>
                        {u.is_active ? "active" : "disabled"}
                      </span>
                    </td>
                    <td className="right actions">
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => toggleSuperadmin(u)}
                        disabled={isSelf}
                        title={isSelf ? "You can't change your own role" : ""}
                      >
                        {u.is_superadmin ? "Revoke admin" : "Make superadmin"}
                      </button>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => toggleActive(u)}
                        disabled={isSelf}
                      >
                        {u.is_active ? "Disable" : "Enable"}
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => onDelete(u)}
                        disabled={isSelf}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
