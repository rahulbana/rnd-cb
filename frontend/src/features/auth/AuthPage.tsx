import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Input } from "../../components/ui";
import { useAuth } from "../../store/auth";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const navigate = useNavigate();
  const { login, register, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      navigate("/chat");
    } catch {
      /* error surfaced via store */
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-sm p-6">
        <h1 className="mb-1 text-xl font-semibold text-slate-800">
          {mode === "login" ? "Sign in" : "Create account"}
        </h1>
        <p className="mb-4 text-sm text-slate-500">Multi-Document RAG Platform</p>
        <form onSubmit={submit} className="space-y-3">
          <Input
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="password (min 8 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={busy}>
            {mode === "login" ? "Sign in" : "Register"}
          </Button>
        </form>
        <div className="mt-4 text-center text-sm text-slate-500">
          {mode === "login" ? (
            <a href="/register" className="text-brand-600 hover:underline">
              Need an account? Register
            </a>
          ) : (
            <a href="/login" className="text-brand-600 hover:underline">
              Have an account? Sign in
            </a>
          )}
        </div>
      </Card>
    </div>
  );
}
