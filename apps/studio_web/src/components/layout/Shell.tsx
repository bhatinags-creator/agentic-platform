import type { ComponentType, PropsWithChildren } from "react";
import { Bot, FileText, Gauge, GitBranch, Library, PlayCircle, Settings, ShieldCheck, Wrench } from "lucide-react";
import { Button } from "../ui/Primitives";

export type StudioRoute = "agents" | "prompts" | "tools" | "tool-runner" | "workflow" | "knowledge" | "testing" | "governance" | "settings";

const routes: Array<{ id: StudioRoute; label: string; icon: ComponentType<{ size?: number }>; enabled: boolean }> = [
  { id: "agents", label: "Agent Studio", icon: Bot, enabled: true },
  { id: "prompts", label: "Prompt Studio", icon: FileText, enabled: true },
  { id: "tools", label: "Tool Studio", icon: Wrench, enabled: true },
  { id: "workflow", label: "Workflow Studio", icon: GitBranch, enabled: false },
  { id: "knowledge", label: "Knowledge Studio", icon: Library, enabled: false },
  { id: "testing", label: "Testing Studio", icon: Gauge, enabled: true },
  { id: "governance", label: "Governance", icon: ShieldCheck, enabled: false },
  { id: "settings", label: "Settings", icon: Settings, enabled: true }
];

export function Shell({ route, onRouteChange, onRefresh, children }: PropsWithChildren<{
  route: StudioRoute;
  onRouteChange: (route: StudioRoute) => void;
  onRefresh: () => void;
}>) {
  return (
    <div className="studio-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">N</div>
          <div>
            <div className="brand-title">Nexus Platform</div>
            <div className="brand-subtitle">Enterprise Agentic AI</div>
          </div>
        </div>
        <div>
          <div className="nav-section-title">Build</div>
          <nav className="nav-list">
            {routes.slice(0, 3).map((item) => <NavButton key={item.id} item={item} active={route === item.id} onRouteChange={onRouteChange} />)}
            {(route === "tools" || route === "tool-runner") && (
              <NavButton
                item={{ id: "tool-runner", label: "Tool Test Runner", icon: PlayCircle, enabled: true }}
                active={route === "tool-runner"}
                onRouteChange={onRouteChange}
                nested
              />
            )}
            {routes.slice(3, 6).map((item) => <NavButton key={item.id} item={item} active={route === item.id} onRouteChange={onRouteChange} />)}
          </nav>
          <div className="nav-section-title">Operate</div>
          <nav className="nav-list">
            {routes.slice(6).map((item) => <NavButton key={item.id} item={item} active={route === item.id} onRouteChange={onRouteChange} />)}
          </nav>
        </div>
        <div className="sidebar-footer">Phase 2 adds persisted Tool Studio registration and governed tool testing through the local control plane.</div>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <span className="env-pill"><span className="env-dot" /> Local Control Plane</span>
          <div className="topbar-spacer" />
          <Button onClick={onRefresh}>Refresh</Button>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}

function NavButton({ item, active, onRouteChange, nested = false }: { item: { id: StudioRoute; label: string; icon: ComponentType<{ size?: number }>; enabled: boolean }; active: boolean; onRouteChange: (route: StudioRoute) => void; nested?: boolean }) {
  const Icon = item.icon;
  return (
    <button disabled={!item.enabled} onClick={() => onRouteChange(item.id)} className={`nav-item ${nested ? "nav-item-nested" : ""} ${active ? "active" : ""} ${item.enabled ? "" : "disabled"}`}>
      <Icon size={16} />
      <span>{item.label}</span>
      {!item.enabled && <span className="nav-soon">Soon</span>}
    </button>
  );
}
