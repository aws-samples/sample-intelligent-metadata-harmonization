/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  Chip,
  Skeleton,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  Edit as EditIcon,
  Computer as SystemIcon,
  Person as UserIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import { ChangesSummaryCardProps } from '../../lib/types';

/**
 * Summary card component displaying high-level change statistics
 * Shows total changes, breakdown by type, and source attribution
 */
export const ChangesSummaryCard: React.FC<ChangesSummaryCardProps> = ({
  summary,
  loading = false,
  title = "Changes Summary",
  onClick
}) => {
  // Loading state
  if (loading) {
    return (
      <Card
        variant="outlined"
        sx={{
          mb: 2,
          border: 2,
          borderColor: 'primary.main',
          backgroundColor: 'background.paper'
        }}
      >
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Skeleton variant="circular" width={24} height={24} sx={{ mr: 1 }} />
            <Skeleton variant="text" width={150} height={28} />
          </Box>
          <Grid container spacing={2}>
            {[1, 2, 3, 4].map((item) => (
              <Grid item xs={6} sm={3} key={item}>
                <Skeleton variant="rectangular" height={60} />
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    );
  }

  // No changes state
  if (summary.totalChanges === 0) {
    return (
      <Card
        variant="outlined"
        sx={{
          mb: 2,
          border: 2,
          borderColor: 'success.main',
          backgroundColor: 'success.50',
          cursor: onClick ? 'pointer' : 'default'
        }}
        onClick={onClick}
      >
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <TrendingUpIcon color="success" sx={{ mr: 1 }} />
              <Typography variant="h6" color="success.main" sx={{ fontWeight: 600 }}>
                No Changes Detected
              </Typography>
            </Box>
            {onClick && (
              <IconButton size="small" color="success">
                <ExpandMoreIcon />
              </IconButton>
            )}
          </Box>
          <Typography variant="body2" color="success.dark" sx={{ mt: 1 }}>
            Your data remained unchanged during processing.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  // Get color based on total changes
  const getCardColor = () => {
    if (summary.totalChanges === 0) return 'success';
    if (summary.totalChanges <= 5) return 'info';
    if (summary.totalChanges <= 20) return 'warning';
    return 'error';
  };

  const cardColor = getCardColor();

  return (
    <Card
      variant="outlined"
      sx={{
        mb: 2,
        border: 2,
        borderColor: `${cardColor}.main`,
        backgroundColor: 'background.paper',
        borderLeftWidth: 4,
        borderLeftColor: `${cardColor}.main`,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease-in-out',
        '&:hover': onClick ? {
          borderColor: `${cardColor}.dark`,
          boxShadow: 2,
          borderLeftColor: `${cardColor}.dark`,
          transform: 'translateY(-1px)'
        } : {}
      }}
      onClick={onClick}
    >
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TrendingUpIcon color={cardColor} sx={{ mr: 1 }} />
            <Typography variant="h6" color={`${cardColor}.main`} sx={{ fontWeight: 600 }}>
              {title}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label={`${summary.totalChanges} Total`}
              color={cardColor}
              sx={{
                fontWeight: 'bold',
                fontSize: '0.875rem'
              }}
            />
            {onClick && (
              <IconButton size="small" color={cardColor}>
                <ExpandMoreIcon />
              </IconButton>
            )}
          </Box>
        </Box>

        {/* Statistics Grid */}
        <Grid container spacing={2}>
          {/* Change Types */}
          <Grid item xs={12} sm={6}>
            <Box sx={{
              p: 2,
              backgroundColor: 'grey.50',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'grey.200'
            }}>
              <Typography variant="subtitle2" color="text.secondary" sx={{
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: 0.5,
                mb: 1.5
              }}>
                Change Types
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {/* Additions */}
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AddIcon sx={{ fontSize: 16, color: '#4caf50' }} />
                    <Typography variant="body2" color="text.primary">
                      Added
                    </Typography>
                  </Box>
                  <Chip
                    label={summary.adds}
                    size="small"
                    sx={{
                      backgroundColor: '#e8f5e8',
                      color: '#4caf50',
                      fontWeight: 'bold',
                      minWidth: 32
                    }}
                  />
                </Box>

                {/* Removals */}
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <RemoveIcon sx={{ fontSize: 16, color: '#f44336' }} />
                    <Typography variant="body2" color="text.primary">
                      Removed
                    </Typography>
                  </Box>
                  <Chip
                    label={summary.removes}
                    size="small"
                    sx={{
                      backgroundColor: '#ffeaea',
                      color: '#f44336',
                      fontWeight: 'bold',
                      minWidth: 32
                    }}
                  />
                </Box>

                {/* Modifications */}
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <EditIcon sx={{ fontSize: 16, color: '#ff9800' }} />
                    <Typography variant="body2" color="text.primary">
                      Modified
                    </Typography>
                  </Box>
                  <Chip
                    label={summary.renames}
                    size="small"
                    sx={{
                      backgroundColor: '#fff3e0',
                      color: '#ff9800',
                      fontWeight: 'bold',
                      minWidth: 32
                    }}
                  />
                </Box>
              </Box>
            </Box>
          </Grid>

          {/* Change Sources */}
          <Grid item xs={12} sm={6}>
            <Box sx={{
              p: 2,
              backgroundColor: 'grey.50',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'grey.200'
            }}>
              <Typography variant="subtitle2" color="text.secondary" sx={{
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: 0.5,
                mb: 1.5
              }}>
                Change Sources
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {/* System Changes */}
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SystemIcon sx={{ fontSize: 16, color: '#2196f3' }} />
                    <Typography variant="body2" color="text.primary">
                      System
                    </Typography>
                  </Box>
                  <Tooltip title="Changes recommended by the system" arrow>
                    <Chip
                      label={summary.systemChanges}
                      size="small"
                      sx={{
                        backgroundColor: '#e3f2fd',
                        color: '#2196f3',
                        fontWeight: 'bold',
                        minWidth: 32,
                        cursor: 'help'
                      }}
                    />
                  </Tooltip>
                </Box>

                {/* User Changes */}
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <UserIcon sx={{ fontSize: 16, color: '#9c27b0' }} />
                    <Typography variant="body2" color="text.primary">
                      User
                    </Typography>
                  </Box>
                  <Tooltip title="Changes made by user input" arrow>
                    <Chip
                      label={summary.userChanges}
                      size="small"
                      sx={{
                        backgroundColor: '#f3e5f5',
                        color: '#9c27b0',
                        fontWeight: 'bold',
                        minWidth: 32,
                        cursor: 'help'
                      }}
                    />
                  </Tooltip>
                </Box>

                {/* Percentage breakdown */}
                {summary.totalChanges > 0 && (
                  <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid', borderColor: 'grey.300' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                      {Math.round((summary.systemChanges / summary.totalChanges) * 100)}% system, {' '}
                      {Math.round((summary.userChanges / summary.totalChanges) * 100)}% user
                    </Typography>
                  </Box>
                )}
              </Box>
            </Box>
          </Grid>
        </Grid>

        {/* Footer message */}
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            {onClick ? 'Click to view detailed changes' : 'Changes detected during processing'}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};
