const fs = require("fs");
const path = require("path");
// load .env.production hoặc .env (tùy bạn)
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
      name: "notevideo-frontend",
      cwd: __dirname,
      script: "node_modules/next/dist/bin/next",
      args: "start -p " + (process.env.PORT || "3000"),
      interpreter: process.env.NODE_INTERPRETER || "node",
      env: {
        NODE_ENV: process.env.NODE_ENV || "production",
        PORT: process.env.PORT || "3000",
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
        NEXT_PUBLIC_USE_MOCK: process.env.NEXT_PUBLIC_USE_MOCK || "false",
      },
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_memory_restart: "512M",
    },
  ],
};