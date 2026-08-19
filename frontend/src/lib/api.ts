import axios from "axios";

// One axios instance; the API key is stored client-side and injected on every request.
// Pattern mirrors bipolar-code's services/api.ts.
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

export const api = {
  health: () => client.get<Health>("/health").then((r) => r.data),
  persons: () => client.get<Person[]>("/persons").then((r) => r.data),
  events: () => client.get<ArgosEvent[]>("/events").then((r) => r.data),
  enroll: (id: string, name: string) =>
    client.post(`/persons/${id}/enroll`, { name }).then((r) => r.data),
};
