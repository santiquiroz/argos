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
  notifications: { enabled: boolean; notify_on: string; cooldown_s: number };
}

export const api = {
  health: () => client.get<Health>("/health").then((r) => r.data),
  persons: () => client.get<Person[]>("/persons").then((r) => r.data),
  enroll: (id: string, name: string) => client.post(`/persons/${id}/enroll`, { name }).then((r) => r.data),
  events: (limit = 100) => client.get<ArgosEvent[]>("/events", { params: { limit } }).then((r) => r.data),
  cameras: () => client.get<Camera[]>("/cameras").then((r) => r.data),
  addCamera: (name: string, url: string) => client.post<Camera>("/cameras", { name, url }).then((r) => r.data),
  removeCamera: (name: string) => client.delete(`/cameras/${name}`).then((r) => r.data),
  settings: () => client.get<SettingsSnapshot>("/settings").then((r) => r.data),
  scan: (body: { subnet?: string | null; sweep: boolean; audit_credentials: boolean }) =>
    client.post<DiscoveredCamera[]>("/discovery/scan", body).then((r) => r.data),
  notifyTest: () => client.post("/notify/test").then((r) => r.data),
};

// Latest crop thumbnail for a person (<img>, so key goes in the query string).
export function personThumbUrl(id: string): string {
  return `/api/persons/${encodeURIComponent(id)}/thumbnail?key=${encodeURIComponent(getApiKey())}`;
}

// <img>/EventSource can't set headers, so pass the key as a query param.
export function mjpegUrl(camera: string): string {
  return `/api/cameras/${encodeURIComponent(camera)}/stream.mjpeg?key=${encodeURIComponent(getApiKey())}`;
}
export function eventStreamUrl(): string {
  return `/api/events/stream?key=${encodeURIComponent(getApiKey())}`;
}
