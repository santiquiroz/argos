import { Aperture, Bell, LayoutDashboard, Radar, Settings, Users, Video } from "lucide-react";
import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/live", label: "Live", icon: Video },
  { to: "/discovery", label: "Discovery", icon: Radar },
  { to: "/persons", label: "Persons", icon: Users },
  { to: "/events", label: "Events", icon: Bell },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="sidebar__brand">
        <Aperture size={22} strokeWidth={1.5} />
        Argos
      </div>
      {LINKS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => `sidebar__link ${isActive ? "is-active" : ""}`}
        >
          <Icon size={18} strokeWidth={1.5} />
          {label}
        </NavLink>
      ))}
      <div className="sidebar__spacer" />
      <div className="sidebar__link" style={{ fontSize: 12, opacity: 0.6, cursor: "default" }}>
        Local · private · yours
      </div>
    </nav>
  );
}
