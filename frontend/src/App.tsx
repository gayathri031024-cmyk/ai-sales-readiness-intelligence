import { useEffect, useState } from "react"

type HealthResponse = {
  status: string
  app: string
  environment: string
  database: string
  database_error: string | null
}

/**
 * Phase 3 placeholder only — proves the frontend can reach the backend
 * and render its response. Real screens (Start Scenario / Conversation /
 * Result) are built in Phase 4 using the frontend-design skill.
 */
function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then(setHealth)
      .catch((err) => setError(String(err)))
  }, [])

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-900">
      <div className="max-w-md w-full mx-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold">AI Sales Readiness Intelligence</h1>
        <p className="mt-1 text-sm text-slate-500">Phase 3 — Project Foundation</p>

        <div className="mt-4 text-sm">
          {error && <p className="text-red-600">Could not reach backend: {error}</p>}
          {!error && !health && <p className="text-slate-500">Checking backend health…</p>}
          {health && (
            <dl className="grid grid-cols-2 gap-y-1">
              <dt className="text-slate-500">status</dt>
              <dd>{health.status}</dd>
              <dt className="text-slate-500">environment</dt>
              <dd>{health.environment}</dd>
              <dt className="text-slate-500">database</dt>
              <dd>{health.database}</dd>
            </dl>
          )}
        </div>
      </div>
    </main>
  )
}

export default App
