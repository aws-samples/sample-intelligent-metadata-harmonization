/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * CSV Processing Utilities
 *
 * This module provides utilities for parsing and generating CSV data,
 * handling edge cases like quotes, commas, and special characters.
 */

export interface CSVParseOptions {
  delimiter?: string;
  quote?: string;
  escape?: string;
  skipEmptyLines?: boolean;
}

export interface CSVGenerateOptions {
  delimiter?: string;
  quote?: string;
  escape?: string;
  forceQuotes?: boolean;
}

export interface CSVValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Parse CSV text into a 2D array of strings
 */
export function parseCSV(
  text: string,
  options: CSVParseOptions = {}
): string[][] {
  const {
    delimiter = ',',
    quote = '"',
    escape = '"',
    skipEmptyLines = true
  } = options;

  console.log('📊 CSV Utils: Starting CSV parsing:', {
    textLength: text?.length || 0,
    textPreview: text?.substring(0, 100) + (text?.length > 100 ? '...' : ''),
    options
  });

  if (!text || text.trim() === '') {
    throw new Error('CSV text is empty or undefined');
  }

  const lines = text.split('\n');
  console.log('📊 CSV Utils: Split text into lines:', {
    lineCount: lines.length,
    firstFewLines: lines.slice(0, 3)
  });

  const result: string[][] = [];

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
    const line = lines[lineIndex];

    // Skip empty lines if requested
    if (skipEmptyLines && line.trim() === '') {
      continue;
    }

    const row: string[] = [];
    let current = '';
    let inQuotes = false;
    let i = 0;

    while (i < line.length) {
      const char = line[i];
      const nextChar = line[i + 1];

      if (char === quote) {
        if (inQuotes) {
          // Check for escaped quote
          if (nextChar === quote) {
            current += quote;
            i += 2; // Skip both quotes
            continue;
          } else {
            // End of quoted field
            inQuotes = false;
          }
        } else {
          // Start of quoted field
          inQuotes = true;
        }
      } else if (char === delimiter && !inQuotes) {
        // Field separator
        row.push(current.trim());
        current = '';
      } else {
        // Regular character
        current += char;
      }

      i++;
    }

    // Add the last field
    row.push(current.trim());

    // Only add non-empty rows or if we're not skipping empty lines
    if (!skipEmptyLines || row.some(cell => cell !== '')) {
      result.push(row);
    }
  }

  console.log('📊 CSV Utils: CSV parsing completed:', {
    resultRows: result.length,
    resultPreview: result.slice(0, 3),
    columnCount: result[0]?.length || 0
  });

  return result;
}

/**
 * Convert a 2D array of strings to CSV text
 */
export function generateCSV(
  data: string[][],
  options: CSVGenerateOptions = {}
): string {
  const {
    delimiter = ',',
    quote = '"',
    escape = '"',
    forceQuotes = false
  } = options;

  if (!data || data.length === 0) {
    return '';
  }

  return data.map(row =>
    row.map(cell => {
      if (cell === null || cell === undefined) {
        return '';
      }

      const cellStr = String(cell);

      // Determine if we need to quote this cell
      const needsQuoting = forceQuotes ||
        cellStr.includes(delimiter) ||
        cellStr.includes(quote) ||
        cellStr.includes('\n') ||
        cellStr.includes('\r') ||
        cellStr.startsWith(' ') ||
        cellStr.endsWith(' ');

      if (needsQuoting) {
        // Escape any existing quotes
        const escapedCell = cellStr.replace(new RegExp(quote, 'g'), escape + quote);
        return quote + escapedCell + quote;
      }

      return cellStr;
    }).join(delimiter)
  ).join('\n');
}

/**
 * Parse a File object as CSV
 */
export async function parseCSVFile(
  file: File,
  options: CSVParseOptions = {}
): Promise<string[][]> {
  if (!file) {
    throw new Error('No file provided');
  }

  if (!file.name.toLowerCase().endsWith('.csv')) {
    throw new Error('File must have .csv extension');
  }

  try {
    const text = await file.text();
    return parseCSV(text, options);
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Failed to parse CSV file: ${error.message}`);
    }
    throw new Error('Failed to parse CSV file: Unknown error');
  }
}

/**
 * Validate CSV structure and data
 */
export function validateCSV(data: string[][]): CSVValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check if data exists
  if (!data || data.length === 0) {
    errors.push('CSV data is empty');
    return { isValid: false, errors, warnings };
  }

  // Check for header row
  if (data.length < 2) {
    errors.push('CSV must contain at least a header row and one data row');
  }

  // Check for consistent column count
  const headerColumnCount = data[0]?.length || 0;
  if (headerColumnCount === 0) {
    errors.push('Header row is empty');
  }

  // Check each data row
  for (let i = 1; i < data.length; i++) {
    const row = data[i];

    if (row.length !== headerColumnCount) {
      warnings.push(`Row ${i + 1} has ${row.length} columns, expected ${headerColumnCount}`);
    }

    // Check for completely empty rows
    if (row.every(cell => cell.trim() === '')) {
      warnings.push(`Row ${i + 1} is completely empty`);
    }
  }

  // Check for duplicate column names
  const columnNames = data[0] || [];
  const uniqueColumns = new Set(columnNames.filter(name => name.trim() !== ''));
  if (uniqueColumns.size !== columnNames.filter(name => name.trim() !== '').length) {
    warnings.push('Duplicate column names detected');
  }

  // Check for empty column names
  columnNames.forEach((name, index) => {
    if (name.trim() === '') {
      warnings.push(`Column ${index + 1} has no name`);
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Apply a single change to CSV data
 */
export function applyChangeToCSV(
  data: string[][],
  row: number,
  column: number,
  newValue: string
): string[][] {
  if (!data || data.length === 0) {
    throw new Error('CSV data is empty');
  }

  if (row < 0 || row >= data.length) {
    throw new Error(`Row index ${row} is out of bounds`);
  }

  if (column < 0 || column >= (data[row]?.length || 0)) {
    throw new Error(`Column index ${column} is out of bounds for row ${row}`);
  }

  // Create a deep copy of the data
  const newData = data.map(r => [...r]);
  newData[row][column] = newValue;

  return newData;
}

/**
 * Apply multiple changes to CSV data
 */
export function applyChangesToCSV(
  data: string[][],
  changes: Array<{ row: number; column: number; newValue: string }>
): string[][] {
  let result = data;

  // Sort changes by row and column to ensure consistent application
  const sortedChanges = [...changes].sort((a, b) => {
    if (a.row !== b.row) return a.row - b.row;
    return a.column - b.column;
  });

  for (const change of sortedChanges) {
    result = applyChangeToCSV(result, change.row, change.column, change.newValue);
  }

  return result;
}

/**
 * Find differences between two CSV datasets
 */
export function findCSVDifferences(
  original: string[][],
  modified: string[][]
): Array<{ row: number; column: number; oldValue: string; newValue: string }> {
  const differences: Array<{ row: number; column: number; oldValue: string; newValue: string }> = [];

  const maxRows = Math.max(original.length, modified.length);

  for (let row = 0; row < maxRows; row++) {
    const originalRow = original[row] || [];
    const modifiedRow = modified[row] || [];
    const maxCols = Math.max(originalRow.length, modifiedRow.length);

    for (let col = 0; col < maxCols; col++) {
      const oldValue = originalRow[col] || '';
      const newValue = modifiedRow[col] || '';

      if (oldValue !== newValue) {
        differences.push({
          row,
          column: col,
          oldValue,
          newValue
        });
      }
    }
  }

  return differences;
}

/**
 * Get CSV statistics
 */
export function getCSVStats(data: string[][]): {
  totalRows: number;
  totalColumns: number;
  emptyRows: number;
  emptyCells: number;
  totalCells: number;
} {
  if (!data || data.length === 0) {
    return {
      totalRows: 0,
      totalColumns: 0,
      emptyRows: 0,
      emptyCells: 0,
      totalCells: 0
    };
  }

  const totalRows = data.length;
  const totalColumns = Math.max(...data.map(row => row.length));
  let emptyRows = 0;
  let emptyCells = 0;
  let totalCells = 0;

  for (const row of data) {
    const isEmptyRow = row.every(cell => cell.trim() === '');
    if (isEmptyRow) emptyRows++;

    for (const cell of row) {
      totalCells++;
      if (cell.trim() === '') emptyCells++;
    }
  }

  return {
    totalRows,
    totalColumns,
    emptyRows,
    emptyCells,
    totalCells
  };
}
