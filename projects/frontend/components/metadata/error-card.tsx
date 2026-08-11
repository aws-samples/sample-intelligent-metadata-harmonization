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
  IconButton,
  Chip,
  Tooltip,
  Stack
} from '@mui/material';
import { Check, CheckCircle, Close, InfoOutlined, Error } from '@mui/icons-material';
import { ValidationError } from '../../lib/types';

interface ErrorCardProps {
  error: ValidationError;
  onAccept: () => void;
  onAcceptAll: () => void;
  onDismiss: () => void;
}

export const ErrorCardComponent: React.FC<ErrorCardProps> = ({
  error,
  onAccept,
  onAcceptAll,
  onDismiss
}) => {

  const formatErrorType = (errorType: string): string => {
    return errorType
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  const getLocationText = (): string => {
    return `Row ${error.row}, Column ${error.column}`;
  };

  const getConfidenceColor = (level: string): string => {
    switch (level) {
      case 'High': return '#4caf50';  // Green
      case 'Medium': return '#ff9800'; // Orange
      case 'Low': return '#f44336';   // Red
      default: return '#757575';      // Gray
    }
  };

  const getConfidenceTooltip = (): string => {
    const errorMessage = error.errorMessage || 'No Error message';
    return `Error: ${errorMessage}`;
  };

  return (
    <Card
      variant="outlined"
      sx={{
        position: 'relative',
        mb: 2, // Add spacing between error cards
        // Enhanced styling to match schema-changes panel
        border: 2,
        borderColor: 'error.main',
        backgroundColor: 'background.paper',
        borderLeftWidth: 4,
        borderLeftColor: 'error.main',
        '&:hover': {
          borderColor: 'error.dark',
          boxShadow: 2,
          borderLeftColor: 'error.dark'
        }
      }}
    >
      <CardContent sx={{ pb: 2 }}>
        {/* Vertical layout to match schema-changes panel */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>

          {/* Header with error type and confidence - matching schema-changes layout */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Error color="error" />
              <Tooltip title={error.errorMessage || 'No error details available'} arrow>
                <Typography variant="subtitle2" color="error.main" sx={{
                  fontWeight: 600,
                  cursor: 'help',
                  '&:hover': {
                    textDecoration: 'underline'
                  }
                }}>
                  {formatErrorType(error.errorType)}
                </Typography>
              </Tooltip>
            </Box>

            {/* Confidence and location indicators */}
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
              <Chip
                label={getLocationText()}
                size="small"
                sx={{
                  fontSize: '0.75rem',
                  height: 24,
                  backgroundColor: 'primary.main',
                  color: 'primary.contrastText',
                  fontWeight: 'bold'
                }}
              />
              <Tooltip title={getConfidenceTooltip()} arrow>
                <Chip
                  label={`${error.confidenceLevel || 'Unknown'}`}
                  size="small"
                  icon={<InfoOutlined sx={{ fontSize: '0.75rem !important' }} />}
                  sx={{
                    fontSize: '0.75rem',
                    height: 24,
                    backgroundColor: getConfidenceColor(error.confidenceLevel || 'Unknown'),
                    color: 'white',
                    fontWeight: 'bold',
                    '& .MuiChip-icon': {
                      color: 'white',
                      fontSize: '0.75rem'
                    }
                  }}
                />
              </Tooltip>

              <IconButton
                size="small"
                onClick={onDismiss}
                sx={{
                  color: 'text.secondary',
                  '&:hover': {
                    backgroundColor: 'action.hover',
                    color: 'text.primary'
                  }
                }}
                aria-label="Dismiss error"
              >
                <Close fontSize="small" />
              </IconButton>
            </Box>
          </Box>

          {/* Value comparison */}
          <Box sx={{
            mb: 3,
            p: 2,
            backgroundColor: 'grey.50',
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'grey.200'
          }}>
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Current Value
              </Typography>
              <Typography variant="body2" color="text.primary" sx={{ mt: 0.5, fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {error.currentValue || <em style={{ color: '#999' }}>(empty)</em>}
              </Typography>
            </Box>

            {error.recommendedValue && (
              <Box>
                <Typography variant="caption" color="primary.main" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Suggested Value
                </Typography>
                <Typography variant="body2" color="primary.dark" sx={{ mt: 0.5, fontFamily: 'monospace', fontSize: '0.875rem', fontWeight: 500 }}>
                  {error.recommendedValue}
                </Typography>
              </Box>
            )}
          </Box>


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
          <Stack direction="row" spacing={1}>
            {error.recommendedValue && (
              <Button
                size="small"
                variant="outlined"
                startIcon={<Check fontSize="small" />}
                onClick={onAccept}
                disabled={!error.recommendedValue}
                sx={{
                  textTransform: 'none',
                  fontWeight: 'bold',
                  minWidth: 90,
                  '&:hover': {
                    transform: 'translateY(-1px)',
                    boxShadow: 1
                  }
                }}
                aria-label={`Accept suggested value: ${error.recommendedValue}`}
              >
                Accept
              </Button>
            )}
            <Button
              size="small"
              variant="contained"
              startIcon={<CheckCircle fontSize="small" />}
              onClick={onAcceptAll}
              sx={{
                textTransform: 'none',
                fontWeight: 'bold',
                minWidth: 110,
                '&:hover': {
                  transform: 'translateY(-1px)',
                  boxShadow: 2
                }
              }}
              aria-label={`Accept all similar changes for column ${error.column}`}
            >
              Accept All
            </Button>
          </Stack>
        </Box>

      </CardActions>
    </Card>
  );
};
