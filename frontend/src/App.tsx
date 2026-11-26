
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

  risk_level: "low" | "medium" | "unassessed";
  risk_reason: string;
  review_recommendation: string;
};

type AuditEntry = {
  id: number;
  action_id: number;
  title: string;
  decision: "approved" | "rejected";
  decided_at: string;
};

type ExecutionEntry = {
  id: number;
  action_id: number;
  title: string;
  tool: string;
  target: string;
  status: "completed" | "failed";
  message: string;
  executed_at: string;
};

const API_URL = "http://127.0.0.1:8000";

async function fetchAuditLog(): Promise<AuditEntry[]> {
  const response = await fetch(`${API_URL}/audit-log`);

  if (!response.ok) {
    throw new Error("Could not load decision history");
  }

  return response.json();
}

async function fetchExecutionLog(): Promise<ExecutionEntry[]> {
  const response = await fetch(`${API_URL}/execution-log`);

  if (!response.ok) {
    throw new Error("Could not load execution history");
  }

  return response.json();
}



function App() {
  const [backendStatus, setBackendStatus] = useState<
    "checking" | "connected" | "disconnected"
  >("checking");

  const [actions, setActions] = useState<AgentAction[]>([]);
  const [userInstruction, setUserInstruction] = useState("");
  const [proposalLoading, setProposalLoading] = useState(false);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const [proposalMessage, setProposalMessage] = useState<string | null>(null);
  const [actionsLoading, setActionsLoading] = useState(true);
  const [actionsError, setActionsError] = useState<string | null>(null);
  const [actionToConfirm, setActionToConfirm] = useState<number | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(true);
  const [auditError, setAuditError] = useState<string | null>(null);

  const [executionLogs, setExecutionLogs] = useState<ExecutionEntry[]>([]);
  const [executionLoading, setExecutionLoading] = useState(true);
  const [executionError, setExecutionError] = useState<string | null>(null);

  // Check backend connection.
  useEffect(() => {
    fetch(`${API_URL}/health`)
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

  // Refresh actions from the backend.
  const refreshActions = async () => {
    const response = await fetch(`${API_URL}/actions`);

    if (!response.ok) {
      throw new Error("Could not load agent actions");
    }

    const data: AgentAction[] = await response.json();
    setActions(data);
  };

  // Refresh decision history.
  const refreshAuditLogs = async () => {
    const data = await fetchAuditLog();
    setAuditLogs(data);
    setAuditError(null);
  };

  // Refresh execution history.
  const refreshExecutionLogs = async () => {
    const data = await fetchExecutionLog();
    setExecutionLogs(data);
    setExecutionError(null);
  };


  // Send a user instruction to Gemini.
  const createProposal = async () => {
    if (!userInstruction.trim()) {
      return;
    }

    setProposalLoading(true);
setProposalError(null);
setProposalMessage(null);

    try {
      const response = await fetch(
        `${API_URL}/proposals`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            instruction: userInstruction,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not generate proposal"
        );
      }

      // Handle requests that need clarification.
if (data.status === "needs_clarification") {
  setProposalMessage(
    data.message || "Please provide more details about your request."
  );
  return;
}

// Handle proposals blocked by backend policies.
if (data.status === "policy_blocked") {
  setProposalMessage(
    "Policy blocked this proposal: " + data.message
  );
  return;
}

// Handle duplicate proposals.
if (data.status === "duplicate") {
  setProposalMessage(data.message);
  return;
}

      // Load the newly generated proposal into the approval queue.
      await refreshActions();

      setUserInstruction("");

      setProposalMessage(
  "AI proposal created! Please review it in the approval queue."
);

    } catch (error) {
      setProposalError(
        error instanceof Error
          ? error.message
          : "Something went wrong"
      );
    } finally {
      setProposalLoading(false);
    }
  };


  // Load all dashboard data.
  useEffect(() => {
    const loadDashboard = async () => {
      try {
        await refreshActions();
      } catch (error) {
        setActionsError(
          error instanceof Error
            ? error.message
            : "Could not load actions"
        );
      } finally {
        setActionsLoading(false);
      }

      try {
        await refreshAuditLogs();
      } catch (error) {
        setAuditError(
          error instanceof Error
            ? error.message
            : "Could not load decision history"
        );
      } finally {
        setAuditLoading(false);
      }

      try {
        await refreshExecutionLogs();
      } catch (error) {
        setExecutionError(
          error instanceof Error
            ? error.message
            : "Could not load execution history"
        );
      } finally {
        setExecutionLoading(false);
      }
    };

    loadDashboard();
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
        `${API_URL}/actions/${id}/decision`,
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

      await refreshAuditLogs();
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
    setActions((currentActions) =>
      currentActions.map((action) =>
        action.id === id
          ? { ...action, execution_status: "running" }
          : action
      )
    );

    try {
      const response = await fetch(
        `${API_URL}/actions/${id}/execute`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Execution failed");
      }

      setActions((currentActions) =>
        currentActions.map((action) =>
          action.id === id ? data.action : action
        )
      );

      await refreshExecutionLogs();

      alert("File operation completed successfully!");
    } catch (error) {
      // Reload the latest status, including failed executions.
      try {
        await refreshActions();
        await refreshExecutionLogs();
      } catch {
        // Preserve the original execution error.
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
          <a className="nav-item active" href="#">
            <span>▦</span> Overview
          </a>

          <a className="nav-item" href="#approval-queue">
            <span>◷</span> Approval Queue
            <span className="nav-count">{pendingCount}</span>
          </a>

          <a className="nav-item" href="#audit-history">
            <span>☷</span> Activity Logs
          </a>

          <a className="nav-item" href="#execution-history">
            <span>↗</span> Executions
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


  {/* AI instruction panel */}
  <section className="panel">
    <div className="panel-header">
      <div>
        <span className="eyebrow">AI ASSISTANT</span>
        <h2>Create an action with AI</h2>
        <p>
          Describe what you want the agent to do.
          Gemini will generate a proposal for your approval.
        </p>
      </div>
    </div>

    <form
      onSubmit={(event) => {
        event.preventDefault();
        void createProposal();
      }}
    >
      <textarea
        value={userInstruction}
        onChange={(event) =>
          setUserInstruction(event.target.value)
        }
        placeholder="Example: Copy the project plan into the archive folder."
        rows={4}
        maxLength={2000}
        disabled={proposalLoading}
        style={{
          width: "100%",
          padding: "14px",
          border: "1px solid #d1d5db",
          borderRadius: "8px",
          resize: "vertical",
          font: "inherit",
          boxSizing: "border-box",
          marginBottom: "12px",
        }}
      />

      {proposalError && (
        <p style={{ color: "red" }}>
          {proposalError}
        </p>
      )}

      {proposalMessage && (
  <p
    style={{
      padding: "12px",
      background: "#f3f4f6",
      borderRadius: "8px",
      color: "#374151",
    }}
  >
    {proposalMessage}
  </p>
)}

      <button
  type="submit"
  className="approve-button"
  disabled={proposalLoading || !userInstruction.trim()}
>
  {proposalLoading ? "Generating proposal..." : "Generate AI Proposal"}
</button>
    </form>
  </section>


          {/* Approval queue */}
          <section className="panel" id="approval-queue">
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


<div style={{ marginTop: "12px" }}>
  <div
    style={{
      display: "inline-block",
      padding: "5px 10px",
      borderRadius: "6px",
      fontSize: "12px",
      fontWeight: 700,
      background:
        action.risk_level === "low"
          ? "#dcfce7"
          : action.risk_level === "medium"
            ? "#fef3c7"
            : "#e5e7eb",
      color:
        action.risk_level === "low"
          ? "#166534"
          : action.risk_level === "medium"
            ? "#92400e"
            : "#374151",
    }}
  >
    RISK: {action.risk_level.toUpperCase()}
  </div>

  {action.risk_reason && (
    <p>{action.risk_reason}</p>
  )}

  {action.review_recommendation && (
    <p>
      <strong>Review recommendation:</strong>{" "}
      {action.review_recommendation}
    </p>
  )}
</div>

                    </div>

{actionToConfirm === action.id && (
  <div
    style={{
      width: "100%",
      padding: "16px",
      background: "#f3f4f6",
      border: "1px solid #d1d5db",
      borderRadius: "10px",
      marginBottom: "12px",
      boxSizing: "border-box",
    }}
  >
    <h3>Confirm file operation</h3>

    <p>
      <strong>Operation:</strong> {action.tool}
    </p>

    <p>
      <strong>Requested file change:</strong>
      <br />
      {action.target}
    </p>

    <p>
      This operation will modify files inside your
      dedicated test workspace. Do you want to continue?
    </p>

    <div
      style={{
        display: "flex",
        gap: "10px",
        flexWrap: "wrap",
      }}
    >
      <button
        type="button"
        className="reject-button"
        onClick={() => setActionToConfirm(null)}
      >
        Cancel
      </button>

      <button
        type="button"
        className="approve-button"
        onClick={() => {
          setActionToConfirm(null);
          void executeAction(action.id);
        }}
      >
        Confirm Execution
      </button>
    </div>
  </div>
)}


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
      type="button"
      className="approve-button"
      onClick={() => setActionToConfirm(action.id)}
    >
      Review & Execute
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
                    <p>No pending approvals remain in this demo.</p>
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
                          TIME: {new Date(entry.decided_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </section>

          {/* Execution history */}
          <section className="panel" id="execution-history">
            <div className="panel-header">
              <div>
                <span className="eyebrow">
                  EXECUTION MONITORING
                </span>
                <h2>Execution history</h2>
                <p>
                  Track file operations performed by the agent.
                </p>
              </div>

              <span className="queue-count">
                {executionLogs.length} execution records
              </span>
            </div>

            <div className="action-list">
              {executionLoading && (
                <p>Loading execution history...</p>
              )}

              {executionError && (
                <p style={{ color: "red" }}>{executionError}</p>
              )}

              {!executionLoading &&
                !executionError &&
                executionLogs.length === 0 && (
                  <div className="empty-state">
                    <span>↗</span>
                    <h3>No executions recorded yet</h3>
                    <p>
                      Executed file operations will appear here.
                    </p>
                  </div>
                )}

              {!executionLoading &&
                !executionError &&
                executionLogs.map((entry) => (
                  <div className="action-card" key={entry.id}>
                    <div className="action-icon">
                      {entry.status === "completed" ? "✓" : "×"}
                    </div>

                    <div className="action-details">
                      <div className="action-title-row">
                        <h3>{entry.title}</h3>
                        <span className={`badge ${entry.status}`}>
                          {entry.status}
                        </span>
                      </div>

                      <p>
                        Tool: {entry.tool} | Action ID: {entry.action_id}
                      </p>

                      <div className="action-metadata">
                        <span>TARGET: {entry.target}</span>
                        <span>
                          TIME: {new Date(entry.executed_at).toLocaleString()}
                        </span>
                      </div>

                      <p>{entry.message}</p>
                    </div>
                  </div>
                ))}
            </div>
          </section>

          <div className="notice">
            <span>ⓘ</span>
            <p>
              Demo mode: Approved actions can be executed inside the
              dedicated test workspace. Decisions and execution results
              are saved in SQLite. No personal files are modified.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
