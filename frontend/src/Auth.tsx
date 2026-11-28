
import { useState, type FormEvent } from "react";
import { supabase } from "./lib/supabaseClient";

type AuthProps = {
  onAuthenticated: () => void;
};

function Auth({ onAuthenticated }: AuthProps) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    setLoading(true);
    setError("");
    setMessage("");

    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            emailRedirectTo: window.location.origin,
          },
        });

        if (error) throw error;

        if (data.session) {
          onAuthenticated();
        } else {
          setMessage(
            "Account created! Please check your email and confirm your account before logging in."
          );
        }
      } else {
        const { data, error } =
          await supabase.auth.signInWithPassword({
            email: email.trim(),
            password,
          });

        if (error) throw error;

        if (data.session) {
          onAuthenticated();
        }
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Authentication failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode(mode === "login" ? "signup" : "login");
    setError("");
    setMessage("");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f4f6fa",
        padding: "24px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          background: "#ffffff",
          padding: "36px",
          borderRadius: "14px",
          boxShadow: "0 8px 30px rgba(0,0,0,0.06)",
          boxSizing: "border-box",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "30px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              background: "#111827",
              color: "#ffffff",
              borderRadius: "12px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "24px",
              fontWeight: 700,
            }}
          >
            O
          </div>

          <h1 style={{ marginBottom: "6px", color: "#111827" }}>
            Agent Oversight
          </h1>

          <p style={{ color: "#6b7280", fontSize: "14px" }}>
            Control and monitor your AI agents.
          </p>
        </div>

        <h2 style={{ color: "#111827" }}>
          {mode === "login" ? "Welcome back" : "Create your account"}
        </h2>

        <p style={{ color: "#6b7280", fontSize: "14px" }}>
          {mode === "login"
            ? "Sign in to access your workspace."
            : "Create an account to get started."}
        </p>

        <form onSubmit={handleSubmit}>
          <label
            htmlFor="auth-email"
            style={{ display: "block", marginBottom: "7px" }}
          >
            Email address
          </label>

          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
            style={{
              width: "100%",
              padding: "12px",
              border: "1px solid #d1d5db",
              borderRadius: "8px",
              marginBottom: "18px",
              boxSizing: "border-box",
            }}
          />

          <label
            htmlFor="auth-password"
            style={{ display: "block", marginBottom: "7px" }}
          >
            Password
          </label>

          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            minLength={8}
            required
            style={{
              width: "100%",
              padding: "12px",
              border: "1px solid #d1d5db",
              borderRadius: "8px",
              marginBottom: "18px",
              boxSizing: "border-box",
            }}
          />

          {error && (
            <p style={{ color: "#dc2626", fontSize: "13px" }}>
              {error}
            </p>
          )}

          {message && (
            <p
              style={{
                color: "#166534",
                background: "#dcfce7",
                padding: "12px",
                borderRadius: "8px",
                fontSize: "13px",
              }}
            >
              {message}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "13px",
              background: "#111827",
              color: "#ffffff",
              border: "none",
              borderRadius: "8px",
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
              marginTop: "8px",
            }}
          >
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "22px" }}>
          <span style={{ color: "#6b7280", fontSize: "14px" }}>
            {mode === "login"
              ? "Don't have an account?"
              : "Already have an account?"}
          </span>

          <button
            type="button"
            onClick={switchMode}
            style={{
              border: "none",
              background: "none",
              color: "#2563eb",
              fontWeight: 600,
              cursor: "pointer",
              marginLeft: "5px",
            }}
          >
            {mode === "login" ? "Create one" : "Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Auth;
