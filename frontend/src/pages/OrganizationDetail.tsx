import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Dashboard, Membership, Organization } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, Empty, ErrorText, Spinner } from "../components/ui";

export default function OrganizationDetail() {
  const { orgId } = useParams();
  const id = Number(orgId);
  const { me } = useAuth();
  const navigate = useNavigate();

  const [org, setOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<Membership[]>([]);
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isSuperadmin = me?.is_superadmin ?? false;

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
