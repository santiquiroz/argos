import axios from "axios";

const KEY_STORAGE = "argos_api_key";

export function getApiKey(): string {
  return localStorage.getItem(KEY_STORAGE) ?? "";
}
export function setApiKey(key: string): void {
  localStorage.setItem(KEY_STORAGE, key);
}

const client = axios.create({ baseURL: "/api" });
client.interceptors.request.use((config) => {
  config.headers["X-API-Key"] = getApiKey();
  return config;
});

export interface Health {
  status: string;
  version: string;
  device: string;
  ingest: string;
  pipeline_running: boolean;
  analyzers: { name: string; available: boolean }[];
}
export interface Person {
  id: string;
  name: string | null;
  enrolled: number;
  last_seen: number;
}
export interface ArgosEvent {
  id: string;
  person_id: string | null;
  camera: string | null;
  kind: string;
  label: string | null;
  score: number | null;
  ts: number;
}
export interface Camera {
  name: string;
  url: string;
  enabled: boolean;
}
export interface DiscoveredCamera {
  ip: string;
  vendor: string;
  model: string | null;
  channels: number;
  reachable_http: boolean;
  reachable_rtsp: boolean;
  insecure: boolean;
  insecure_default_credential: string | null;
  rtsp_urls: string[];
}
export interface SettingsSnapshot {
  device: string;
  ingest: string;
  prefer_fp16: boolean;
  frigate_url: string;
  analyzers: Record<string, boolean>;
  retention_days: Record<string, number>;
  notifications: { enabled: boolean; webhook_url: string; notify_on: string; cooldown_s: number };
  llm: { enabled: boolean; base_url: string; model: string; has_key: boolean };
}
export interface SettingsUpdate {
  notify_webhook_url?: string;
  notify_on?: string;
  notify_cooldown_s?: number;
  retain_crops_days?: number;
  retain_embeddings_days?: number;
  retain_events_days?: number;
  llm_enabled?: boolean;
  llm_base_url?: string;
  llm_api_key?: string;
  llm_model?: string;
}
export interface Digest {
  text: string;
  source: "llm" | "deterministic";
  events_24h: number;
  generated_at: number;
}

export interface StatusInfo {
  device: string;
  ingest: string;
  uptime_s: number;
  vram_free_mb: number | null;
  cpu_percent: number | null;
  ram_percent: number | null;
  cameras: number;
  zones: number;
  persons: number;
  enrolled: number;
  events_24h: number;
  behaviors_24h: number;
}

export const api = {
  health: () => client.get<Health>("/health").then((r) => r.data),
  status: () => client.get<StatusInfo>("/status").then((r) => r.data),
  persons: () => client.get<Person[]>("/persons").then((r) => r.data),
  enroll: (id: string, name: string) => client.post(`/persons/${id}/enroll`, { name }).then((r) => r.data),
  mergePerson: (targetId: string, sourceId: string) =>
    client.post(`/persons/${targetId}/merge`, { source_id: sourceId }).then((r) => r.data),
  events: (limit = 100) => client.get<ArgosEvent[]>("/events", { params: { limit } }).then((r) => r.data),
  cameras: () => client.get<Camera[]>("/cameras").then((r) => r.data),
  addCamera: (name: string, url: string) => client.post<Camera>("/cameras", { name, url }).then((r) => r.data),
  removeCamera: (name: string) => client.delete(`/cameras/${name}`).then((r) => r.data),
  settings: () => client.get<SettingsSnapshot>("/settings").then((r) => r.data),
  updateSettings: (body: SettingsUpdate) => client.patch<SettingsSnapshot>("/settings", body).then((r) => r.data),
  scan: (body: { subnet?: string | null; sweep: boolean; audit_credentials: boolean }) =>
    client.post<DiscoveredCamera[]>("/discovery/scan", body).then((r) => r.data),
  notifyTest: () => client.post("/notify/test").then((r) => r.data),
  digest: () => client.get<Digest>("/digest").then((r) => r.data),
  person: (id: string) => client.get<PersonDetail>(`/persons/${id}`).then((r) => r.data),
  zones: (camera: string) => client.get<Zone[]>(`/cameras/${camera}/zones`).then((r) => r.data),
  addZone: (z: Omit<Zone, "id">) => client.post<Zone>("/zones", z).then((r) => r.data),
  removeZone: (id: string) => client.delete(`/zones/${id}`).then((r) => r.data),
};

export interface Zone {
  id: string;
  camera: string;
  name: string;
  kind: "alert" | "ignore";
  points: [number, number][];
}

export interface Observation {
  id: string;
  camera: string;
  ts: number;
}
export interface PersonDetail {
  person: Person;
  observations: Observation[];
  cameras: string[];
}

// Latest crop thumbnail for a person (<img>, so key goes in the query string).
export function personThumbUrl(id: string): string {
  return `/api/persons/${encodeURIComponent(id)}/thumbnail?key=${encodeURIComponent(getApiKey())}`;
}
export function observationThumbUrl(id: string): string {
  return `/api/observations/${encodeURIComponent(id)}/thumbnail?key=${encodeURIComponent(getApiKey())}`;
}

// <img>/EventSource can't set headers, so pass the key as a query param.
export function mjpegUrl(camera: string): string {
  return `/api/cameras/${encodeURIComponent(camera)}/stream.mjpeg?key=${encodeURIComponent(getApiKey())}`;
}
export function eventStreamUrl(): string {
  return `/api/events/stream?key=${encodeURIComponent(getApiKey())}`;
}
