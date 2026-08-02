import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type {
  Dashboard,
  DBConnection,
  DBConnectionInput,
  DBType,
  Membership,
  Organization,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, Empty, ErrorText, Spinner } from "../components/ui";

export default function OrganizationDetail() {
  const { orgId } = useParams();
  const id = Number(orgId);
  const { me } = useAuth();

  const isAdminOfOrg =
    !!me &&
    (me.is_superadmin ||
      me.admin_organizations.some((o) => o.organization_id === id));

  return isAdminOfOrg ? (
    <AdminOrgView id={id} isSuperadmin={me!.is_superadmin} />
  ) : (
    <BrowseOrgView id={id} />
  );
}

/* ========================================================================== *
 * Viewer / developer: browse an org's dashboards as cards.
 * ========================================================================== */
function BrowseOrgView({ id }: { id: number }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [o, d] = await Promise.all([
          api.getOrganization(id),
          api.listDashboards(id),
        ]);
        setOrg(o);
        setDashboards(d);
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  if (loading) return <Spinner />;
  if (error) return <ErrorText message={error} />;
  if (!org) return <Empty>Organization not found.</Empty>;

  return (
    <div className="stack">
      <div className="page-head">
        <Link to="/organizations" className="back-link">
          ← Organizations
        </Link>
        <h1>{org.name}</h1>
        <p className="muted">Dashboards you can access in this organization.</p>
      </div>

      {dashboards.length === 0 ? (
        <Empty>You don't have access to any dashboards here yet.</Empty>
      ) : (
        <div className="grid-cards">
          {dashboards.map((d) => (
            <Link key={d.id} to={`/dashboards/${d.id}`} className="tile">
              <h3>{d.name}</h3>
              <p className="muted small">{d.description || "No description"}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

/* ========================================================================== *
 * Admin / superadmin: manage the organization.
 * ========================================================================== */
function AdminOrgView({ id, isSuperadmin }: { id: number; isSuperadmin: boolean }) {
  const navigate = useNavigate();
  const [org, setOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<Membership[]>([]);
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [o, m, d] = await Promise.all([
        api.getOrganization(id),
        api.listMembers(id),
        api.listDashboards(id),
      ]);
      setOrg(o);
      setMembers(m);
      setDashboards(d);
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

  if (loading) return <Spinner />;
  if (error && !org) return <ErrorText message={error} />;
  if (!org) return <Empty>Organization not found.</Empty>;

  const onDeleteOrg = async () => {
    if (!confirm(`Delete organization "${org.name}"? This removes its dashboards.`))
      return;
    try {
      await api.deleteOrganization(id);
      navigate("/organizations");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  };

  return (
    <div className="stack">
      <div className="page-head row">
        <div>
          <Link to="/organizations" className="back-link">
            ← Organizations
          </Link>
          <h1>{org.name}</h1>
          <p className="muted">{org.country}</p>
        </div>
        {isSuperadmin && (
          <button className="btn btn-danger" onClick={onDeleteOrg}>
            Delete organization
          </button>
        )}
      </div>

      <div className="grid-2">
        <OrgInfo org={org} onSaved={load} />
        <MembersPanel orgId={id} members={members} onChange={load} />
      </div>

      <DBConnectionsPanel orgId={id} />

      <DashboardsPanel orgId={id} dashboards={dashboards} onChange={load} />
    </div>
  );
}

function OrgInfo({ org, onSaved }: { org: Organization; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: org.name,
    email: org.email,
    contact_person: org.contact_person,
    country: org.country,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.updateOrganization(org.id, form);
      setSaved(true);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title="Organization details">
      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          Name
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
        </label>
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
          Contact person
          <input
            value={form.contact_person}
            onChange={(e) => setForm({ ...form, contact_person: e.target.value })}
            required
          />
        </label>
        <label>
          Country
          <input
            value={form.country}
            onChange={(e) => setForm({ ...form, country: e.target.value })}
            required
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

function MembersPanel({
  orgId,
  members,
  onChange,
}: {
  orgId: number;
  members: Membership[];
  onChange: () => void;
}) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [showNewUser, setShowNewUser] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const onAdd = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.addMember(orgId, {
        email,
        full_name: showNewUser ? fullName : undefined,
        password: showNewUser ? password : undefined,
      });
      setEmail("");
      setFullName("");
      setPassword("");
      setShowNewUser(false);
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add admin");
    } finally {
      setSaving(false);
    }
  };

  const onRemove = async (userId: number) => {
    if (!confirm("Remove this admin from the organization?")) return;
    try {
      await api.removeMember(orgId, userId);
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove");
    }
  };

  return (
    <Card title="Organization admins">
      {members.length === 0 ? (
        <Empty>No admins assigned yet.</Empty>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id}>
                <td>{m.user.full_name}</td>
                <td>{m.user.email}</td>
                <td className="right">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => onRemove(m.user.id)}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="inline-form" onSubmit={onAdd}>
        <input
          type="email"
          placeholder="admin@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
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
          Add admin
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

const DB_TYPES: DBType[] = ["postgres", "mysql", "mssql"];
const EMPTY_CONN: DBConnectionInput = {
  name: "",
  db_type: "postgres",
  host: "",
  port: null,
  database: "",
  username: "",
  password: "",
};

function DBConnectionsPanel({ orgId }: { orgId: number }) {
  const [conns, setConns] = useState<DBConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<DBConnectionInput>(EMPTY_CONN);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setConns(await api.listConnections(orgId));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load connections");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    load();
  }, [load]);

  const startCreate = () => {
    setEditingId(null);
    setForm(EMPTY_CONN);
    setShowForm(true);
  };

  const startEdit = (c: DBConnection) => {
    setEditingId(c.id);
    setForm({
      name: c.name,
      db_type: c.db_type,
      host: c.host,
      port: c.port,
      database: c.database,
      username: c.username,
      password: "", // blank = keep existing secret
    });
    setShowForm(true);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload: DBConnectionInput = {
        ...form,
        port: form.port ? Number(form.port) : null,
      };
      if (editingId !== null) {
        // Don't send an empty password (keeps the stored one).
        const { password, ...rest } = payload;
        await api.updateConnection(
          orgId,
          editingId,
          password ? payload : rest,
        );
      } else {
        await api.createConnection(orgId, payload);
      }
      setShowForm(false);
      setForm(EMPTY_CONN);
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save connection");
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (c: DBConnection) => {
    if (!confirm(`Delete connection "${c.name}"?`)) return;
    try {
      await api.deleteConnection(orgId, c.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  };

  return (
    <Card
      title="Database connections"
      actions={
        <button className="btn btn-primary btn-sm" onClick={startCreate}>
          New connection
        </button>
      }
    >
      {loading ? (
        <Spinner />
      ) : conns.length === 0 ? (
        <Empty>No database connections configured for this organization.</Empty>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Host</th>
              <th>Database</th>
              <th>User</th>
              <th className="right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {conns.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>
                  <span className={`badge badge-${c.db_type}`}>{c.db_type}</span>
                </td>
                <td className="mono">
                  {c.host}
                  {c.port ? `:${c.port}` : ""}
                </td>
                <td>{c.database}</td>
                <td>{c.username}</td>
                <td className="right actions">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => startEdit(c)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => onDelete(c)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showForm && (
        <form className="conn-form" onSubmit={onSubmit}>
          <div className="conn-grid">
            <label>
              Name
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </label>
            <label>
              Type
              <select
                value={form.db_type}
                onChange={(e) =>
                  setForm({ ...form, db_type: e.target.value as DBType })
                }
              >
                {DB_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Host
              <input
                value={form.host}
                onChange={(e) => setForm({ ...form, host: e.target.value })}
                required
              />
            </label>
            <label>
              Port
              <input
                type="number"
                value={form.port ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    port: e.target.value ? Number(e.target.value) : null,
                  })
                }
                min={1}
                max={65535}
              />
            </label>
            <label>
              Database
              <input
                value={form.database}
                onChange={(e) => setForm({ ...form, database: e.target.value })}
                required
              />
            </label>
            <label>
              Username
              <input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={form.password ?? ""}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder={
                  editingId !== null ? "•••••• (unchanged)" : "Required"
                }
                required={editingId === null}
              />
            </label>
          </div>
          <div className="form-actions">
            <ErrorText message={error} />
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </button>
            <button className="btn btn-primary btn-sm" disabled={saving}>
              {saving ? "Saving…" : editingId !== null ? "Save" : "Create"}
            </button>
          </div>
        </form>
      )}
      {!showForm && <ErrorText message={error} />}
    </Card>
  );
}

function DashboardsPanel({
  orgId,
  dashboards,
  onChange,
}: {
  orgId: number;
  dashboards: Dashboard[];
  onChange: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.createDashboard({
        organization_id: orgId,
        name,
        description: description || null,
      });
      setName("");
      setDescription("");
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create dashboard");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title="Dashboards">
      {dashboards.length === 0 ? (
        <Empty>No dashboards in this organization yet.</Empty>
      ) : (
        <div className="grid-cards">
          {dashboards.map((d) => (
            <Link key={d.id} to={`/dashboards/${d.id}`} className="tile">
              <h3>{d.name}</h3>
              <p className="muted small">{d.description || "No description"}</p>
            </Link>
          ))}
        </div>
      )}

      <form className="inline-form" onSubmit={onCreate}>
        <input
          placeholder="Dashboard name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <button className="btn btn-primary btn-sm" disabled={saving}>
          Add dashboard
        </button>
      </form>
      <ErrorText message={error} />
    </Card>
  );
}
