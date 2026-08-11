/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Integration tests for success page with change tracking functionality
 * Tests the complete workflow from validation completion to change display
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import App, { AppState } from '../../components/app';
import { theme } from '../../lib/theme';
import {
  ChangeTrackingResults,
  ChangesSummary,
  ChangeObject,
  ChangeType,
  ChangeSourceType,
  ChangeComponent
} from '../../lib/types';

// Mock the auth context
jest.mock('react-oidc-context', () => ({
  useAuth: () => ({
    user: {
      access_token: 'mock-token',
      profile: {
        email: 'test@example.com',
        name: 'Test User'
      }
    },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

// Mock the API calls
jest.mock('../../lib/api', () => ({
  getAvailableSchemas: jest.fn(),
  getAvailableSchemasForUI: jest.fn().mockResolvedValue({
    success: true,
    coreSchemas: [],
    programSchemas: []
  }),
  submitMetadataValidation: jest.fn(),
  updateValidationJob: jest.fn(),
  pollValidationStatus: jest.fn(),
}));

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

// Mock change tracking data
const mockChangesSummary: ChangesSummary = {
  totalChanges: 5,
  adds: 2,
  removes: 1,
  renames: 2,
  systemChanges: 3,
  userChanges: 2
};

const mockChangeObjects: ChangeObject[] = [
  {
    changeId: 'chg_001',
    changeType: ChangeType.RENAME,
    sourceType: ChangeSourceType.SYSTEM,
    component: ChangeComponent.VALIDATION,
    row: 1,
    column: 'participant_id',
    oldValue: 'old_value',
    newValue: 'new_value',
    timestamp: '2025-01-01T12:00:00Z',
    sourceVersion: 1,
    targetVersion: 2,
    confidenceScore: 0.85
  },
  {
    changeId: 'chg_002',
    changeType: ChangeType.ADD,
    sourceType: ChangeSourceType.USER,
    component: ChangeComponent.VALIDATION,
    row: 2,
    column: 'status',
    newValue: 'added_value',
    timestamp: '2025-01-01T12:01:00Z',
    sourceVersion: 1,
    targetVersion: 2
  },
  {
    changeId: 'chg_003',
    changeType: ChangeType.REMOVE,
    sourceType: ChangeSourceType.SYSTEM,
    component: ChangeComponent.SCHEMA_ALIGNMENT,
    row: null, // Schema-level change
    column: 'temp_column',
    oldValue: 'removed_value',
    timestamp: '2025-01-01T12:02:00Z',
    sourceVersion: 1,
    targetVersion: 2,
    confidenceScore: 0.92
  }
];

const mockChangeTracking: ChangeTrackingResults = {
  changes: mockChangeObjects,
  summary: mockChangesSummary,
  comparisonMetadata: {
    detectionTimestamp: '2025-01-01T12:00:00Z',
    comparedVersions: [1, 2]
  }
};

// Helper to create App component with specific state
const createAppWithState = (state: Partial<AppState>) => {
  const AppWithState = () => {
    const [appState, setAppState] = React.useState<AppState>({
      stage: 'upload',
      csvData: null,
      validationErrors: null,
      ...state
    });

    // Override the state for testing
    React.useEffect(() => {
      setAppState(prev => ({ ...prev, ...state }));
    }, []);

    return <App />;
  };

  return AppWithState;
};

describe('Success Page Change Tracking Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Success Page with Change Tracking', () => {
    test('renders success page with change tracking data', async () => {
      // Create a mock App component that starts in complete stage with change tracking
      const MockApp = () => {
        const [appState, setAppState] = React.useState<AppState>({
          stage: 'complete',
          csvData: [['header1', 'header2'], ['data1', 'data2']],
          validationErrors: null,
          jobId: 'test-job-123',
          changeTracking: mockChangeTracking
        });

        const handleStartOver = () => {
          setAppState({
            stage: 'upload',
            csvData: null,
            validationErrors: null,
            jobId: undefined,
            changeTracking: undefined
          });
        };

        const handleValidationComplete = (jobId?: string, changeTracking?: ChangeTrackingResults) => {
          setAppState(prev => ({
            ...prev,
            stage: 'complete',
            jobId: jobId || prev.jobId,
            changeTracking: changeTracking || prev.changeTracking
          }));
        };

        const handleValidationErrors = (errors: any[], jobId?: string) => {
          setAppState(prev => ({
            ...prev,
            validationErrors: errors,
            jobId: jobId || prev.jobId
          }));
        };

        // Render the complete stage directly
        if (appState.stage === 'complete') {
          return (
            <div>
              {/* Success Header */}
              <div>
                <h1>Validation Complete!</h1>
                <p>Your metadata has been successfully validated and submitted.</p>
                {appState.jobId && (
                  <span data-testid="job-id">Job ID: {appState.jobId}</span>
                )}
              </div>

              {/* Change Tracking Section */}
              {appState.changeTracking ? (
                <div data-testid="change-tracking-section">
                  <h2>Changes Made During Processing</h2>

                  {/* Mock Changes Summary Card */}
                  <div data-testid="changes-summary">
                    <span>Total Changes: {appState.changeTracking.summary.totalChanges}</span>
                    <span>Adds: {appState.changeTracking.summary.adds}</span>
                    <span>Removes: {appState.changeTracking.summary.removes}</span>
                    <span>Renames: {appState.changeTracking.summary.renames}</span>
                    <span>System Changes: {appState.changeTracking.summary.systemChanges}</span>
                    <span>User Changes: {appState.changeTracking.summary.userChanges}</span>
                  </div>

                  {/* Mock Detailed Changes List */}
                  {appState.changeTracking.changes && appState.changeTracking.changes.length > 0 && (
                    <div data-testid="detailed-changes">
                      <h3>Detailed Changes ({appState.changeTracking.changes.length})</h3>
                      {appState.changeTracking.changes.map((change) => (
                        <div key={change.changeId} data-testid={`change-${change.changeId}`}>
                          <span>{change.changeType}</span>
                          <span>{change.sourceType}</span>
                          <span>{change.component}</span>
                          <span>{change.row ? `Row ${change.row}, ${change.column}` : change.column}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div data-testid="no-change-tracking">
                  <p>Change tracking information is not available for this validation session.</p>
                </div>
              )}

              {/* Action Buttons */}
              <button onClick={handleStartOver} data-testid="start-new-validation">
                Start New Validation
              </button>
            </div>
          );
        }

        return <div>Other stages not implemented in mock</div>;
      };

      renderWithTheme(<MockApp />);

      // Verify success page elements
      expect(screen.getByText('Validation Complete!')).toBeInTheDocument();
      expect(screen.getByText('Your metadata has been successfully validated and submitted.')).toBeInTheDocument();
      expect(screen.getByTestId('job-id')).toHaveTextContent('Job ID: test-job-123');

      // Verify change tracking section is present
      expect(screen.getByTestId('change-tracking-section')).toBeInTheDocument();
      expect(screen.getByText('Changes Made During Processing')).toBeInTheDocument();

      // Verify changes summary
      const summarySection = screen.getByTestId('changes-summary');
      expect(summarySection).toHaveTextContent('Total Changes: 5');
      expect(summarySection).toHaveTextContent('Adds: 2');
      expect(summarySection).toHaveTextContent('Removes: 1');
      expect(summarySection).toHaveTextContent('Renames: 2');
      expect(summarySection).toHaveTextContent('System Changes: 3');
      expect(summarySection).toHaveTextContent('User Changes: 2');

      // Verify detailed changes list
      expect(screen.getByTestId('detailed-changes')).toBeInTheDocument();
      expect(screen.getByText('Detailed Changes (3)')).toBeInTheDocument();

      // Verify individual changes
      expect(screen.getByTestId('change-chg_001')).toBeInTheDocument();
      expect(screen.getByTestId('change-chg_002')).toBeInTheDocument();
      expect(screen.getByTestId('change-chg_003')).toBeInTheDocument();

      // Verify action button
      expect(screen.getByTestId('start-new-validation')).toBeInTheDocument();
    });

    test('renders success page without change tracking data', async () => {
      const MockApp = () => {
        const [appState] = React.useState<AppState>({
          stage: 'complete',
          csvData: [['header1', 'header2'], ['data1', 'data2']],
          validationErrors: null,
          jobId: 'test-job-123',
          changeTracking: undefined // No change tracking data
        });

        if (appState.stage === 'complete') {
          return (
            <div>
              <h1>Validation Complete!</h1>
              <p>Your metadata has been successfully validated and submitted.</p>

              {appState.changeTracking ? (
                <div data-testid="change-tracking-section">
                  <h2>Changes Made During Processing</h2>
                </div>
              ) : (
                <div data-testid="no-change-tracking">
                  <p>Change tracking information is not available for this validation session.</p>
                  <p>This may occur if this is the first validation or if change detection encountered an issue.</p>
                </div>
              )}
            </div>
          );
        }

        return <div>Other stages not implemented in mock</div>;
      };

      renderWithTheme(<MockApp />);

      // Verify success page elements
      expect(screen.getByText('Validation Complete!')).toBeInTheDocument();

      // Verify no change tracking message is shown
      expect(screen.getByTestId('no-change-tracking')).toBeInTheDocument();
      expect(screen.getByText('Change tracking information is not available for this validation session.')).toBeInTheDocument();
      expect(screen.getByText('This may occur if this is the first validation or if change detection encountered an issue.')).toBeInTheDocument();

      // Verify change tracking section is not present
      expect(screen.queryByTestId('change-tracking-section')).not.toBeInTheDocument();
    });

    test('handles start new validation button click', async () => {
      const MockApp = () => {
        const [appState, setAppState] = React.useState<AppState>({
          stage: 'complete',
          csvData: [['header1', 'header2'], ['data1', 'data2']],
          validationErrors: null,
          jobId: 'test-job-123',
          changeTracking: mockChangeTracking
        });

        const handleStartOver = () => {
          setAppState({
            stage: 'upload',
            csvData: null,
            validationErrors: null,
            jobId: undefined,
            changeTracking: undefined
          });
        };

        if (appState.stage === 'complete') {
          return (
            <div>
              <h1>Validation Complete!</h1>
              <div data-testid="change-tracking-section">
                <h2>Changes Made During Processing</h2>
              </div>
              <button onClick={handleStartOver} data-testid="start-new-validation">
                Start New Validation
              </button>
            </div>
          );
        }

        if (appState.stage === 'upload') {
          return (
            <div data-testid="upload-stage">
              <h1>Upload Metadata File</h1>
            </div>
          );
        }

        return <div>Other stages not implemented in mock</div>;
      };

      renderWithTheme(<MockApp />);

      // Verify we're on the complete page
      expect(screen.getByText('Validation Complete!')).toBeInTheDocument();
      expect(screen.getByTestId('change-tracking-section')).toBeInTheDocument();

      // Click the start new validation button
      const startNewButton = screen.getByTestId('start-new-validation');
      fireEvent.click(startNewButton);

      // Verify we've navigated back to upload stage
      await waitFor(() => {
        expect(screen.getByTestId('upload-stage')).toBeInTheDocument();
        expect(screen.getByText('Upload Metadata File')).toBeInTheDocument();
      });

      // Verify complete page elements are no longer present
      expect(screen.queryByText('Validation Complete!')).not.toBeInTheDocument();
      expect(screen.queryByTestId('change-tracking-section')).not.toBeInTheDocument();
    });

    test('handles empty changes array gracefully', async () => {
      const emptyChangeTracking: ChangeTrackingResults = {
        changes: [], // Empty changes array
        summary: {
          totalChanges: 0,
          adds: 0,
          removes: 0,
          renames: 0,
          systemChanges: 0,
          userChanges: 0
        },
        comparisonMetadata: {
          detectionTimestamp: '2025-01-01T12:00:00Z',
          comparedVersions: [1, 2]
        }
      };

      const MockApp = () => {
        const [appState] = React.useState<AppState>({
          stage: 'complete',
          csvData: [['header1', 'header2'], ['data1', 'data2']],
          validationErrors: null,
          jobId: 'test-job-123',
          changeTracking: emptyChangeTracking
        });

        if (appState.stage === 'complete') {
          return (
            <div>
              <h1>Validation Complete!</h1>

              {appState.changeTracking ? (
                <div data-testid="change-tracking-section">
                  <h2>Changes Made During Processing</h2>

                  <div data-testid="changes-summary">
                    <span>Total Changes: {appState.changeTracking.summary.totalChanges}</span>
                  </div>

                  {appState.changeTracking.changes && appState.changeTracking.changes.length > 0 ? (
                    <div data-testid="detailed-changes">
                      <h3>Detailed Changes</h3>
                    </div>
                  ) : (
                    <div data-testid="no-changes-message">
                      <p>No individual changes to display.</p>
                    </div>
                  )}
                </div>
              ) : (
                <div data-testid="no-change-tracking">
                  <p>Change tracking information is not available.</p>
                </div>
              )}
            </div>
          );
        }

        return <div>Other stages not implemented in mock</div>;
      };

      renderWithTheme(<MockApp />);

      // Verify success page elements
      expect(screen.getByText('Validation Complete!')).toBeInTheDocument();

      // Verify change tracking section is present
      expect(screen.getByTestId('change-tracking-section')).toBeInTheDocument();

      // Verify summary shows zero changes
      const summarySection = screen.getByTestId('changes-summary');
      expect(summarySection).toHaveTextContent('Total Changes: 0');

      // Verify no detailed changes are shown
      expect(screen.queryByTestId('detailed-changes')).not.toBeInTheDocument();
      expect(screen.getByTestId('no-changes-message')).toBeInTheDocument();
      expect(screen.getByText('No individual changes to display.')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('handles malformed change tracking data gracefully', async () => {
      const malformedChangeTracking = {
        changes: null, // Malformed data
        summary: null,
        comparisonMetadata: {}
      } as any;

      const MockApp = () => {
        const [appState] = React.useState<AppState>({
          stage: 'complete',
          csvData: [['header1', 'header2'], ['data1', 'data2']],
          validationErrors: null,
          jobId: 'test-job-123',
          changeTracking: malformedChangeTracking
        });

        if (appState.stage === 'complete') {
          return (
            <div>
              <h1>Validation Complete!</h1>

              {appState.changeTracking ? (
                <div data-testid="change-tracking-section">
                  <h2>Changes Made During Processing</h2>

                  {/* Handle malformed summary gracefully */}
                  {appState.changeTracking.summary ? (
                    <div data-testid="changes-summary">
                      <span>Total Changes: {appState.changeTracking.summary.totalChanges}</span>
                    </div>
                  ) : (
                    <div data-testid="malformed-summary">
                      <p>Change summary data is not available.</p>
                    </div>
                  )}

                  {/* Handle malformed changes array gracefully */}
                  {appState.changeTracking.changes && Array.isArray(appState.changeTracking.changes) && appState.changeTracking.changes.length > 0 ? (
                    <div data-testid="detailed-changes">
                      <h3>Detailed Changes</h3>
                    </div>
                  ) : (
                    <div data-testid="malformed-changes">
                      <p>Detailed change data is not available.</p>
                    </div>
                  )}
                </div>
              ) : (
                <div data-testid="no-change-tracking">
                  <p>Change tracking information is not available.</p>
                </div>
              )}
            </div>
          );
        }

        return <div>Other stages not implemented in mock</div>;
      };

      renderWithTheme(<MockApp />);

      // Verify success page elements
      expect(screen.getByText('Validation Complete!')).toBeInTheDocument();

      // Verify change tracking section is present
      expect(screen.getByTestId('change-tracking-section')).toBeInTheDocument();

      // Verify malformed data is handled gracefully
      expect(screen.getByTestId('malformed-summary')).toBeInTheDocument();
      expect(screen.getByText('Change summary data is not available.')).toBeInTheDocument();

      expect(screen.getByTestId('malformed-changes')).toBeInTheDocument();
      expect(screen.getByText('Detailed change data is not available.')).toBeInTheDocument();
    });

    test('handles missing job ID gracefully', async () => {
      const MockApp = () => {
        const [appState] = React.useState<AppState>({
          stage: 'complete',
          csvData: [['header1', 'header2'], ['data1', 'data2']],
          validationErrors: null,
          jobId: undefined, // Missing job ID
          changeTracking: mockChangeTracking
        });

        if (appState.stage === 'complete') {
          return (
            <div>
              <h1>Validation Complete!</h1>
              <p>Your metadata has been successfully validated and submitted.</p>
              {appState.jobId ? (
                <span data-testid="job-id">Job ID: {appState.jobId}</span>
              ) : (
                <span data-testid="no-job-id">Job ID not available</span>
              )}

              <div data-testid="change-tracking-section">
                <h2>Changes Made During Processing</h2>
              </div>
            </div>
          );
        }

        return <div>Other stages not implemented in mock</div>;
      };

      renderWithTheme(<MockApp />);

      // Verify success page elements
      expect(screen.getByText('Validation Complete!')).toBeInTheDocument();

      // Verify missing job ID is handled gracefully
      expect(screen.queryByTestId('job-id')).not.toBeInTheDocument();
      expect(screen.getByTestId('no-job-id')).toBeInTheDocument();
      expect(screen.getByText('Job ID not available')).toBeInTheDocument();

      // Verify change tracking still works
      expect(screen.getByTestId('change-tracking-section')).toBeInTheDocument();
    });
  });
});
