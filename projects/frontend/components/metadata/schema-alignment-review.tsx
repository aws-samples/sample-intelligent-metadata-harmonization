/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,

  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  CircularProgress,
  Divider
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  ExpandMore,
  SwapHoriz,
  Add,
  Remove,
  Info
} from '@mui/icons-material';
import {
  SchemaAlignmentChange,
  SchemaAlignmentChangeType,
  SchemaAlignmentResults,
  TransformationSummary
} from '../../lib/types';
// Removed unused imports - now using direct conversion from SchemaAlignmentChangeDetail

interface SchemaAlignmentReviewProps {
  /** Schema alignment data from API response */
  schemaAlignmentData: SchemaAlignmentResults;
  /** Callback when user accepts all schema changes */
  onAcceptChanges: (changes: SchemaAlignmentChange[]) => void;
  /** Callback when user rejects all schema changes */
  onRejectChanges: (changes: SchemaAlignmentChange[]) => void;
  /** Whether the component is in a loading state */
  loading?: boolean;
  /** Optional error message to display */
  error?: string;
}

/**
 * SchemaAlignmentReviewComponent displays schema alignment changes for user review
 *
 * This component processes columnMappings from the API response and presents them
 * as user-friendly changes with statistics and detailed descriptions. Users can
 * accept or reject the schema alignment changes before proceeding with validation.
 *
 * Features:
 * - Displays transformation summary with statistics
 * - Shows detailed list of column changes (renamed, added, removed)
 * - Provides accept/reject functionality for schema changes
 * - Handles loading and error states
 * - Responsive design with Material UI components
 */
export const SchemaAlignmentReviewComponent: React.FC<SchemaAlignmentReviewProps> = ({
  schemaAlignmentData,
  onAcceptChanges,
  onRejectChanges,
  loading = false,
  error
}) => {
  const [changes, setChanges] = useState<SchemaAlignmentChange[]>([]);
  const [transformationSummary, setTransformationSummary] = useState<TransformationSummary | null>(null);
  const [processing, setProcessing] = useState(false);

  // Process schema alignment data when it changes
  useEffect(() => {
    if (!schemaAlignmentData || !schemaAlignmentData.schemaAlignmentResults) {
      setChanges([]);
      setTransformationSummary(null);
      return;
    }

    try {
      setProcessing(true);

      // Convert SchemaAlignmentChangeDetail to SchemaAlignmentChange
      const processedChanges: SchemaAlignmentChange[] = schemaAlignmentData.schemaAlignmentResults.map((detail, index) => {
        let change: SchemaAlignmentChange;

        switch (detail.changeType) {
          case 'rename':
            change = {
              id: `rename-${detail.originalColumn}-${detail.newColumn}-${index}`,
              type: SchemaAlignmentChangeType.COLUMN_RENAMED,
              originalColumn: detail.originalColumn,
              alignedColumn: detail.newColumn,
              description: `Column "${detail.originalColumn}" was renamed to "${detail.newColumn}"`,
              reason: detail.reason || 'Required by schema specification',
              canRevert: true,
              isAccepted: false
            };
            break;

          case 'add':
            change = {
              id: `add-${detail.newColumn}-${index}`,
              type: SchemaAlignmentChangeType.COLUMN_ADDED,
              alignedColumn: detail.newColumn,
              description: `Column "${detail.newColumn}" was added`,
              reason: detail.reason || 'Required by target schema',
              canRevert: false,
              isAccepted: false
            };
            break;

          case 'remove':
            change = {
              id: `remove-${detail.originalColumn}-${index}`,
              type: SchemaAlignmentChangeType.COLUMN_REMOVED,
              originalColumn: detail.originalColumn,
              description: `Column "${detail.originalColumn}" was removed`,
              reason: detail.reason || 'Not required by target schema',
              canRevert: true,
              isAccepted: false
            };
            break;

          default:
            // Skip unknown change types
            return null;
        }

        return change;
      }).filter((change): change is SchemaAlignmentChange => change !== null);

      setChanges(processedChanges);

      // Create transformation summary from the new structure
      const summary: TransformationSummary = {
        columnsRenamed: schemaAlignmentData.summary.columnsRenamed,
        columnsAdded: schemaAlignmentData.summary.columnsAdded,
        columnsRemoved: schemaAlignmentData.summary.columnsRemoved,
        rowsOriginal: schemaAlignmentData.summary.rowsOriginal,
        rowsAligned: schemaAlignmentData.summary.rowsAligned
      };

      setTransformationSummary(summary);
    } catch (err) {
      console.error('Error processing schema alignment data:', err);
      setChanges([]);
      setTransformationSummary(null);
    } finally {
      setProcessing(false);
    }
  }, [schemaAlignmentData]);

  // Helper function to get icon for change type
  const getChangeIcon = (type: SchemaAlignmentChangeType) => {
    switch (type) {
      case SchemaAlignmentChangeType.COLUMN_RENAMED:
        return <SwapHoriz color="primary" />;
      case SchemaAlignmentChangeType.COLUMN_ADDED:
        return <Add color="success" />;
      case SchemaAlignmentChangeType.COLUMN_REMOVED:
        return <Remove color="warning" />;
      default:
        return <Info color="info" />;
    }
  };

  // Helper function to get color for change type
  const getChangeColor = (type: SchemaAlignmentChangeType): "primary" | "success" | "warning" | "info" => {
    switch (type) {
      case SchemaAlignmentChangeType.COLUMN_RENAMED:
        return "primary";
      case SchemaAlignmentChangeType.COLUMN_ADDED:
        return "success";
      case SchemaAlignmentChangeType.COLUMN_REMOVED:
        return "warning";
      default:
        return "info";
    }
  };

  // Helper function to format change type for display
  const formatChangeType = (type: SchemaAlignmentChangeType): string => {
    return type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
  };

  // Handle accept changes
  const handleAcceptChanges = () => {
    if (changes.length === 0) {
      // No changes to accept, proceed directly
      onAcceptChanges([]);
      return;
    }

    // Mark all changes as accepted
    const acceptedChanges = changes.map(change => ({
      ...change,
      isAccepted: true
    }));

    onAcceptChanges(acceptedChanges);
  };

  // Handle reject changes
  const handleRejectChanges = () => {
    onRejectChanges(changes);
  };

  // Show loading state
  if (loading || processing) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <CircularProgress size={40} />
        <Typography variant="body1" sx={{ mt: 2 }}>
          Processing schema alignment changes...
        </Typography>
      </Box>
    );
  }

  // Show error state
  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Schema Alignment Error
          </Typography>
          <Typography variant="body2">
            {error}
          </Typography>
        </Alert>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
          <Button
            variant="outlined"
            onClick={() => onRejectChanges([])}
          >
            Continue Without Schema Alignment
          </Button>
        </Box>
      </Box>
    );
  }

  // Show empty state if no changes
  if (changes.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            No Schema Changes Required
          </Typography>
          <Typography variant="body2">
            Your data structure already matches the expected schema format. No alignment changes are needed.
          </Typography>
        </Alert>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
          <Button
            variant="contained"
            startIcon={<CheckCircle />}
            onClick={() => onAcceptChanges([])}
          >
            Continue to Validation
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Typography variant="h5" gutterBottom>
        Schema Alignment Changes
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Your data has been aligned to match the expected schema structure.
        Review the changes below before proceeding with validation.
      </Typography>

      {/* Summary Statistics */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Transformation Summary
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip
              icon={<SwapHoriz />}
              label={`${transformationSummary?.columnsRenamed || 0} Renamed`}
              color="primary"
              variant="outlined"
            />
            <Chip
              icon={<Add />}
              label={`${transformationSummary?.columnsAdded || 0} Added`}
              color="success"
              variant="outlined"
            />
            <Chip
              icon={<Remove />}
              label={`${transformationSummary?.columnsRemoved || 0} Removed`}
              color="warning"
              variant="outlined"
            />
          </Box>

          {/* Additional summary information */}
          {transformationSummary && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Total changes: {changes.length}
              </Typography>
              {transformationSummary.rowsOriginal && (
                <Typography variant="body2" color="text.secondary">
                  Rows processed: {transformationSummary.rowsOriginal}
                </Typography>
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Detailed Changes List */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Detailed Changes ({changes.length})</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            {changes.map((change, index) => (
              <React.Fragment key={change.id}>
                <ListItem>
                  <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                    {getChangeIcon(change.type)}
                  </Box>
                  <ListItemText
                    primary={change.description}
                    secondary={
                      <React.Fragment>
                        <Typography variant="body2" color="text.secondary" component="span">
                          {change.reason}
                        </Typography>
                        {change.originalColumn && change.alignedColumn && (
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }} component="span">
                            "{change.originalColumn}" → "{change.alignedColumn}"
                          </Typography>
                        )}
                      </React.Fragment>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Chip
                      size="small"
                      label={formatChangeType(change.type)}
                      color={getChangeColor(change.type)}
                      variant="outlined"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                {index < changes.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </AccordionDetails>
      </Accordion>

      {/* Information Alert */}
      <Alert severity="info" sx={{ mt: 3, mb: 3 }}>
        <Typography variant="body2" component="div">
          <strong>What happens next:</strong>
        </Typography>
        <Typography variant="body2" sx={{ mt: 1 }} component="div">
          • <strong>Accept Changes:</strong> Your data will be transformed according to the schema requirements and then validated.
        </Typography>
        <Typography variant="body2" component="div">
          • <strong>Reject Changes:</strong> Your original data structure will be preserved, but validation may fail if it doesn't match the schema.
        </Typography>
      </Alert>

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 3 }}>
        <Button
          variant="outlined"
          startIcon={<Cancel />}
          onClick={handleRejectChanges}
          disabled={processing}
        >
          Reject Changes
        </Button>
        <Button
          variant="contained"
          startIcon={<CheckCircle />}
          onClick={handleAcceptChanges}
          disabled={processing}
        >
          Accept & Continue
        </Button>
      </Box>
    </Box>
  );
};

export default SchemaAlignmentReviewComponent;
