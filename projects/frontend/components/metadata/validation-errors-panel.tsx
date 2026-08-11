/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import {
  Box,
  Typography,
  List,
  Button,
  Stack,
  Chip
} from '@mui/material';
import { CheckCircle, PlaylistAddCheck, Info, Warning } from '@mui/icons-material';
import { ValidationError } from '../../lib/types';

interface ValidationErrorsPanelProps {
  /** Array of validation errors to display */
  errors: ValidationError[];
  // currentView removed - no longer using toggle functionality
  /** Whether the panel is in a loading/processing state */
  isLoading?: boolean;
  /** Callback when user accepts/applies a single error correction */
  onAcceptError?: (error: ValidationError) => void;
  /** Callback when user accepts/applies all error corrections */
  onAcceptAllErrors?: (errors: ValidationError[]) => void;
  /** Callback when user dismisses a single error */
  onDismissError?: (error: ValidationError) => void;
  /** Custom error card components to render */
  children?: React.ReactNode;
}

/**
 * ValidationErrorsPanel component displays validation errors in a structured format
 * with options for accepting corrections and bulk operations.
 *
 * This component extracts the existing validation error display functionality
 * from the ValidationSidebarComponent to support the new tabbed interface.
 */
export const ValidationErrorsPanel: React.FC<ValidationErrorsPanelProps> = ({
  errors,
  isLoading = false,
  onAcceptError,
  onAcceptAllErrors,
  onDismissError,
  children
}) => {
  // Filter errors that have recommended values for bulk operations
  const errorsWithRecommendations = errors.filter((error: ValidationError) => error.recommendedValue !== null);
  const hasApplicableErrors = errorsWithRecommendations.length > 0;

  const handleAcceptAllErrors = () => {
    if (onAcceptAllErrors && hasApplicableErrors) {
      onAcceptAllErrors(errorsWithRecommendations);
    }
  };

  // Empty state when no errors exist
  if (!isLoading && errors.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <CheckCircle sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
        <Typography variant="body1" color="text.secondary" gutterBottom>
          No Validation Issues
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Your data passes all validation checks for the selected schema.
        </Typography>
      </Box>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
          Checking for validation issues...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header with bulk actions */}
      <Box sx={{ mb: 2, flexShrink: 0 }}>
        {/* Bulk Actions */}
        {hasApplicableErrors && onAcceptAllErrors && (
          <Box sx={{ mt: 1 }}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<PlaylistAddCheck />}
              onClick={handleAcceptAllErrors}
              sx={{ textTransform: 'none' }}
            >
              Accept All Recommendations ({errorsWithRecommendations.length})
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
              Only errors with automatic recommendations can be bulk-accepted
            </Typography>
          </Box>
        )}
      </Box>

      {/* Error List - Scrollable within parent container */}
      <Box sx={{
        flexGrow: 1,
        overflow: 'auto',
        minHeight: 0,
        '&::-webkit-scrollbar': {
          width: '8px',
        },
        '&::-webkit-scrollbar-track': {
          backgroundColor: 'grey.100',
          borderRadius: '4px',
        },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: 'grey.400',
          borderRadius: '4px',
          '&:hover': {
            backgroundColor: 'grey.600',
          },
        },
      }}>
        {children ? (
          // Render custom error cards passed as children
          <List sx={{ p: 0 }}>
            {children}
          </List>
        ) : (
          // Default error display if no custom cards provided
          <List sx={{ p: 0 }}>
            {errors.map((error: ValidationError, index: number) => (
              <Box key={`${error.row}-${error.column}-${index}`} sx={{ mb: 1, p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Row {error.row}, Column "{error.column}"
                  {error.schemaFieldName && error.schemaFieldName !== error.column && (
                    <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1, fontWeight: 'normal' }}>
                      (Schema field: {error.schemaFieldName})
                    </Typography>
                  )}
                </Typography>

                {/* Display custom error message prominently if available */}
                {error.errorMessage ? (
                  <Box sx={{ mb: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ mb: 0.5 }}>
                      <Chip
                        icon={<Info />}
                        label="Schema Requirement"
                        size="small"
                        color="info"
                        variant="outlined"
                        sx={{ fontSize: '0.75rem', height: 'auto', py: 0.5 }}
                      />
                    </Stack>
                    <Box sx={{ p: 1.5, backgroundColor: 'info.light', borderRadius: 1, border: '1px solid', borderColor: 'info.main' }}>
                      <Typography variant="body2" sx={{ fontWeight: 'medium', color: 'info.contrastText' }}>
                        {error.errorMessage}
                      </Typography>
                    </Box>
                  </Box>
                ) : (
                  // Fallback to generic error message when no custom message is available
                  <Box sx={{ mb: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ mb: 0.5 }}>
                      <Chip
                        icon={<Warning />}
                        label="System Generated"
                        size="small"
                        color="warning"
                        variant="outlined"
                        sx={{ fontSize: '0.75rem', height: 'auto', py: 0.5 }}
                      />
                    </Stack>
                    <Typography variant="body2" color="error.main" sx={{ fontWeight: 'medium' }}>
                      {error.errorType === 'REQUIRED_VALUE' && 'This field is required and cannot be empty.'}
                      {error.errorType === 'INVALID_OPTION' && 'The value is not one of the allowed options.'}
                      {error.errorType === 'INVALID_PATTERN' && 'The value does not match the required format.'}
                    </Typography>
                  </Box>
                )}

                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Current: "{error.currentValue}"
                </Typography>
                {error.recommendedValue ? (
                  <>
                    <Typography variant="body2" color="success.main" sx={{ mb: 1 }}>
                      Recommended: "{error.recommendedValue}"
                    </Typography>
                    {onAcceptError && (
                      <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                        <Button
                          size="small"
                          variant="contained"
                          color="primary"
                          onClick={() => onAcceptError(error)}
                          sx={{ textTransform: 'none' }}
                        >
                          Accept Recommendation
                        </Button>
                        {onDismissError && (
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => onDismissError(error)}
                            sx={{ textTransform: 'none' }}
                          >
                            Dismiss
                          </Button>
                        )}
                      </Stack>
                    )}
                  </>
                ) : error.validOptions && error.validOptions.length > 0 && (
                  <>
                    <Typography variant="body2" color="warning.main" sx={{ mb: 1 }}>
                      No automatic recommendation found
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                      Valid options: {error.validOptions.join(', ')}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontStyle: 'italic' }}>
                      You can manually edit this cell in the spreadsheet to use one of the valid options above.
                    </Typography>
                  </>
                )}
              </Box>
            ))}
          </List>
        )}
      </Box>
    </Box>
  );
};
