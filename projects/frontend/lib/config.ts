/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Configuration.

export interface ConfigType {
  API_URI: string;
  COGNITO: {
    authority: string;
    client_id: string;
    redirect_uri: string;
    post_logout_redirect_uri: string;
    scope: string;
    response_type: string;
    loadUserInfo: boolean;
    metadata: {
      authorization_endpoint: string;
      token_endpoint: string;
      userinfo_endpoint: string;
      end_session_endpoint: string;
    };
  };
}

// Default config for build time
const defaultConfig: ConfigType = {
  API_URI: "",
  COGNITO: {
    authority: "",
    client_id: "",
    redirect_uri: "",
    post_logout_redirect_uri: "",
    scope: "openid",
    response_type: "code",
    loadUserInfo: true,
    metadata: {
      authorization_endpoint: "",
      token_endpoint: "",
      userinfo_endpoint: "",
      end_session_endpoint: "",
    },
  },
};

export const getConfig = (): ConfigType => {
  // During build/SSR, return empty config
  if (typeof window === "undefined") {
    return defaultConfig;
  }

  // In browser, return runtime config
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  if ((window as any).env) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (window as any).env;
  }

  // Fallback
  return defaultConfig;
};
