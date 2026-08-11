/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { FileUploadComponent } from '../../../components/metadata/file-upload';
import * as api from '../../../lib/api';

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

// Mock file for testing
const createMockFile = (name: string, size: number, content: string): File => {
  const file = new File([content], name, { type: 'text/csv' });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

// Mock API module
jest.mock('../../../lib/api');
const mockApi = api as jest.Mocked<typeof api>;

// Mock schema data
const mockSchemaData = {
  coreSchemas: [
    { id: 'core-1', name: 'Core Schema 1', description: 'First core schema' },
    { id: 'core-2', name: 'Core Schema 2', description: 'Second core schema' }
  ],
  programSchemas: [
    { id: 'program-1', name: 'Program Schema 1', description: 'First program schema' },
    { id: 'program-2', name: 'Program Schema 2', description: 'Second program schema' }
  ],
  rawSchemas: []
};

// Helper function to select schemas
const selectSchemas = async (coreSchemaName = 'Core Schema 1', programSchemaName = 'Program Schema 1') => {
  await waitFor(() => {
    expect(screen.getByLabelText('Core Schema')).toBeInTheDocument();
  });

  // Select core schema
  const coreSchemaSelect = screen.getByLabelText('Core Schema');
  fireEvent.mouseDown(coreSchemaSelect);

  // Wait for the menu to open and find the option
  await waitFor(() => {
    const option = screen.getByRole('option', { name: coreSchemaName });
    expect(option).toBeInTheDocument();
  });
  fireEvent.click(screen.getByRole('option', { name: coreSchemaName }));

  // Select program schema
  const programSchemaSelect = screen.getByLabelText('Program Schema');
  fireEvent.mouseDown(programSchemaSelect);

  // Wait for the menu to open and find the option
  await waitFor(() => {
    const option = screen.getByRole('option', { name: programSchemaName });
    expect(option).toBeInTheDocument();
  });
  fireEvent.click(screen.getByRole('option', { name: programSchemaName }));
};

describe('FileUploadComponent', () => {
  const mockOnFileProcessed = jest.fn();

  beforeEach(() => {
    mockOnFileProcessed.mockClear();

    // Mock successful schema loading by default
    mockApi.getAvailableSchemasForUI.mockResolvedValue({
      success: true,
      data: mockSchemaData
    });
  });

  it('renders upload interface correctly', async () => {
    renderWithTheme(<FileUploadComponent onFileProcessed={mockOnFileProcessed} />);

    expect(screen.getByText('Upload Metadata File')).toBeInTheDocument();
    expect(screen.getByText('Select validation schemas and upload a CSV file containing your metadata')).toBeInTheDocument();
    expect(screen.getByText('Choose CSV File')).toBeInTheDocument();
    expect(screen.getByText('Maximum file size: 10MB • Supported format: CSV')).toBeInTheDocument();

    // Wait for schemas to load
    await waitFor(() => {
      expect(screen.getByLabelText('Core Schema')).toBeInTheDocument();
      expect(screen.getByLabelText('Program Schema')).toBeInTheDocument();
    });
  });

  it('loads schemas on mount', async () => {
    renderWithTheme(<FileUploadComponent onFileProcessed={mockOnFileProcessed} />);

    // Should show loading state initially
    expect(screen.getByText('Loading available schemas...')).toBeInTheDocument();

    // Wait for schemas to load
    await waitFor(() => {
      expect(mockApi.getAvailableSchemasForUI).toHaveBeenCalled();
      expect(screen.queryByText('Loading available schemas...')).not.toBeInTheDocument();
    });
  });

  it('displays schema selection dropdowns', async () => {
    renderWithTheme(<FileUploadComponent onFileProcessed={mockOnFileProcessed} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Core Schema')).toBeInTheDocument();
      expect(screen.getByLabelText('Program Schema')).toBeInTheDocument();
    });
  });

  it('requires both schemas to be selected before enabling upload', async () => {
    renderWithTheme(<FileUploadComponent onFileProcessed={mockOnFileProcessed} />);

    await waitFor(() => {
      expect(screen.getByText('Please select both Core and Program schemas to enable file upload')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /choose csv file/i })).toBeDisabled();
    });
  });

  it('enables upload button when both schemas are selected', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    // Wait for schemas to load - when both schemas are set via props, button should be enabled
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    // Validation message should not be present
    expect(screen.queryByText('Please select both Core and Program schemas to enable file upload')).not.toBeInTheDocument();
  });

  it('validates schema selection before file processing', async () => {
    renderWithTheme(<FileUploadComponent onFileProcessed={mockOnFileProcessed} />);

    // Wait for schemas to load
    await waitFor(() => {
      expect(screen.getByLabelText('Core Schema')).toBeInTheDocument();
    });

    // Try to upload without selecting schemas
    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    const validFile = createMockFile('test.csv', 1000, 'Name,Age\nJohn,25');

    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByText('Please select both Core and Program schemas before uploading a file')).toBeInTheDocument();
    });

    expect(mockOnFileProcessed).not.toHaveBeenCalled();
  });

  it('validates file extension correctly', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    // Wait for button to be enabled
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    const invalidFile = createMockFile('test.txt', 1000, 'test content');

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    await waitFor(() => {
      expect(screen.getByText('Please select a CSV file (.csv extension required)')).toBeInTheDocument();
    });

    expect(mockOnFileProcessed).not.toHaveBeenCalled();
  });

  it('validates file size correctly', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    // Wait for button to be enabled
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    const largeFile = createMockFile('test.csv', 11 * 1024 * 1024, 'test content'); // 11MB

    fireEvent.change(fileInput, { target: { files: [largeFile] } });

    await waitFor(() => {
      expect(screen.getByText('File size must be less than 10MB')).toBeInTheDocument();
    });

    expect(mockOnFileProcessed).not.toHaveBeenCalled();
  });

  it('processes valid CSV file correctly with schema IDs', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    // Wait for button to be enabled
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    const csvContent = 'Name,Age,City\nJohn,25,New York\nJane,30,Boston';
    const validFile = createMockFile('test.csv', 1000, csvContent);

    // Mock file.text() method
    validFile.text = jest.fn().mockResolvedValue(csvContent);

    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(mockOnFileProcessed).toHaveBeenCalledWith(
        [
          ['Name', 'Age', 'City'],
          ['John', '25', 'New York'],
          ['Jane', '30', 'Boston']
        ],
        'core-1',
        'program-1'
      );
    });
  });

  it('handles CSV parsing with quotes correctly', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    const csvContent = 'Name,Description\n"John Doe","A person with, comma"\n"Jane Smith","Another person"';
    const validFile = createMockFile('test.csv', 1000, csvContent);

    validFile.text = jest.fn().mockResolvedValue(csvContent);

    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(mockOnFileProcessed).toHaveBeenCalledWith(
        [
          ['Name', 'Description'],
          ['John Doe', 'A person with, comma'],
          ['Jane Smith', 'Another person']
        ],
        'core-1',
        'program-1'
      );
    });
  });

  it('handles empty CSV file error', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    const emptyFile = createMockFile('test.csv', 0, '');
    emptyFile.text = jest.fn().mockResolvedValue('');

    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [emptyFile] } });

    await waitFor(() => {
      expect(screen.getByText('CSV file is empty')).toBeInTheDocument();
    });

    expect(mockOnFileProcessed).not.toHaveBeenCalled();
  });

  it('handles CSV with insufficient data', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    const csvContent = 'Name,Age'; // Only header, no data rows
    const validFile = createMockFile('test.csv', 1000, csvContent);
    validFile.text = jest.fn().mockResolvedValue(csvContent);

    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByText('CSV file must contain at least a header row and one data row')).toBeInTheDocument();
    });

    expect(mockOnFileProcessed).not.toHaveBeenCalled();
  });

  it('handles schema loading error', async () => {
    mockApi.getAvailableSchemasForUI.mockResolvedValue({
      success: false,
      error: 'Failed to load schemas'
    });

    renderWithTheme(<FileUploadComponent onFileProcessed={mockOnFileProcessed} />);

    await waitFor(() => {
      expect(screen.getAllByText('Failed to load schemas')).toHaveLength(2); // Alert and Snackbar
      expect(screen.getByRole('button', { name: /choose csv file/i })).toBeDisabled();
    });
  });

  it('handles network error during schema loading', async () => {
    mockApi.getAvailableSchemasForUI.mockRejectedValue(new Error('Network error'));

    renderWithTheme(<FileUploadComponent onFileProcessed={mockOnFileProcessed} />);

    await waitFor(() => {
      expect(screen.getAllByText('Failed to load schemas from server')).toHaveLength(2); // Alert and Snackbar
      expect(screen.getByRole('button', { name: /choose csv file/i })).toBeDisabled();
    });
  });

  it('shows loading state during file processing', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    const csvContent = 'Name,Age\nJohn,25';
    const validFile = createMockFile('test.csv', 1000, csvContent);

    // Mock file.text() to return a promise that we can control
    let resolveText: (value: string) => void;
    const textPromise = new Promise<string>((resolve) => {
      resolveText = resolve;
    });
    validFile.text = jest.fn().mockReturnValue(textPromise);

    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    // Check loading state
    await waitFor(() => {
      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });

    // Resolve the promise
    resolveText!(csvContent);

    await waitFor(() => {
      expect(mockOnFileProcessed).toHaveBeenCalled();
    });
  });

  it('closes snackbar when close button is clicked', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-1"
        initialProgramSchemaId="program-1"
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /choose csv file/i })).not.toBeDisabled();
    });

    const fileInput = screen.getByRole('button', { name: /choose csv file/i }).previousSibling as HTMLInputElement;
    const invalidFile = createMockFile('test.txt', 1000, 'test content');

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    await waitFor(() => {
      expect(screen.getByText('Please select a CSV file (.csv extension required)')).toBeInTheDocument();
    });

    // Find and click the close button
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText('Please select a CSV file (.csv extension required)')).not.toBeInTheDocument();
    });
  });

  it('supports initial schema selection via props', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        initialCoreSchemaId="core-2"
        initialProgramSchemaId="program-2"
      />
    );

    // Wait for schemas to load first
    await waitFor(() => {
      expect(screen.getByLabelText('Core Schema')).toBeInTheDocument();
    });

    // Check that the correct schemas are selected by looking at the text content
    await waitFor(() => {
      expect(screen.getByText('Core Schema 2')).toBeInTheDocument();
      expect(screen.getByText('Program Schema 2')).toBeInTheDocument();
    });
  });

  it('can be disabled via props', async () => {
    renderWithTheme(
      <FileUploadComponent
        onFileProcessed={mockOnFileProcessed}
        disabled={true}
      />
    );

    await waitFor(() => {
      // Check that the Select components have disabled attributes
      const coreSchemaSelect = screen.getByLabelText('Core Schema');
      const programSchemaSelect = screen.getByLabelText('Program Schema');

      expect(coreSchemaSelect).toHaveAttribute('aria-disabled', 'true');
      expect(programSchemaSelect).toHaveAttribute('aria-disabled', 'true');
      expect(screen.getByRole('button', { name: /choose csv file/i })).toBeDisabled();
    });
  });
});
