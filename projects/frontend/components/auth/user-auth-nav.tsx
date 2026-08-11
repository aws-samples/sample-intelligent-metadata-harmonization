/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// User auth navigation component.

"use client";

import { useAuth } from "react-oidc-context";
import {
  Avatar,
  Button,
  Box,
  Typography,
  useTheme,
  useMediaQuery
} from "@mui/material";
import { Logout } from "@mui/icons-material";
import { getUserInitials } from "../../lib/utils";

export function UserAuthNav() {
  const auth = useAuth();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  if (!auth.isAuthenticated || !auth.user) {
    return null;
  }

  const userEmail = auth.user.profile.email;
  const userInitials = getUserInitials(userEmail || "");

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 2
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1
        }}
      >
        <Avatar
          sx={{
            width: 32,
            height: 32,
            bgcolor: 'primary.main',
            fontSize: '0.875rem',
            fontWeight: 600
          }}
        >
          {userInitials}
        </Avatar>
        {!isMobile && (
          <Typography
            variant="body2"
            sx={{
              color: 'inherit',
              fontWeight: 500
            }}
          >
            {userEmail}
          </Typography>
        )}
      </Box>
      <Button
        onClick={() => void auth.removeUser()}
        variant="outlined"
        size="small"
        startIcon={<Logout />}
        sx={{
          color: 'inherit',
          borderColor: 'rgba(255, 255, 255, 0.5)',
          '&:hover': {
            borderColor: 'rgba(255, 255, 255, 0.8)',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
          },
        }}
      >
        Sign Out
      </Button>
    </Box>
  );
}
