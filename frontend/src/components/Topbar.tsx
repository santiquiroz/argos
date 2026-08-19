import { useQuery } from "@tanstack/react-query";
import { Moon, Sun } from "lucide-react";
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../lib/api";
import { getTheme, toggleTheme } from "../lib/theme";
import { Dot } from "./ui/Feedback";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/live": "Live cameras",
  "/discovery": "Discovery",
  "/persons": "Persons",
  "/events": "Events",
  "/settings": "Settings",
};

export function Topbar() {
  const { pathname } = useLocation();
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });
  const [theme, setTheme] = useState(getTheme());

  const connected = health.isSuccess;

  return (
    <header className="topbar">
      <h1 className="topbar__title">{TITLES[pathname] ?? "Argos"}</h1>
      <div className="topbar__actions">
        <span className="badge" title={connected ? "connected" : "disconnected"}>
          <Dot variant={connected ? "live" : "danger"} />
          {connected ? `${health.data?.device} · ${health.data?.ingest}` : "offline"}
        </span>
        <button
          className="btn btn--secondary btn--sm"
          aria-label="Toggle theme"
          onClick={() => setTheme(toggleTheme())}
        >
          {theme === "dark" ? <Sun size={16} strokeWidth={1.5} /> : <Moon size={16} strokeWidth={1.5} />}
        </button>
      </div>
    </header>
  );
}
