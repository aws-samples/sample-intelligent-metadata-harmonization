/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Main layout.

"use client";

import "../styles/globals.css";
import { Inter } from "next/font/google";
import Script from "next/script";
import { AuthProvider } from "react-oidc-context";
import { ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";

import { getConfig } from "../lib/config";
import { theme } from "../lib/theme";

const inter = Inter({ subsets: ["latin"] });

// Metadata can't be used in client components, so we need to move it out
// You can create a separate file for metadata if needed
const metadata = {
  title: "Metadata Tool",
  description: "metadata validation system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const config = getConfig();

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>{metadata.title}</title>
        <meta name="description" content={metadata.description} />
      </head>
      <body className={inter.className}>
        <Script src="/env.js" strategy="beforeInteractive" />
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AuthProvider {...config.COGNITO}>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
