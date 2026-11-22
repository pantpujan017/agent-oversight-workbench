
import { useEffect, useState } from "react";
import "./App.css";

type AgentAction = {
  id: number;
  title: string;
  description: string;
  tool: string;
  target: string;
  status: "pending" | "approved" | "rejected";
};

function App() {
  const [backendStatus, setBackendStatus] = useState<
    "checking" | "connected" | "disconnected"
  >("checking");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend request failed");
        }
        return response.json();
      })
      .then((data: { status: string }) => {
        setBackendStatus(
          data.status === "healthy" ? "connected" : "disconnected"
        );
      })
      .catch(() => {
        setBackendStatus("disconnected");
      });
  }, []);

  const [actions, setActions] = useState<AgentAction[]>([
    {
      id: 1,
      title: "Copy project plan",
      description: "Agent wants to copy a project document.",
      tool: "copy_file",
      target: "project/plan.txt → review/plan.txt",
      status: "pending",
    },
    {
      id: 2,
      title: "Move meeting notes",
      description: "Agent wants to move a meeting document.",
      tool: "move_file",
      target: "project/meeting_notes.txt → archive/",
      status: "pending",
    },
    {
      id: 3,
      title: "Rename draft document",
      description: "Agent wants to rename a draft file.",
      tool: "rename_file",
      target: "draft.docx → final_draft.docx",
      status: "pending",
    },
  ]);

  const pendingCount = actions.filter(
    (action) => action.status === "pending"
  ).length;

  const approveAction = (id: number) => {
    setActions((previous) =>
      previous.map((action) =>
        action.id === id
          ? { ...action, status: "approved" }
          : action
      )
    );
  };

  const rejectAction = (id: number) => {
    setActions((previous) =>
      previous.map((action) =>
        action.id === id
          ? { ...action, status: "rejected" }
          : action
      )
    );
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">O</div>
          <div>
            <h2>Oversight</h2>
            <span>Agent Workbench</span>
          </div>
        </div>

        <div className="workspace-label">WORKSPACE</div>

        <nav className="navigation">
          <div className="nav-item active">
            <span>▦</span> Overview
          </div>
          <div className="nav-item">
            <span>◷</span> Approval Queue
            <span className="nav-count">{pendingCount}</span>
          </div>
          <div className="nav-item">
            <span>☷</span> Activity Logs
          </div>
          <div className="nav-item">
            <span>⬡</span> Policies
          </div>
          <div className="nav-item">
            <span>⚙</span> Settings
          </div>
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot"></span>
            System operational
          </div>
          <div className="profile">
            <div className="avatar">PP</div>
            <div>
              <strong>Workspace Owner</strong>
              <span>Administrator</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> Overview
          </div>
          <div className="topbar-right">
            <span className="environment-tag">LOCAL ENVIRONMENT</span>
            <div className="avatar small-avatar">PP</div>
          </div>
        </header>

        <section className="page-content">
          <div className="welcome-section">
            <div>
              <span className="eyebrow">AGENT MONITORING</span>
              <h1>Overview</h1>
              <p>
                Monitor agent activity, review proposed actions
                and stay in control of execution.
              </p>
            </div>
            <div className="connection-status">
  <span className={`status-dot ${backendStatus}`}></span>

  {backendStatus === "connected"
    ? "Backend connected"
    : backendStatus === "checking"
      ? "Checking backend..."
      : "Backend disconnected"}
</div>
          </div>

          <section className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">ACTIVE AGENTS</span>
              <strong>1</strong>
              <span className="stat-description">Demo agent</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">PENDING APPROVALS</span>
              <strong>{pendingCount}</strong>
              <span className="stat-description">
                Require your review
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-label">APPROVED ACTIONS</span>
              <strong>
                {actions.filter((a) => a.status === "approved").length}
              </strong>
              <span className="stat-description">
                Approved in this session
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-label">REJECTED ACTIONS</span>
              <strong>
                {actions.filter((a) => a.status === "rejected").length}
              </strong>
              <span className="stat-description">
                Blocked in this session
              </span>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">HUMAN OVERSIGHT</span>
                <h2>Action approval queue</h2>
                <p>Review each action before it can proceed.</p>
              </div>
              <span className="queue-count">
                {pendingCount} awaiting review
              </span>
            </div>

            <div className="action-list">
              {actions.map((action) => (
                <div className="action-card" key={action.id}>
                  <div className="action-icon">↗</div>

                  <div className="action-details">
                    <div className="action-title-row">
                      <h3>{action.title}</h3>
                      <span className={`badge ${action.status}`}>
                        {action.status}
                      </span>
                    </div>

                    <p>{action.description}</p>

                    <div className="action-metadata">
                      <span>TOOL: {action.tool}</span>
                      <span>TARGET: {action.target}</span>
                    </div>
                  </div>

                  {action.status === "pending" && (
                    <div className="action-buttons">
                      <button
                        className="reject-button"
                        onClick={() => rejectAction(action.id)}
                      >
                        Reject
                      </button>
                      <button
                        className="approve-button"
                        onClick={() => approveAction(action.id)}
                      >
                        Approve
                      </button>
                    </div>
                  )}
                </div>
              ))}

              {pendingCount === 0 && (
                <div className="empty-state">
                  <span>✓</span>
                  <h3>All actions reviewed</h3>
                  <p>No pending approvals remain in this demo.</p>
                </div>
              )}
            </div>
          </section>

          <div className="notice">
            <span>ⓘ</span>
            <p>
              Demo mode: Actions are sample proposals.
              Approval and rejection currently update only
              the frontend state. No real files are modified.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
