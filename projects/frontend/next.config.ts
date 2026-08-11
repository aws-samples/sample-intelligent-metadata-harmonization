/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export", // Enable static export
  images: {
    unoptimized: true, // Required for static export
  },
  reactStrictMode: true,
  // Disable directory listing
  trailingSlash: false,
};

export default nextConfig;
