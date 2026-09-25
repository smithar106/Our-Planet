import {
  defineRailway,
  github,
  postgres,
  preserve,
  project,
  service,
  volume,
} from "railway/iac";

export default defineRailway((ctx) => {
  const db = postgres("postgres");

  const mlflowData = volume("mlflow-data", {
    region: "us-west2",
    sizeMB: 2048,
  });

  const mlflow = service("mlflow", {
    source: github("smithar106/Our-Planet", { branch: "main", rootDirectory: "mlflow" }),
    start:
      "mlflow server --host 0.0.0.0 --port 5000 " +
      "--backend-store-uri sqlite:////data/mlflow.db " +
      "--default-artifact-root /data/artifacts",
    volumeMounts: { "/data": mlflowData },
    env: {
      PORT: "5000",
    },
  });

  const api = service("api", {
    source: github("smithar106/Our-Planet", { branch: "main", rootDirectory: "backend" }),
    build: "pip install -r requirements.txt",
    start: "python -m app.cli initdb && uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    healthcheck: "/api/health",
    env: {
      DATABASE_URL: db.env.DATABASE_URL,
      NASA_FIRMS_MAP_KEY: preserve(),
      LLM_PROVIDER: "deepseek",
      LLM_MODEL: "deepseek-chat",
      LLM_API_KEY: preserve(),
      LLM_BASE_URL: preserve(),
      AGENT_THRESHOLD: "50",
      TRACING_BACKEND: "memory",
      MLFLOW_TRACKING_URI: "http://mlflow.railway.internal:5000",
    },
  });

  const worker = service("worker", {
    source: github("smithar106/Our-Planet", { branch: "main", rootDirectory: "backend" }),
    build: "pip install -r requirements.txt",
    start: "python -m app.cli initdb && python -m app.cli worker",
    env: {
      DATABASE_URL: db.env.DATABASE_URL,
      NASA_FIRMS_MAP_KEY: preserve(),
      LLM_PROVIDER: "deepseek",
      LLM_MODEL: "deepseek-chat",
      LLM_API_KEY: preserve(),
      LLM_BASE_URL: preserve(),
      AGENT_THRESHOLD: "50",
      TRACING_BACKEND: "memory",
      MLFLOW_TRACKING_URI: "http://mlflow.railway.internal:5000",
    },
  });

  const web = service("web", {
    source: github("smithar106/Our-Planet", { branch: "main", rootDirectory: "frontend" }),
    build: "npm install && npm run build",
    start: "npm start",
    env: {
      NEXT_PUBLIC_API_URL: "https://api-production-3f28.up.railway.app",
      NEXT_PUBLIC_MAPBOX_TOKEN: preserve(),
    },
  });

  return project("planet", {
    resources: [db, mlflowData, mlflow, api, worker, web],
  });
});
