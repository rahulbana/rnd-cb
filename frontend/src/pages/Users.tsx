import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, Empty, ErrorText, RoleBadge, Spinner } from "../components/ui";

const EMPTY = { email: "", full_name: "", password: "", is_superadmin: false };

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

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      await api.createUser(form);
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
            <label className="checkbox">
              <input
                type="checkbox"
                checked={form.is_superadmin}
                onChange={(e) =>
                  setForm({ ...form, is_superadmin: e.target.checked })
                }
              />
              Grant superadmin
            </label>
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
