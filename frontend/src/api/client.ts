import type {
  AccessGrantInput,
  Dashboard,
  DashboardAccess,
  DBConnection,
  DBConnectionInput,
  MemberInput,
  Me,
  Membership,
  Organization,
  Role,
  Tokens,
  User,
} from "./types";

const ACCESS_KEY = "rbac.access_token";
const REFRESH_KEY = "rbac.refresh_token";

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function extractDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: unknown[] };
      const loc = Array.isArray(first.loc) ? first.loc.join(".") : "";
      return first.msg ? `${loc}: ${first.msg}` : fallback;
    }
  }
  return fallback;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  retryOnAuth?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, retryOnAuth = true } = opts;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const access = tokenStore.access;
  if (access) headers["Authorization"] = `Bearer ${access}`;

  const resp = await fetch(`/api${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // Transparent one-shot refresh on a 401.
  if (resp.status === 401 && retryOnAuth && tokenStore.refresh) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request<T>(path, { ...opts, retryOnAuth: false });
    }
  }

  if (resp.status === 204) {
    return undefined as T;
  }

  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;

  if (!resp.ok) {
    throw new ApiError(resp.status, extractDetail(data, resp.statusText));
  }
  return data as T;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const resp = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) {
    tokenStore.clear();
    return false;
  }
  const data = (await resp.json()) as { access_token: string };
  tokenStore.set(data.access_token);
  return true;
}

export const api = {
  // --- auth ---
  async login(email: string, password: string): Promise<Tokens> {
    const tokens = await request<Tokens>("/auth/login", {
      method: "POST",
      body: { email, password },
      retryOnAuth: false,
    });
    tokenStore.set(tokens.access_token, tokens.refresh_token);
    return tokens;
  },
  logout() {
    tokenStore.clear();
  },
  me(): Promise<Me> {
    return request<Me>("/me");
  },

  // --- users (superadmin) ---
  listUsers(search?: string): Promise<User[]> {
    const q = search ? `?search=${encodeURIComponent(search)}` : "";
    return request<User[]>(`/users${q}`);
  },
  createUser(input: {
    email: string;
    full_name: string;
    password: string;
    role: Role;
    organization_id?: number | null;
    dashboard_id?: number | null;
  }): Promise<User> {
    return request<User>("/users", { method: "POST", body: input });
  },
  updateUser(
    id: number,
    input: Partial<{
      full_name: string;
      password: string;
      is_active: boolean;
      is_superadmin: boolean;
    }>,
  ): Promise<User> {
    return request<User>(`/users/${id}`, { method: "PATCH", body: input });
  },
  deleteUser(id: number): Promise<void> {
    return request<void>(`/users/${id}`, { method: "DELETE" });
  },

  // --- organizations ---
  listOrganizations(): Promise<Organization[]> {
    return request<Organization[]>("/organizations");
  },
  getOrganization(id: number): Promise<Organization> {
    return request<Organization>(`/organizations/${id}`);
  },
  createOrganization(input: {
    name: string;
    email: string;
    contact_person: string;
    country: string;
    admins: MemberInput[];
  }): Promise<Organization> {
    return request<Organization>("/organizations", { method: "POST", body: input });
  },
  updateOrganization(
    id: number,
    input: Partial<{
      name: string;
      email: string;
      contact_person: string;
      country: string;
    }>,
  ): Promise<Organization> {
    return request<Organization>(`/organizations/${id}`, {
      method: "PATCH",
      body: input,
    });
  },
  deleteOrganization(id: number): Promise<void> {
    return request<void>(`/organizations/${id}`, { method: "DELETE" });
  },
  listMembers(orgId: number): Promise<Membership[]> {
    return request<Membership[]>(`/organizations/${orgId}/members`);
  },
  addMember(orgId: number, input: MemberInput): Promise<Membership> {
    return request<Membership>(`/organizations/${orgId}/members`, {
      method: "POST",
      body: input,
    });
  },
  removeMember(orgId: number, userId: number): Promise<void> {
    return request<void>(`/organizations/${orgId}/members/${userId}`, {
      method: "DELETE",
    });
  },

  // --- organization DB connections ---
  listConnections(orgId: number): Promise<DBConnection[]> {
    return request<DBConnection[]>(`/organizations/${orgId}/connections`);
  },
  createConnection(orgId: number, input: DBConnectionInput): Promise<DBConnection> {
    return request<DBConnection>(`/organizations/${orgId}/connections`, {
      method: "POST",
      body: input,
    });
  },
  updateConnection(
    orgId: number,
    connId: number,
    input: Partial<DBConnectionInput>,
  ): Promise<DBConnection> {
    return request<DBConnection>(`/organizations/${orgId}/connections/${connId}`, {
      method: "PATCH",
      body: input,
    });
  },
  deleteConnection(orgId: number, connId: number): Promise<void> {
    return request<void>(`/organizations/${orgId}/connections/${connId}`, {
      method: "DELETE",
    });
  },

  // --- dashboards ---
  listDashboards(organizationId?: number): Promise<Dashboard[]> {
    const q = organizationId ? `?organization_id=${organizationId}` : "";
    return request<Dashboard[]>(`/dashboards${q}`);
  },
  getDashboard(id: number): Promise<Dashboard> {
    return request<Dashboard>(`/dashboards/${id}`);
  },
  createDashboard(input: {
    organization_id: number;
    name: string;
    description?: string | null;
  }): Promise<Dashboard> {
    return request<Dashboard>("/dashboards", { method: "POST", body: input });
  },
  updateDashboard(
    id: number,
    input: Partial<{ name: string; description: string | null }>,
  ): Promise<Dashboard> {
    return request<Dashboard>(`/dashboards/${id}`, { method: "PATCH", body: input });
  },
  deleteDashboard(id: number): Promise<void> {
    return request<void>(`/dashboards/${id}`, { method: "DELETE" });
  },
  listAccess(dashboardId: number): Promise<DashboardAccess[]> {
    return request<DashboardAccess[]>(`/dashboards/${dashboardId}/access`);
  },
  grantAccess(dashboardId: number, input: AccessGrantInput): Promise<DashboardAccess> {
    return request<DashboardAccess>(`/dashboards/${dashboardId}/access`, {
      method: "POST",
      body: input,
    });
  },
  updateAccess(
    dashboardId: number,
    userId: number,
    role: string,
  ): Promise<DashboardAccess> {
    return request<DashboardAccess>(`/dashboards/${dashboardId}/access/${userId}`, {
      method: "PATCH",
      body: { role },
    });
  },
  revokeAccess(dashboardId: number, userId: number): Promise<void> {
    return request<void>(`/dashboards/${dashboardId}/access/${userId}`, {
      method: "DELETE",
    });
  },
};
