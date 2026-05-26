// PM2 ecosystem config - Alternative to Docker
// Use when Docker is not preferred on OCI Always Free
module.exports = {
  apps: [
    {
      name: "command-os-backend",
      script: "uvicorn",
      args: "server:app --host 0.0.0.0 --port 8001",
      cwd: "./backend",
      interpreter: "python3",
      env: {
        PYTHONUNBUFFERED: "1",
        SYSTEM_MODE: "production",
        COST_GUARD_ENABLED: "true",
        ZERO_SPEND_MODE: "true",
      },
      max_memory_restart: "500M",
      error_file: "./logs/backend-error.log",
      out_file: "./logs/backend-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
    },
    {
      name: "command-os-frontend",
      script: "yarn",
      args: "start",
      cwd: "./frontend",
      env: {
        BROWSER: "none",
        PORT: "3000",
      },
      max_memory_restart: "1G",
      error_file: "./logs/frontend-error.log",
      out_file: "./logs/frontend-out.log",
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
    },
  ],
};
