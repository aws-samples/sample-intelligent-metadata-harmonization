/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Auth-wrapper component.

"use client";

import { useAuth } from "react-oidc-context";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
  AlertTitle,
} from "@mui/material";
import { LocalHospital } from "@mui/icons-material";
import { commonStyles } from "../../lib/ui-helpers";

interface AuthWrapperProps {
  children: React.ReactNode;
}

export function AuthWrapper({ children }: AuthWrapperProps) {
  const auth = useAuth();

  if (auth.isLoading) {
    return (
      <Box
        sx={{
          ...commonStyles.centeredContainer,
          bgcolor: 'primary.main',
        }}
      >
        <Card sx={{ maxWidth: 400, width: '100%', mx: 2 }}>
          <CardContent sx={{ ...commonStyles.loadingContainer }}>
            <CircularProgress size={48} sx={{ mb: 3, color: 'primary.main' }} />
            <Typography variant="h6" component="h1" gutterBottom>
              Loading Application
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Please wait while we prepare the Metadata Tool...
            </Typography>
          </CardContent>
        </Card>
      </Box>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <Box
        sx={{
          ...commonStyles.centeredContainer,
          bgcolor: 'primary.main',
        }}
      >
        <Card sx={{ maxWidth: 400, width: '100%', mx: 2 }}>
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Box
                sx={{
                  bgcolor: 'primary.main',
                  p: 1,
                  borderRadius: 1,
                  mr: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <LocalHospital sx={{ color: 'white', fontSize: 32 }} />
              </Box>
              <Box>
                <Typography variant="h6" component="h1" fontWeight="bold">
                  Metadata Tool
                </Typography>
              </Box>
            </Box>

            <Alert severity="info" sx={{ mb: 3 }}>
              <AlertTitle>Authentication Required</AlertTitle>
              Please sign in to access the Metadata Tool.
            </Alert>

            <Button
              onClick={() => void auth.signinRedirect()}
              variant="contained"
              fullWidth
              size="large"
              sx={{ py: 1.5 }}
            >
              Sign In
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return <>{children}</>;
}
