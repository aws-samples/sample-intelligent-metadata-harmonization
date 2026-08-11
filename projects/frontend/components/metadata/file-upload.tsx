/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState, useRef, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Snackbar,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  SelectChangeEvent
} from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { useAuth } from 'react-oidc-context';
import { getAvailableSchemasForUI } from '../../lib/api';
import { SchemaOption, SchemaSelectionState } from '../../lib/types';

interface FileUploadProps {
  onFileProcessed: (data: string[][], coreSchemaId: string, programSchemaId: string) => void;
  initialCoreSchemaId?: string;
  initialProgramSchemaId?: string;
  disabled?: boolean;
}

export const FileUploadComponent: React.FC<FileUploadProps> = ({
  onFileProcessed,
  initialCoreSchemaId = '',
  initialProgramSchemaId = '',
  disabled = false
}) => {
  const auth = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Schema selection state
  const [schemaState, setSchemaState] = useState<SchemaSelectionState>({
    coreSchemaId: '', // Don't set initial values until schemas are loaded
    programSchemaId: '', // Don't set initial values until schemas are loaded
    coreSchemas: [],
    programSchemas: [],
    loading: true,
    error: undefined
  });

  // Load available schemas on component mount
  useEffect(() => {
    const loadSchemas = async () => {
      console.log('📋 FileUpload: Loading available schemas...');

      try {
        setSchemaState(prev => ({ ...prev, loading: true, error: undefined }));

        const response = await getAvailableSchemasForUI(auth.user?.id_token);

        if (response.success && response.data) {
          console.log('✅ FileUpload: Schemas loaded successfully:', {
            coreSchemas: response.data.coreSchemas.length,
            programSchemas: response.data.programSchemas.length
          });

          // Validate initial schema IDs against available schemas
          const validCoreSchemaId = initialCoreSchemaId &&
            response.data.coreSchemas.some(schema => schema.id === initialCoreSchemaId)
            ? initialCoreSchemaId : '';

          const validProgramSchemaId = initialProgramSchemaId &&
            response.data.programSchemas.some(schema => schema.id === initialProgramSchemaId)
            ? initialProgramSchemaId : '';

          console.log('📋 FileUpload: Setting initial schema values:', {
            initialCoreSchemaId,
            validCoreSchemaId,
            initialProgramSchemaId,
            validProgramSchemaId
          });

          setSchemaState(prev => ({
            ...prev,
            coreSchemaId: validCoreSchemaId,
            programSchemaId: validProgramSchemaId,
            coreSchemas: response.data!.coreSchemas,
            programSchemas: response.data!.programSchemas,
            loading: false,
            error: undefined
          }));
        } else {
          const errorMessage = response.error || 'Failed to load available schemas';
          console.error('❌ FileUpload: Schema loading failed:', errorMessage);

          setSchemaState(prev => ({
            ...prev,
            loading: false,
            error: errorMessage
          }));

          setError(errorMessage);
          setSnackbarOpen(true);
        }
      } catch (err) {
        const errorMessage = 'Failed to load schemas from server';
        console.error('❌ FileUpload: Schema loading error:', err);

        setSchemaState(prev => ({
          ...prev,
          loading: false,
          error: errorMessage
        }));

        setError(errorMessage);
        setSnackbarOpen(true);
      }
    };

    loadSchemas();
  }, []);

  // Handle schema selection changes
  const handleCoreSchemaChange = (event: SelectChangeEvent<string>) => {
    const newCoreSchemaId = event.target.value;
    console.log('📋 FileUpload: Core schema selected:', newCoreSchemaId);

    setSchemaState(prev => ({
      ...prev,
      coreSchemaId: newCoreSchemaId
    }));
  };

  const handleProgramSchemaChange = (event: SelectChangeEvent<string>) => {
    const newProgramSchemaId = event.target.value;
    console.log('📋 FileUpload: Program schema selected:', newProgramSchemaId);

    setSchemaState(prev => ({
      ...prev,
      programSchemaId: newProgramSchemaId
    }));
  };

  const parseCSV = (text: string): string[][] => {
    console.log('📄 FileUpload: Starting CSV parsing:', {
      textLength: text.length,
      textPreview: text.substring(0, 200) + (text.length > 200 ? '...' : '')
    });

    const lines = text.split('\n');
    console.log('📄 FileUpload: Split into lines:', {
      totalLines: lines.length,
      firstFewLines: lines.slice(0, 3)
    });

    const result: string[][] = [];

    for (const line of lines) {
      if (line.trim() === '') continue;

      const row: string[] = [];
      let current = '';
      let inQuotes = false;

      for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          row.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }

      row.push(current.trim());
      result.push(row);
    }

    console.log('📄 FileUpload: CSV parsing completed:', {
      totalRows: result.length,
      firstFewRows: result.slice(0, 3),
      columnCount: result[0]?.length || 0
    });

    return result;
  };

  const validateFile = (file: File): string | null => {
    // Check file extension
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return 'Please select a CSV file (.csv extension required)';
    }

    // Check file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB in bytes
    if (file.size > maxSize) {
      return 'File size must be less than 10MB';
    }

    return null;
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    console.log('📁 FileUpload: File selected:', {
      fileName: file?.name,
      fileSize: file?.size,
      fileType: file?.type,
      coreSchemaId: schemaState.coreSchemaId,
      programSchemaId: schemaState.programSchemaId
    });

    if (!file) return;

    // Validate schema selection first
    if (!schemaState.coreSchemaId || !schemaState.programSchemaId) {
      const errorMessage = 'Please select both Core and Program schemas before uploading a file';
      console.log('❌ FileUpload: Schema validation failed:', errorMessage);
      setError(errorMessage);
      setSnackbarOpen(true);
      return;
    }

    // Validate file
    const validationError = validateFile(file);
    if (validationError) {
      console.log('❌ FileUpload: File validation failed:', validationError);
      setError(validationError);
      setSnackbarOpen(true);
      return;
    }

    console.log('✅ FileUpload: File and schema validation passed, starting processing');
    setLoading(true);
    setError(null);

    try {
      const text = await file.text();
      console.log('📖 FileUpload: File text read successfully:', {
        textLength: text.length,
        isEmpty: !text.trim()
      });

      if (!text.trim()) {
        throw new Error('CSV file is empty');
      }

      const parsedData = parseCSV(text);

      if (parsedData.length === 0) {
        throw new Error('No valid data found in CSV file');
      }

      // Validate that we have at least a header row
      if (parsedData.length < 2) {
        throw new Error('CSV file must contain at least a header row and one data row');
      }

      console.log('🎉 FileUpload: File processing completed successfully, calling onFileProcessed:', {
        dataRows: parsedData.length,
        dataPreview: parsedData.slice(0, 3),
        coreSchemaId: schemaState.coreSchemaId,
        programSchemaId: schemaState.programSchemaId
      });

      onFileProcessed(parsedData, schemaState.coreSchemaId, schemaState.programSchemaId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to parse CSV file';
      console.log('❌ FileUpload: Error during file processing:', errorMessage);
      setError(errorMessage);
      setSnackbarOpen(true);
    } finally {
      setLoading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };

  // Determine if upload should be disabled
  const isUploadDisabled = loading ||
                          schemaState.loading ||
                          !schemaState.coreSchemaId ||
                          !schemaState.programSchemaId ||
                          disabled ||
                          !!schemaState.error;

  return (
    <Container maxWidth="md" sx={{ py: 8 }}>
      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="h4" gutterBottom>
          Upload Metadata File
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Select validation schemas and upload a CSV file containing your metadata
        </Typography>

        {/* Schema Selection */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth disabled={schemaState.loading || disabled}>
              <InputLabel id="core-schema-label">Core Schema</InputLabel>
              <Select
                labelId="core-schema-label"
                value={schemaState.coreSchemaId}
                label="Core Schema"
                onChange={handleCoreSchemaChange}
                error={!!schemaState.error}
              >
                {schemaState.coreSchemas.map((schema) => (
                  <MenuItem key={schema.id} value={schema.id}>
                    {schema.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth disabled={schemaState.loading || disabled}>
              <InputLabel id="program-schema-label">Program Schema</InputLabel>
              <Select
                labelId="program-schema-label"
                value={schemaState.programSchemaId}
                label="Program Schema"
                onChange={handleProgramSchemaChange}
                error={!!schemaState.error}
              >
                {schemaState.programSchemas.map((schema) => (
                  <MenuItem key={schema.id} value={schema.id}>
                    {schema.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        {/* Schema Loading State */}
        {schemaState.loading && (
          <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CircularProgress size={20} sx={{ mr: 1 }} />
            <Typography variant="body2" color="text.secondary">
              Loading available schemas...
            </Typography>
          </Box>
        )}

        {/* Schema Error State */}
        {schemaState.error && !schemaState.loading && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {schemaState.error}
          </Alert>
        )}

        {/* File Upload */}
        <Box sx={{ mb: 3 }}>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            ref={fileInputRef}
            style={{ display: 'none' }}
            disabled={isUploadDisabled}
          />
          <Button
            variant="contained"
            size="large"
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <CloudUpload />}
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploadDisabled}
            sx={{ minWidth: 200 }}
          >
            {loading ? 'Processing...' : 'Choose CSV File'}
          </Button>
        </Box>

        {/* Validation Message */}
        {(!schemaState.coreSchemaId || !schemaState.programSchemaId) && !schemaState.loading && !schemaState.error && (
          <Typography variant="body2" color="warning.main" sx={{ mb: 2 }}>
            Please select both Core and Program schemas to enable file upload
          </Typography>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Maximum file size: 10MB • Supported format: CSV
        </Typography>
      </Box>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Container>
  );
};
