
import { useEffect, useState } from "react";
import "./App.css";

type AgentAction = {
  id: number;
  title: string;
  description: string;
  tool: string;
  target: string;
  status: "pending" | "approved" | "rejected";
  execution_status:
    | "not_started"
    | "running"
    | "completed"
    | "failed";
  execution_message: string;
};

type AuditEntry = {
  id: number;
  action_id: number;
  title: string;
  decision: "approved" | "rejected";
  decided_at: string;
};

async function fetchAuditLog(): Promise<AuditEntry[]> {
  const response = await fetch("http://127.0.0.1:8000/audit-log");

  if (!response.ok) {
    throw new Error("Could not load decision history");
  }

  return response.json();
}

function App() {
  const [backendStatus, setBackendStatus] = useState<
    "checking" | "connected" | "disconnected"
  >("checking");

  const [actions, setActions] = useState<AgentAction[]>([]);
  const [actionsLoading, setActionsLoading] = useState(true);
  const [actionsError, setActionsError] = useState<string | null>(null);

  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(true);
  const [auditError, setAuditError] = useState<string | null>(null);

  // Check backend connection.
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

  // Load actions from the backend.
  const refreshActions = async () => {
    const response = await fetch("http://127.0.0.1:8000/actions");

    if (!response.ok) {
      throw new Error("Could not load agent actions");
    }

    const data: AgentAction[] = await response.json();
    setActions(data);
  };

  useEffect(() => {
    const loadActions = async () => {
      try {
        await refreshActions();
      } catch (error) {
        setActionsError(
          error instanceof Error
            ? error.message
            : "Something went wrong"
        );
      } finally {
        setActionsLoading(false);
      }
    };

    loadActions();
  }, []);

  // Load audit history.
  useEffect(() => {
    const loadAuditLog = async () => {
      try {
        const data = await fetchAuditLog();
        setAuditLogs(data);
      } catch (error) {
        setAuditError(
          error instanceof Error
            ? error.message
            : "Could not load decision history"
        );
      } finally {
        setAuditLoading(false);
      }
    };

    loadAuditLog();
  }, []);

  const pendingCount = actions.filter(
    (action) => action.status === "pending"
  ).length;

  // Approve or reject an action.
  const decideAction = async (
    id: number,
    decision: "approved" | "rejected"
  ) => {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/actions/${id}/decision`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ decision }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Decision failed");
      }

      setActions((currentActions) =>
        currentActions.map((action) =>
          action.id === id ? data.action : action
        )
      );

      const updatedLogs = await fetchAuditLog();
      setAuditLogs(updatedLogs);
      setAuditError(null);
    } catch (error) {
      alert(
        error instanceof Error
          ? error.message
          : "Something went wrong"
      );
    }
  };

  const approveAction = (id: number) =>
    decideAction(id, "approved");

  const rejectAction = (id: number) =>
    decideAction(id, "rejected");

  // Execute an approved file operation.
  const executeAction = async (id: number) => {
    // Immediately show that execution has started.
    setActions((currentActions) =>
      currentActions.map((action) =>
        action.id === id
          ? { ...action, execution_status: "running" }
          : action
      )
    );

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/actions/${id}/execute`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Execution failed");
      }

      // Display the updated action returned by the backend.
      setActions((currentActions) =>
        currentActions.map((action) =>
          action.id === id ? data.action : action
        )
      );

      alert("File operation completed successfully!");
    } catch (error) {
      // Reload the action so a failed execution is displayed.
      try {
        await refreshActions();
      } catch {
        // Keep the original error message.
      }

      alert(
        error instanceof Error
          ? error.message
          : "Something went wrong"
      );
    }
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

          <a className="nav-item" href="#audit-history">
            <span>☷</span> Activity Logs
          </a>

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
            <span className="environment-tag">
              LOCAL ENVIRONMENT
            </span>
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

          {/* Dashboard statistics */}
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
                Saved in database
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-label">REJECTED ACTIONS</span>
              <strong>
                {actions.filter((a) => a.status === "rejected").length}
              </strong>
              <span className="stat-description">
                Saved in database
              </span>
            </div>
          </section>

          {/* Approval queue */}
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
              {actionsLoading && <p>Loading agent actions...</p>}

              {actionsError && (
                <p style={{ color: "red" }}>{actionsError}</p>
              )}

              {!actionsLoading &&
                !actionsError &&
                actions.map((action) => (
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

                      <div className="action-metadata">
                        <span>
                          EXECUTION:{" "}
                          {action.execution_status
                            .replace("_", " ")
                            .toUpperCase()}
                        </span>
                        {action.execution_message && (
                          <span>{action.execution_message}</span>
                        )}
                      </div>
                    </div>

                    <div className="action-buttons">
                      {action.status === "pending" && (
                        <>
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
                        </>
                      )}

                      {action.status === "approved" &&
                        action.execution_status === "not_started" && (
                          <button
                            className="approve-button"
                            onClick={() => executeAction(action.id)}
                          >
                            Execute
                          </button>
                        )}

                      {action.execution_status === "running" && (
                        <span>Executing...</span>
                      )}
                    </div>
                  </div>
                ))}

              {!actionsLoading &&
                !actionsError &&
                actions.length > 0 &&
                pendingCount === 0 && (
                  <div className="empty-state">
                    <span>✓</span>
                    <h3>All actions reviewed</h3>
                    <p>
                      No pending approvals remain in this demo.
                    </p>
                  </div>
                )}
            </div>
          </section>

          {/* Decision history */}
          <section className="panel" id="audit-history">
            <div className="panel-header">
              <div>
                <span className="eyebrow">
                  TRANSPARENCY & ACCOUNTABILITY
                </span>
                <h2>Decision history</h2>
                <p>
                  A record of actions that have been approved or rejected.
                </p>
              </div>

              <span className="queue-count">
                {auditLogs.length} recorded decisions
              </span>
            </div>

            <div className="action-list">
              {auditLoading && <p>Loading decision history...</p>}

              {auditError && (
                <p style={{ color: "red" }}>{auditError}</p>
              )}

              {!auditLoading &&
                !auditError &&
                auditLogs.length === 0 && (
                  <div className="empty-state">
                    <span>☷</span>
                    <h3>No decisions recorded yet</h3>
                    <p>
                      New approvals and rejections will appear here.
                    </p>
                  </div>
                )}

              {!auditLoading &&
                !auditError &&
                auditLogs.map((entry) => (
                  <div className="action-card" key={entry.id}>
                    <div className="action-icon">
                      {entry.decision === "approved" ? "✓" : "×"}
                    </div>

                    <div className="action-details">
                      <div className="action-title-row">
                        <h3>{entry.title}</h3>

                        <span className={`badge ${entry.decision}`}>
                          {entry.decision}
                        </span>
                      </div>

                      <p>Action ID: {entry.action_id}</p>

                      <div className="action-metadata">
                        <span>
                          DECISION: {entry.decision.toUpperCase()}
                        </span>
                        <span>
                          TIME:{" "}
                          {new Date(entry.decided_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </section>

          <div className="notice">
            <span>ⓘ</span>
            <p>
              Demo mode: Actions are sample proposals. Approved actions
              can be executed inside the dedicated test workspace.
              Decisions and execution results are saved in SQLite.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
