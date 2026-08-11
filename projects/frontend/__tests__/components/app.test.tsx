/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { useAuth } from 'react-oidc-context';
import App from '../../components/app';
import { beforeEach } from 'node:test';

// Mock the react-oidc-context hook
jest.mock('react-oidc-context');
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

// Mock the UserAuthNav component
jest.mock('../../components/auth/user-auth-nav', () => ({
  UserAuthNav: () => <div data-testid="user-auth-nav">UserAuthNav</div>
}));

// Mock the metadata components
jest.mock('../../components/metadata/file-upload', () => ({
  FileUploadComponent: ({ onFileProcessed }: any) => (
    <div data-testid="file-upload-component">
      <div>File Upload Component</div>
      <button onClick={() => onFileProcessed([['Name', 'Age'], ['John', '25']], 'core-schema-1', 'program-schema-1')}>
        Mock File Upload
      </button>
    </div>
  )
}));

jest.mock('../../components/metadata/metadata-editor', () => ({
  MetadataEditorComponent: ({ csvData, onValidationComplete, onValidationErrors }: any) => (
    <div data-testid="metadata-editor-component">
      <div>Metadata Editor Component</div>
      <div>Data rows: {csvData.length}</div>
      <button onClick={onValidationComplete}>Mock Complete Validation</button>
      <button onClick={() => onValidationErrors([{ row: 1, column: 'Name', currentValue: 'John', recommendedValue: 'John Doe', errorType: 'INVALID_FORMAT' }])}>
        Mock Validation Errors
      </button>
    </div>
  )
}));

// Create a test theme
const theme = createTheme();

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

describe('App Component', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();

    // Mock authenticated user by default
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        profile: {
          email: 'test@example.com'
        }
      }
    } as any);
  });

  it('renders Metadata Tool title', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Check for the main title in the header
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Metadata Tool');
  });

  it('shows authentication navigation', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Check that UserAuthNav component is rendered
    expect(screen.getByTestId('user-auth-nav')).toBeInTheDocument();
  });

  it('displays hospital icon in header', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Check for the LocalHospital icon (Material UI icons have specific test attributes)
    const hospitalIcon = document.querySelector('[data-testid="LocalHospitalIcon"]');
    expect(hospitalIcon).toBeInTheDocument();
  });

  it('starts in upload stage', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    expect(screen.getByTestId('file-upload-component')).toBeInTheDocument();
    expect(screen.getByText('File Upload Component')).toBeInTheDocument();
  });

  it('transitions from upload to edit stage when file is processed', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Initially in upload stage
    expect(screen.getByTestId('file-upload-component')).toBeInTheDocument();

    // Simulate file upload
    const uploadButton = screen.getByText('Mock File Upload');
    fireEvent.click(uploadButton);

    // Should now be in edit stage
    expect(screen.queryByTestId('file-upload-component')).not.toBeInTheDocument();
    expect(screen.getByTestId('metadata-editor-component')).toBeInTheDocument();
    expect(screen.getByText('Data rows: 2')).toBeInTheDocument();
  });

  it('transitions from edit to complete stage when validation completes', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Upload a file first
    const uploadButton = screen.getByText('Mock File Upload');
    fireEvent.click(uploadButton);

    // Should be in edit stage
    expect(screen.getByTestId('metadata-editor-component')).toBeInTheDocument();

    // Complete validation
    const completeButton = screen.getByText('Mock Complete Validation');
    fireEvent.click(completeButton);

    // Should now be in complete stage
    expect(screen.queryByTestId('metadata-editor-component')).not.toBeInTheDocument();
    expect(screen.getByText('Validation Complete!')).toBeInTheDocument();
    expect(screen.getByText('Your metadata has been successfully validated and submitted.')).toBeInTheDocument();
    expect(screen.getByText('Start New Validation')).toBeInTheDocument();
  });

  it('handles validation errors in edit stage', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Upload a file first
    const uploadButton = screen.getByText('Mock File Upload');
    fireEvent.click(uploadButton);

    // Simulate validation errors
    const errorsButton = screen.getByText('Mock Validation Errors');
    fireEvent.click(errorsButton);

    // Should still be in edit stage but with errors
    expect(screen.getByTestId('metadata-editor-component')).toBeInTheDocument();
  });

  it('allows starting over from complete stage', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Go through the full workflow
    const uploadButton = screen.getByText('Mock File Upload');
    fireEvent.click(uploadButton);

    const completeButton = screen.getByText('Mock Complete Validation');
    fireEvent.click(completeButton);

    // Should be in complete stage
    expect(screen.getByText('Validation Complete!')).toBeInTheDocument();

    // Start over
    const startOverButton = screen.getByText('Start New Validation');
    fireEvent.click(startOverButton);

    // Should be back to upload stage
    expect(screen.getByTestId('file-upload-component')).toBeInTheDocument();
    expect(screen.queryByText('Validation Complete!')).not.toBeInTheDocument();
  });

  it('applies different styling for edit stage', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Check initial styling (upload stage)
    const mainContent = screen.getByRole('main');
    expect(mainContent).toHaveStyle('padding-top: 32px'); // py: 4

    // Upload a file to go to edit stage
    const uploadButton = screen.getByText('Mock File Upload');
    fireEvent.click(uploadButton);

    // Check edit stage styling (no padding)
    expect(mainContent).toHaveStyle('padding-top: 0px'); // py: 0
  });

  it('maintains app state correctly through transitions', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Upload file
    const uploadButton = screen.getByText('Mock File Upload');
    fireEvent.click(uploadButton);

    // Verify data is passed correctly
    expect(screen.getByText('Data rows: 2')).toBeInTheDocument();

    // Add validation errors
    const errorsButton = screen.getByText('Mock Validation Errors');
    fireEvent.click(errorsButton);

    // Complete validation
    const completeButton = screen.getByText('Mock Complete Validation');
    fireEvent.click(completeButton);

    // Should reach complete stage
    expect(screen.getByText('Validation Complete!')).toBeInTheDocument();
  });

  it('renders success icon in complete stage', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Go to complete stage
    const uploadButton = screen.getByText('Mock File Upload');
    fireEvent.click(uploadButton);

    const completeButton = screen.getByText('Mock Complete Validation');
    fireEvent.click(completeButton);

    // Check for success icon
    const successIcon = document.querySelector('[data-testid="CheckCircleIcon"]');
    expect(successIcon).toBeInTheDocument();
  });

  it('maintains responsive layout structure', () => {
    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Check for main structural elements
    expect(screen.getByRole('banner')).toBeInTheDocument(); // AppBar creates a banner role
    expect(screen.getByRole('main')).toBeInTheDocument(); // Main content area

    // Check that the layout has the expected structure
    const mainContent = screen.getByRole('main');
    expect(mainContent).toHaveStyle({ flexGrow: '1' });
  });

  it('renders without authentication context', () => {
    // Mock unauthenticated state
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null
    } as any);

    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Should still render the main title and content
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Metadata Tool');

    // UserAuthNav should still be rendered (it handles its own auth state)
    expect(screen.getByTestId('user-auth-nav')).toBeInTheDocument();

    // Should still show file upload component
    expect(screen.getByTestId('file-upload-component')).toBeInTheDocument();
  });
});
