const fs = require("fs");
const path = require("path");
// Load backend/.env
const envPath = path.join(__dirname, ".env");
if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, "utf-8").split("\n");
  for (const line of lines) {
    const m = line.match(/^\s*([A-Za-z0-9_]+)\s*=\s*(.*)\s*$/);
    if (!m) continue;
    const key = m[1];
    let value = m[2];
    if (value.startsWith('"') && value.endsWith('"')) {
      value = value.slice(1, -1);
    }
    if (value.startsWith("'") && value.endsWith("'")) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}
module.exports = {
  apps: [
    {
      name: "notevideo-backend",
      cwd: __dirname,
      // Chạy uvicorn qua python, đọc host/port từ env
      script: "uvicorn",
      args:
        "main:app --host 0.0.0.0 --port " +
        (process.env.PORT || "8000") +
        " --workers 2",
      interpreter: process.env.PYTHON_INTERPRETER || "python",
      env: {
        // chuyển toàn bộ env backend vào process
        ...process.env,
      },
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_memory_restart: "512M",
    },
  ],
};