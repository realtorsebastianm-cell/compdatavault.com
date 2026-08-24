const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type DealType = "sale" | "lease";

export type PropertyType =
  | "office"
  | "industrial"
  | "retail"
  | "land"
  | "multifamily"
  | "other";

export interface SaleComp {
  id: string;
  flyer_id: string;
  address: string;
  city: string | null;
  state: string | null;
  submarket: string | null;
  property_type: PropertyType;
  building_sf: number | null;
  lot_sf: number | null;
  price: number | null;
  price_per_sf: number | null;
  cap_rate: number | null;
  num_units: number | null;
  price_per_unit: number | null;
  zoning: string | null;
  broker_name: string | null;
  brokerage: string | null;
  date_received: string;
  notes: string | null;
}

export interface LeaseComp {
  id: string;
  flyer_id: string;
  address: string;
  city: string | null;
  state: string | null;
  submarket: string | null;
  property_type: PropertyType;
  building_sf: number | null;
  lot_sf: number | null;
  rate: number | null;
  rate_type: "per_sf_year" | "per_sf_month" | "flat_month" | null;
  term_months: number | null;
  expense_type: "nnn" | "gross" | "modified_gross" | "unknown";
  zoning: string | null;
  broker_name: string | null;
  brokerage: string | null;
  date_received: string;
  notes: string | null;
}

export interface ComparisonOut {
  metric: string;
  new_value: number;
  baseline_avg: number;
  pct_diff: number;
  comp_count: number;
}

export interface FlyerResult {
  flyer_id: string;
  deal_type: DealType | null;
  status: string;
  comp_id: string | null;
  low_confidence_fields: string[];
  comparison: ComparisonOut | null;
  error: string | null;
}

export interface AskMatch {
  deal_type: DealType;
  comp: SaleComp | LeaseComp;
  reason: string | null;
}

export interface AskResponse {
  matches: AskMatch[];
  understood: Record<string, unknown>;
  residual_criteria: string | null;
}

const TOKEN_KEY = "dealarchive_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  signup: (email: string, password: string) =>
    request<{ token: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<{ token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<{ email: string; forwarding_address: string }>("/me"),

  uploadFlyer: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<FlyerResult>("/upload", { method: "POST", body: form });
  },

  saleComps: (params: Record<string, string> = {}) =>
    request<SaleComp[]>(`/sale-comps?${new URLSearchParams(params)}`),
  leaseComps: (params: Record<string, string> = {}) =>
    request<LeaseComp[]>(`/lease-comps?${new URLSearchParams(params)}`),
  saleComp: (id: string) => request<SaleComp>(`/sale-comps/${id}`),
  leaseComp: (id: string) => request<LeaseComp>(`/lease-comps/${id}`),

  ask: (query: string) =>
    request<AskResponse>("/ask", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),

  async exportComps(saleCompIds: string[], leaseCompIds: string[]): Promise<void> {
    const token = getToken();
    const headers = new Headers({ "Content-Type": "application/json" });
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const res = await fetch(`${API_URL}/export`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        sale_comp_ids: saleCompIds,
        lease_comp_ids: leaseCompIds,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail || res.statusText);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "compdatavault-comps.xlsx";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  async flyerFileBlobUrl(flyerId: string): Promise<string> {
    const token = getToken();
    const res = await fetch(`${API_URL}/flyers/${flyerId}/file`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError(res.status, res.statusText);
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },
};

export const PROPERTY_TYPES: PropertyType[] = [
  "office",
  "industrial",
  "retail",
  "land",
  "multifamily",
  "other",
];
