/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Box,
  Button,
  Chip,
  Tooltip,
  Stack
} from '@mui/material';
import {
  DriveFileRenameOutline,
  Add,
  Remove,
  ArrowForward,
  Check,
  Undo,
  Transform,
  InfoOutlined
} from '@mui/icons-material';
import { SchemaAlignmentChangeDetail } from '../../lib/types';

interface SchemaChangeCardProps {
  /** The schema change to display */
  change: SchemaAlignmentChangeDetail;
  /** Index of the change in the list */
  index: number;
  /** Whether this change has been applied */
  isApplied: boolean;
  /** Callback when user applies this change */
  onApplyChange: (change: SchemaAlignmentChangeDetail, index: number) => void;
  /** Callback when user reverts this change */
  onRevertChange: (change: SchemaAlignmentChangeDetail, index: number) => void;
  /** Function to get change ID for this change */
  getChangeId?: (change: SchemaAlignmentChangeDetail, index: number) => string;
}

/**
 * SchemaChangeCard component displays a single schema alignment change
 * with options for applying or reverting the change.
 */
export const SchemaChangeCard: React.FC<SchemaChangeCardProps> = ({
  change,
  index,
  isApplied,
  onApplyChange,
  onRevertChange
}) => {
  const changeType = change.changeType.toLowerCase();

  /**
   * Get the appropriate icon for a change type
   */
  const getChangeIcon = (changeType: string) => {
    switch (changeType.toLowerCase()) {
      case 'rename':
        return <DriveFileRenameOutline color="info" />;
      case 'add':
        return <Add color="success" />;
      case 'remove':
        return <Remove color="warning" />;
      default:
        return <Transform color="action" />;
    }
  };

  /**
   * Get a human-readable label for the change type
   */
  const getChangeTypeLabel = (changeType: string): string => {
    switch (changeType.toLowerCase()) {
      case 'rename':
        return 'Rename';
      case 'add':
        return 'Add';
      case 'remove':
        return 'Remove';
      default:
        return changeType;
    }
  };

  /**
   * Get confidence color consistent with error cards
   */
  const getConfidenceColor = (level: string): string => {
    switch (level) {
      case 'High': return '#4caf50';  // Green
      case 'Medium': return '#ff9800'; // Orange
      case 'Low': return '#f44336';   // Red
      default: return '#757575';      // Gray
    }
  };

  /**
   * Get confidence level display text
   */
  const getConfidenceLevel = (change: SchemaAlignmentChangeDetail): string => {
    // First check if confidenceLevel is directly set
    const level = change.confidenceLevel;
    if (level && ['High', 'Medium', 'Low'].includes(level)) {
      return level;
    }

    // Try to extract confidence from structured reason string
    const parsedReason = parseEnhancedReason(change.reason);
    if (parsedReason?.confidence && ['High', 'Medium', 'Low'].includes(parsedReason.confidence)) {
      return parsedReason.confidence;
    }

    // Map confidence score to level if confidenceLevel is not set
    const score = change.confidenceScore || 0;
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    if (score > 0) return 'Low';
    return 'Unknown';
  };

  /**
   * Get confidence tooltip text with reasoning
   */
  const getConfidenceTooltip = (change: SchemaAlignmentChangeDetail): string => {
    // Extract only the reasoning part from structured reason string
    const parsedReason = parseEnhancedReason(change.reason);
    const reasoning = parsedReason?.reasoning || change.reason || 'No reasoning provided';

    return `Reasoning: ${reasoning}`;
  };

  /**
   * Parse enhanced reasoning to extract structured information
   */
  const parseEnhancedReason = (reason: string | undefined) => {
    if (!reason) return null;

    // Try to parse Target/Match/Confidence/Reasoning format
    const targetMatch = reason.match(/Target:\s*([^|]+)/);
    const matchMatch = reason.match(/Match:\s*([^|]+)/);
    const confidenceMatch = reason.match(/Confidence:\s*([^|]+)/);
    const reasoningMatch = reason.match(/Reasoning:\s*(.+)$/);

    if (targetMatch || matchMatch || confidenceMatch || reasoningMatch) {
      return {
        target: targetMatch?.[1]?.trim(),
        match: matchMatch?.[1]?.trim(),
        confidence: confidenceMatch?.[1]?.trim(),
        reasoning: reasoningMatch?.[1]?.trim()
      };
    }

    return null;
  };

  return (
    <Card
      variant="outlined"
      sx={{
        position: 'relative',
        // Enhanced blue theme styling to match application's blue theme
        border: 2,
        borderColor: isApplied ? 'success.main' : 'primary.main',
        backgroundColor: isApplied ? 'success.50' : 'background.paper',
        borderLeftWidth: 4,
        borderLeftColor: isApplied ? 'success.main' : 'primary.main',
        '&:hover': {
          borderColor: isApplied ? 'success.dark' : 'primary.dark',
          boxShadow: 2,
          borderLeftColor: isApplied ? 'success.dark' : 'primary.dark'
        }
      }}
    >
      <CardContent sx={{ pb: 2 }}>
        {/* Vertical layout to prevent text overflow for long column names */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>

          {/* Header with operation type and confidence */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {getChangeIcon(change.changeType)}
              <Typography variant="subtitle2" color="primary.main" sx={{ fontWeight: 600 }}>
                {getChangeTypeLabel(change.changeType)}
              </Typography>
            </Box>

            {/* Confidence indicator consistent with error cards */}
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
              <Tooltip title={getConfidenceTooltip(change)} arrow>
                <Chip
                  label={getConfidenceLevel(change)}
                  size="small"
                  icon={<InfoOutlined sx={{ fontSize: '0.75rem !important' }} />}
                  sx={{
                    fontSize: '0.75rem',
                    height: 24,
                    backgroundColor: getConfidenceColor(getConfidenceLevel(change)),
                    color: 'white',
                    fontWeight: 'bold',
                    '& .MuiChip-icon': {
                      color: 'white',
                      fontSize: '0.75rem'
                    }
                  }}
                />
              </Tooltip>

              <Chip
                label={isApplied ? 'Applied' : 'Pending'}
                size="small"
                color={isApplied ? 'success' : 'primary'}
                variant={isApplied ? 'filled' : 'outlined'}
                sx={{ fontWeight: 'bold' }}
              />
            </Box>
          </Box>

          {/* Column information display - vertical layout for long names */}
          {changeType === 'rename' && change.originalColumn && change.newColumn && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, ml: 1 }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  <Chip
                    label={change.originalColumn}
                    size="small"
                    variant="outlined"
                    sx={{
                      fontFamily: 'monospace',
                      backgroundColor: 'grey.100',
                      borderColor: 'grey.400',
                      alignSelf: 'flex-start',
                      maxWidth: '100%',
                      '& .MuiChip-label': {
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: '300px'
                      }
                    }}
                  />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main' }}>
                  <ArrowForward fontSize="small" />
                  <Typography variant="caption" sx={{ fontWeight: 600 }}>
                    RENAME TO
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  <Chip
                    label={change.newColumn}
                    size="small"
                    color="primary"
                    sx={{
                      fontFamily: 'monospace',
                      fontWeight: 'bold',
                      alignSelf: 'flex-start',
                      maxWidth: '100%',
                      '& .MuiChip-label': {
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: '300px'
                      }
                    }}
                  />
                </Box>
              </Box>
            </Box>
          )}

          {changeType === 'add' && change.newColumn && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ ml: 1 }}>
                <Chip
                  label={change.newColumn}
                  size="small"
                  color="success"
                  icon={<Add />}
                  sx={{
                    fontFamily: 'monospace',
                    fontWeight: 'bold',
                    maxWidth: '100%',
                    '& .MuiChip-label': {
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '300px'
                    }
                  }}
                />
              </Box>
            </Box>
          )}

          {changeType === 'remove' && change.originalColumn && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ ml: 1 }}>
                <Chip
                  label={change.originalColumn}
                  size="small"
                  color="warning"
                  icon={<Remove />}
                  sx={{
                    fontFamily: 'monospace',
                    fontWeight: 'bold',
                    maxWidth: '100%',
                    '& .MuiChip-label': {
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '300px'
                    }
                  }}
                />
              </Box>
            </Box>
          )}

        </Box>
      </CardContent>

      <CardActions sx={{
        pt: 1,
        justifyContent: 'space-between',
        backgroundColor: 'rgba(255,255,255,0.8)',
        borderTop: '1px solid',
        borderColor: 'divider'
      }}>
        <Box>
          {!isApplied ? (
            <Stack direction="row" spacing={1}>
              {/* Manual trigger buttons with enhanced styling */}
              {changeType === 'rename' && (
                <Button
                  size="small"
                  variant="contained"
                  color="primary"
                  startIcon={<DriveFileRenameOutline />}
                  onClick={() => onApplyChange(change, index)}
                  sx={{
                    textTransform: 'none',
                    fontWeight: 'bold',
                    minWidth: 120,
                    '&:hover': {
                      transform: 'translateY(-1px)',
                      boxShadow: 2
                    }
                  }}
                >
                  Apply Rename
                </Button>
              )}
              {changeType === 'add' && (
                <Button
                  size="small"
                  variant="contained"
                  color="success"
                  startIcon={<Add />}
                  onClick={() => onApplyChange(change, index)}
                  sx={{
                    textTransform: 'none',
                    fontWeight: 'bold',
                    minWidth: 120,
                    '&:hover': {
                      transform: 'translateY(-1px)',
                      boxShadow: 2
                    }
                  }}
                >
                  Apply Addition
                </Button>
              )}
              {changeType === 'remove' && (
                <Button
                  size="small"
                  variant="contained"
                  color="warning"
                  startIcon={<Remove />}
                  onClick={() => onApplyChange(change, index)}
                  sx={{
                    textTransform: 'none',
                    fontWeight: 'bold',
                    minWidth: 120,
                    '&:hover': {
                      transform: 'translateY(-1px)',
                      boxShadow: 2
                    }
                  }}
                >
                  Apply Removal
                </Button>
              )}
            </Stack>
          ) : (
            <Stack direction="row" spacing={1}>
              <Button
                size="small"
                variant="outlined"
                color="secondary"
                startIcon={<Undo />}
                onClick={() => onRevertChange(change, index)}
                sx={{
                  textTransform: 'none',
                  fontWeight: 'bold',
                  '&:hover': {
                    transform: 'translateY(-1px)',
                    boxShadow: 1
                  }
                }}
              >
                Revert
              </Button>
            </Stack>
          )}
        </Box>

          {/* Row Count Affected */}
          {change.rowCountAffected !== undefined && change.rowCountAffected !== null && (
            <Typography variant="caption" color="text.secondary" sx={{
              fontStyle: 'italic',
              backgroundColor: 'grey.50',
              padding: '4px 8px',
              borderRadius: 1,
              alignSelf: 'flex-start',
              border: '1px solid',
              borderColor: 'grey.200'
            }}>
              Affects {change.rowCountAffected} rows
            </Typography>
          )}
      </CardActions>
    </Card>
  );
};
