// k6 load test for the RAG platform.
//
//   BASE_URL=https://api.example.com \
//   EMAIL=loadtester@example.com PASSWORD=... \
//   k6 run infra/loadtest/k6-rag.js
//
// Stages ramp to a sustained load and assert p95 latency + error-rate SLOs via
// thresholds (a threshold breach exits non-zero, so this doubles as a CI/CD
// performance gate against a staging deploy).
import http from "k6/http";
import { check, sleep, group } from "k6";
import { Trend, Rate } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";
const EMAIL = __ENV.EMAIL || "loadtester@example.com";
const PASSWORD = __ENV.PASSWORD || "password123";

const chatLatency = new Trend("chat_latency_ms", true);
const chatErrors = new Rate("chat_errors");

export const options = {
  scenarios: {
    ramp: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 10 }, // warm up
        { duration: "1m", target: 25 }, // ramp
        { duration: "2m", target: 25 }, // sustain
        { duration: "30s", target: 0 }, // ramp down
      ],
      gracefulRampDown: "20s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"], // < 1% errors
    "chat_latency_ms": ["p(95)<8000"], // p95 chat under 8s (RAG + LLM)
    "http_req_duration{endpoint:retrieve}": ["p(95)<1500"],
    "http_req_duration{endpoint:health}": ["p(95)<300"],
  },
};

function authToken() {
  http.post(
    `${BASE_URL}/api/v1/auth/register`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  const res = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  return res.json("access_token");
}

export function setup() {
  return { token: authToken() };
}

export default function (data) {
  const authHeaders = {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${data.token}`,
    },
  };

  group("health", () => {
    const res = http.get(`${BASE_URL}/api/v1/health`, { tags: { endpoint: "health" } });
    check(res, { "health 200": (r) => r.status === 200 });
  });

  group("retrieve", () => {
    const res = http.post(
      `${BASE_URL}/api/v1/retrieve`,
      JSON.stringify({ query: "What is the refund policy?", top_k: 5 }),
      { ...authHeaders, tags: { endpoint: "retrieve" } },
    );
    check(res, { "retrieve ok": (r) => r.status === 200 || r.status === 404 });
  });

  group("chat", () => {
    const start = Date.now();
    const res = http.post(
      `${BASE_URL}/api/v1/chat`,
      JSON.stringify({ message: "Summarize the onboarding guide." }),
      { ...authHeaders, tags: { endpoint: "chat" } },
    );
    chatLatency.add(Date.now() - start);
    const ok = res.status === 200;
    chatErrors.add(!ok);
    check(res, { "chat ok": () => ok });
  });

  sleep(1);
}
