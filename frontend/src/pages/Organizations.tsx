import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Organization } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, Empty, ErrorText, Spinner } from "../components/ui";

const EMPTY = { name: "", email: "", contact_person: "", country: "" };

export default function Organizations() {
  const { me } = useAuth();
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const canCreate = me?.is_superadmin ?? false;

  const load = async () => {
    setLoading(true);
    try {
      setOrgs(await api.listOrganizations());
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
      await api.createOrganization(form);
      setForm(EMPTY);
      setShowForm(false);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to create");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="stack">
      <div className="page-head row">
        <div>
          <h1>Organizations</h1>
          <p className="muted">
            {canCreate
              ? "Every organization in the platform."
              : "Organizations you administer."}
          </p>
        </div>
        {canCreate && (
          <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "New organization"}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <Card title="Create organization">
          <form className="form-grid" onSubmit={onCreate}>
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
                onChange={(e) =>
                  setForm({ ...form, contact_person: e.target.value })
                }
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
              <ErrorText message={formError} />
              <button className="btn btn-primary" disabled={saving}>
                {saving ? "Creating…" : "Create"}
              </button>
            </div>
          </form>
        </Card>
      )}

      <ErrorText message={error} />

      {loading ? (
        <Spinner />
      ) : orgs.length === 0 ? (
        <Empty>No organizations yet.</Empty>
      ) : (
        <div className="grid-cards">
          {orgs.map((org) => (
            <Link key={org.id} to={`/organizations/${org.id}`} className="tile">
              <h3>{org.name}</h3>
              <dl>
                <div>
                  <dt>Contact</dt>
                  <dd>{org.contact_person}</dd>
                </div>
                <div>
                  <dt>Email</dt>
                  <dd>{org.email}</dd>
                </div>
                <div>
                  <dt>Country</dt>
                  <dd>{org.country}</dd>
                </div>
              </dl>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
