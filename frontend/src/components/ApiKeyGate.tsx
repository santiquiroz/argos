import { KeyRound } from "lucide-react";
import { ReactNode, useState } from "react";
import { getApiKey, setApiKey } from "../lib/api";
import { Button } from "./ui/Button";

// Gate the app behind the API key (printed in the server console on start).
export function ApiKeyGate({ children }: { children: ReactNode }) {
  const [hasKey, setHasKey] = useState(Boolean(getApiKey()));
  const [value, setValue] = useState("");

  if (hasKey) return <>{children}</>;

  const submit = () => {
    if (!value.trim()) return;
    setApiKey(value.trim());
    setHasKey(true);
  };

  return (
    <div className="gate card stack">
      <div className="row">
        <KeyRound size={22} strokeWidth={1.5} />
        <h2 style={{ fontSize: 22 }}>Connect to Argos</h2>
      </div>
      <p className="muted">
        Enter the API key printed in the Argos server console on startup.
      </p>
      <div className="field">
        <label className="field__label" htmlFor="key">
          API key
        </label>
        <input
          id="key"
          className="input"
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="paste key…"
        />
      </div>
      <Button onClick={submit}>Connect</Button>
    </div>
  );
}
