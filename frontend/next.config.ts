import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // 本番デプロイ用スタンドアロンビルド（EC2 での next start に使用）
  output: "standalone",
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
