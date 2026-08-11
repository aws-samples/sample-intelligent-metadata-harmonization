/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// App.

"use client";

import React, { useState } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Button,
  Alert,
  Divider
} from "@mui/material";
import { LocalHospital, Refresh, CheckCircle, Warning } from "@mui/icons-material";

import { UserAuthNav } from "./auth/user-auth-nav";
import { commonStyles } from "../lib/ui-helpers";
import { FileUploadComponent } from "./metadata/file-upload";
import { MetadataEditorComponent } from "./metadata/metadata-editor";
import { ChangesSummaryCard } from "./metadata/changes-summary-card";
import { DetailedChangesList } from "./metadata/detailed-changes-list";
import { ValidationError, SchemaAlignmentResults, ChangeTrackingResults } from "../lib/types";

export interface AppState {
  stage: 'upload' | 'edit' | 'complete';
  csvData: string[][] | null;
  validationErrors: ValidationError[] | null;
  coreSchemaId?: string;
  programSchemaId?: string;
  jobId?: string;
  schemaAlignmentResults?: SchemaAlignmentResults;
  changeTracking?: ChangeTrackingResults;
}

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>({
    stage: 'upload',
    csvData: null,
    validationErrors: null,
    coreSchemaId: undefined,
    programSchemaId: undefined,
    jobId: undefined
  });

  const handleFileProcessed = (data: string[][], coreSchemaId: string, programSchemaId: string) => {
    console.log('🚀 App: File processed, transitioning to edit stage:', {
      dataLength: data.length,
      dataPreview: data.slice(0, 3),
      columnCount: data[0]?.length || 0,
      coreSchemaId,
      programSchemaId
    });
    setAppState({
      stage: 'edit',
      csvData: data,
      validationErrors: null,
      coreSchemaId,
      programSchemaId,
      jobId: undefined // Reset jobId for new validation
    });
  };

  const handleValidationComplete = (jobId?: string, changeTracking?: ChangeTrackingResults) => {
    console.log('✅ App: Validation completed, transitioning to complete stage', {
      jobId,
      hasChangeTracking: !!changeTracking,
      changeCount: changeTracking?.summary?.totalChanges || 0
    });
    setAppState(prev => ({
      ...prev,
      stage: 'complete',
      jobId: jobId || prev.jobId, // Keep existing jobId if not provided
      changeTracking: changeTracking || prev.changeTracking // Store change tracking data
    }));
  };

  const handleValidationErrors = (errors: ValidationError[], jobId?: string, schemaAlignmentResults?: SchemaAlignmentResults) => {
    const safeErrors = errors || [];
    console.log('⚠️ App: Validation errors received:', {
      errorCount: safeErrors.length,
      errors: safeErrors.slice(0, 3),
      jobId,
      hasSchemaAlignmentResults: !!schemaAlignmentResults
    });
    setAppState(prev => ({
      ...prev,
      validationErrors: safeErrors,
      jobId: jobId || prev.jobId, // Keep existing jobId if not provided
      schemaAlignmentResults // Store the schema alignment results in app state
    }));
  };

  const handleStartOver = () => {
    console.log('🔄 App: Starting over, resetting to upload stage');
    setAppState({
      stage: 'upload',
      csvData: null,
      validationErrors: null,
      coreSchemaId: undefined,
      programSchemaId: undefined,
      jobId: undefined,
      changeTracking: undefined
    });
  };

  const renderMainContent = () => {
    console.log('🎨 App: Rendering main content for stage:', appState.stage, {
      hasCsvData: !!appState.csvData,
      csvDataLength: appState.csvData?.length || 0,
      validationErrorsCount: appState.validationErrors?.length || 0
    });

    switch (appState.stage) {
      case 'upload':
        return (
          <FileUploadComponent onFileProcessed={handleFileProcessed} />
        );

      case 'edit':
        return (
          <MetadataEditorComponent
            csvData={appState.csvData!}
            validationErrors={appState.validationErrors}
            jobId={appState.jobId}
            coreSchemaId={appState.coreSchemaId}
            programSchemaId={appState.programSchemaId}
            schemaAlignmentResults={appState.schemaAlignmentResults}
            onValidationComplete={handleValidationComplete}
            onValidationErrors={handleValidationErrors}
          />
        );

      case 'complete':
        return (
          <Container maxWidth="lg" sx={{ py: 4 }}>
            {/* Success Header */}
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <CheckCircle
                sx={{
                  fontSize: 80,
                  color: 'success.main',
                  mb: 3
                }}
              />
              <Typography variant="h4" gutterBottom>
                Validation Complete!
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                Your metadata has been successfully validated and submitted.
              </Typography>
              {appState.jobId && typeof appState.jobId === 'string' && (
                <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                  Job ID: {appState.jobId}
                </Typography>
              )}
            </Box>

            {/* Change Tracking Section */}
            {appState.changeTracking ? (
              <Box sx={{ mb: 4 }}>
                <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                  Changes Made During Processing
                </Typography>

                {/* Changes Summary Card */}
                <ChangesSummaryCard
                  summary={appState.changeTracking.summary}
                  loading={false}
                  title="Processing Changes Summary"
                />

                {/* Detailed Changes List - only show if there are changes */}
                {appState.changeTracking.changes && appState.changeTracking.changes.length > 0 && (
                  <DetailedChangesList
                    changes={appState.changeTracking.changes}
                    loading={false}
                    initialDisplayCount={5}
                    enableFiltering={true}
                    enableSorting={true}
                  />
                )}
              </Box>
            ) : (
              <Box sx={{ mb: 4 }}>
                <Alert
                  severity="info"
                  icon={<Warning />}
                  sx={{ mb: 2 }}
                >
                  <Typography variant="body2">
                    Change tracking information is not available for this validation session.
                    This may occur if this is the first validation or if change detection encountered an issue.
                  </Typography>
                </Alert>
              </Box>
            )}

            <Divider sx={{ my: 4 }} />

            {/* Action Buttons */}
            <Box sx={{ textAlign: 'center' }}>
              <Button
                variant="contained"
                size="large"
                startIcon={<Refresh />}
                onClick={handleStartOver}
                sx={{ minWidth: 200 }}
              >
                Start New Validation
              </Button>
            </Box>
          </Container>
        );

      default:
        return null;
    }
  };

  return (
    <Box sx={commonStyles.fullHeightColumn}>
      {/* Header */}
      <AppBar position="static">
        <Toolbar>
          <LocalHospital sx={{ mr: 2 }} />
          <Typography variant="h6" component="h1" sx={{ flexGrow: 1 }}>
            Metadata Tool
          </Typography>
          <UserAuthNav />
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'grey.100',
          ...(appState.stage === 'edit' ? { py: 0 } : { py: 4 })
        }}
      >
        {renderMainContent()}
      </Box>
    </Box>
  );
};

export default App;
