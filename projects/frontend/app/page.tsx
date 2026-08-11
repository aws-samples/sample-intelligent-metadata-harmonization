/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Main page.

"use client";

import App from "../components/app";
import { AuthWrapper } from "../components/auth/auth-wrapper";

export default function Page() {
  return (
    <AuthWrapper>
      <App />
    </AuthWrapper>
  );
}
