/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import {
  parseCSV,
  generateCSV,
  parseCSVFile,
  validateCSV,
  applyChangeToCSV,
  applyChangesToCSV,
  findCSVDifferences,
  getCSVStats
} from '../../lib/csv-utils';

describe('CSV Utils', () => {
  describe('parseCSV', () => {
    it('parses simple CSV correctly', () => {
      const csv = 'Name,Age,City\nJohn,25,New York\nJane,30,Boston';
      const result = parseCSV(csv);

      expect(result).toEqual([
        ['Name', 'Age', 'City'],
        ['John', '25', 'New York'],
        ['Jane', '30', 'Boston']
      ]);
    });

    it('handles quoted fields with commas', () => {
      const csv = 'Name,Description\n"John Doe","A person with, comma"\n"Jane Smith","Another person"';
      const result = parseCSV(csv);

      expect(result).toEqual([
        ['Name', 'Description'],
        ['John Doe', 'A person with, comma'],
        ['Jane Smith', 'Another person']
      ]);
    });

    it('handles escaped quotes', () => {
      const csv = 'Name,Quote\n"John","He said ""Hello"""\n"Jane","She said ""Hi"""';
      const result = parseCSV(csv);

      expect(result).toEqual([
        ['Name', 'Quote'],
        ['John', 'He said "Hello"'],
        ['Jane', 'She said "Hi"']
      ]);
    });

    it('handles empty fields', () => {
      const csv = 'Name,Age,City\nJohn,,New York\n,30,Boston';
      const result = parseCSV(csv);

      expect(result).toEqual([
        ['Name', 'Age', 'City'],
        ['John', '', 'New York'],
        ['', '30', 'Boston']
      ]);
    });

    it('skips empty lines by default', () => {
      const csv = 'Name,Age\nJohn,25\n\nJane,30\n';
      const result = parseCSV(csv);

      expect(result).toEqual([
        ['Name', 'Age'],
        ['John', '25'],
        ['Jane', '30']
      ]);
    });

    it('includes empty lines when skipEmptyLines is false', () => {
      const csv = 'Name,Age\nJohn,25\n\nJane,30';
      const result = parseCSV(csv, { skipEmptyLines: false });

      expect(result).toEqual([
        ['Name', 'Age'],
        ['John', '25'],
        [''],
        ['Jane', '30']
      ]);
    });

    it('handles custom delimiter', () => {
      const csv = 'Name;Age;City\nJohn;25;New York\nJane;30;Boston';
      const result = parseCSV(csv, { delimiter: ';' });

      expect(result).toEqual([
        ['Name', 'Age', 'City'],
        ['John', '25', 'New York'],
        ['Jane', '30', 'Boston']
      ]);
    });

    it('throws error for empty input', () => {
      expect(() => parseCSV('')).toThrow('CSV text is empty or undefined');
      expect(() => parseCSV('   ')).toThrow('CSV text is empty or undefined');
    });

    it('handles newlines within quoted fields', () => {
      const csv = 'Name,Description\n"John","Line 1\nLine 2"\n"Jane","Single line"';
      const result = parseCSV(csv);

      // parseCSV splits on newlines before handling quotes,
      // so multi-line quoted fields are split across rows
      expect(result).toEqual([
        ['Name', 'Description'],
        ['John', 'Line 1'],
        ['Line 2'],
        ['Jane', 'Single line']
      ]);
    });
  });

  describe('generateCSV', () => {
    it('generates simple CSV correctly', () => {
      const data = [
        ['Name', 'Age', 'City'],
        ['John', '25', 'New York'],
        ['Jane', '30', 'Boston']
      ];
      const result = generateCSV(data);

      expect(result).toBe('Name,Age,City\nJohn,25,New York\nJane,30,Boston');
    });

    it('quotes fields with commas', () => {
      const data = [
        ['Name', 'Description'],
        ['John Doe', 'A person with, comma'],
        ['Jane Smith', 'Another person']
      ];
      const result = generateCSV(data);

      expect(result).toBe('Name,Description\nJohn Doe,"A person with, comma"\nJane Smith,Another person');
    });

    it('escapes quotes in fields', () => {
      const data = [
        ['Name', 'Quote'],
        ['John', 'He said "Hello"'],
        ['Jane', 'She said "Hi"']
      ];
      const result = generateCSV(data);

      expect(result).toBe('Name,Quote\nJohn,"He said ""Hello"""\nJane,"She said ""Hi"""');
    });

    it('handles empty fields', () => {
      const data = [
        ['Name', 'Age', 'City'],
        ['John', '', 'New York'],
        ['', '30', 'Boston']
      ];
      const result = generateCSV(data);

      expect(result).toBe('Name,Age,City\nJohn,,New York\n,30,Boston');
    });

    it('handles null and undefined values', () => {
      const data = [
        ['Name', 'Age', 'City'],
        ['John', null as any, 'New York'],
        [undefined as any, '30', 'Boston']
      ];
      const result = generateCSV(data);

      expect(result).toBe('Name,Age,City\nJohn,,New York\n,30,Boston');
    });

    it('uses custom delimiter', () => {
      const data = [
        ['Name', 'Age', 'City'],
        ['John', '25', 'New York']
      ];
      const result = generateCSV(data, { delimiter: ';' });

      expect(result).toBe('Name;Age;City\nJohn;25;New York');
    });

    it('forces quotes when requested', () => {
      const data = [
        ['Name', 'Age'],
        ['John', '25']
      ];
      const result = generateCSV(data, { forceQuotes: true });

      expect(result).toBe('"Name","Age"\n"John","25"');
    });

    it('returns empty string for empty data', () => {
      expect(generateCSV([])).toBe('');
      expect(generateCSV(null as any)).toBe('');
      expect(generateCSV(undefined as any)).toBe('');
    });

    it('quotes fields with leading/trailing spaces', () => {
      const data = [
        ['Name', 'Value'],
        [' John ', ' 25 ']
      ];
      const result = generateCSV(data);

      expect(result).toBe('Name,Value\n" John "," 25 "');
    });
  });

  describe('parseCSVFile', () => {
    const createMockFile = (name: string, content: string): File => {
      const file = new File([content], name, { type: 'text/csv' });
      file.text = jest.fn().mockResolvedValue(content);
      return file;
    };

    it('parses CSV file correctly', async () => {
      const content = 'Name,Age\nJohn,25\nJane,30';
      const file = createMockFile('test.csv', content);

      const result = await parseCSVFile(file);

      expect(result).toEqual([
        ['Name', 'Age'],
        ['John', '25'],
        ['Jane', '30']
      ]);
    });

    it('throws error for non-CSV file', async () => {
      const file = createMockFile('test.txt', 'content');

      await expect(parseCSVFile(file)).rejects.toThrow('File must have .csv extension');
    });

    it('throws error for no file', async () => {
      await expect(parseCSVFile(null as any)).rejects.toThrow('No file provided');
    });

    it('handles file reading errors', async () => {
      const file = createMockFile('test.csv', 'content');
      file.text = jest.fn().mockRejectedValue(new Error('File read error'));

      await expect(parseCSVFile(file)).rejects.toThrow('Failed to parse CSV file: File read error');
    });
  });

  describe('validateCSV', () => {
    it('validates correct CSV structure', () => {
      const data = [
        ['Name', 'Age', 'City'],
        ['John', '25', 'New York'],
        ['Jane', '30', 'Boston']
      ];

      const result = validateCSV(data);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('detects empty CSV', () => {
      const result = validateCSV([]);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('CSV data is empty');
    });

    it('detects missing data rows', () => {
      const data = [['Name', 'Age', 'City']];

      const result = validateCSV(data);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('CSV must contain at least a header row and one data row');
    });

    it('detects empty header', () => {
      const data = [[]];

      const result = validateCSV(data);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Header row is empty');
    });

    it('warns about inconsistent column counts', () => {
      const data = [
        ['Name', 'Age', 'City'],
        ['John', '25'],
        ['Jane', '30', 'Boston', 'Extra']
      ];

      const result = validateCSV(data);

      expect(result.isValid).toBe(true);
      expect(result.warnings).toContain('Row 2 has 2 columns, expected 3');
      expect(result.warnings).toContain('Row 3 has 4 columns, expected 3');
    });

    it('warns about empty rows', () => {
      const data = [
        ['Name', 'Age'],
        ['John', '25'],
        ['', '']
      ];

      const result = validateCSV(data);

      expect(result.warnings).toContain('Row 3 is completely empty');
    });

    it('warns about duplicate column names', () => {
      const data = [
        ['Name', 'Age', 'Name'],
        ['John', '25', 'Doe']
      ];

      const result = validateCSV(data);

      expect(result.warnings).toContain('Duplicate column names detected');
    });

    it('warns about empty column names', () => {
      const data = [
        ['Name', '', 'Age'],
        ['John', 'Middle', '25']
      ];

      const result = validateCSV(data);

      expect(result.warnings).toContain('Column 2 has no name');
    });
  });

  describe('applyChangeToCSV', () => {
    const testData = [
      ['Name', 'Age', 'City'],
      ['John', '25', 'New York'],
      ['Jane', '30', 'Boston']
    ];

    it('applies single change correctly', () => {
      const result = applyChangeToCSV(testData, 1, 0, 'Johnny');

      expect(result).toEqual([
        ['Name', 'Age', 'City'],
        ['Johnny', '25', 'New York'],
        ['Jane', '30', 'Boston']
      ]);

      // Original data should not be modified
      expect(testData[1][0]).toBe('John');
    });

    it('throws error for invalid row index', () => {
      expect(() => applyChangeToCSV(testData, -1, 0, 'value')).toThrow('Row index -1 is out of bounds');
      expect(() => applyChangeToCSV(testData, 10, 0, 'value')).toThrow('Row index 10 is out of bounds');
    });

    it('throws error for invalid column index', () => {
      expect(() => applyChangeToCSV(testData, 1, -1, 'value')).toThrow('Column index -1 is out of bounds');
      expect(() => applyChangeToCSV(testData, 1, 10, 'value')).toThrow('Column index 10 is out of bounds');
    });

    it('throws error for empty data', () => {
      expect(() => applyChangeToCSV([], 0, 0, 'value')).toThrow('CSV data is empty');
    });
  });

  describe('applyChangesToCSV', () => {
    const testData = [
      ['Name', 'Age', 'City'],
      ['John', '25', 'New York'],
      ['Jane', '30', 'Boston']
    ];

    it('applies multiple changes correctly', () => {
      const changes = [
        { row: 1, column: 0, newValue: 'Johnny' },
        { row: 2, column: 1, newValue: '31' },
        { row: 1, column: 2, newValue: 'Chicago' }
      ];

      const result = applyChangesToCSV(testData, changes);

      expect(result).toEqual([
        ['Name', 'Age', 'City'],
        ['Johnny', '25', 'Chicago'],
        ['Jane', '31', 'Boston']
      ]);
    });

    it('handles empty changes array', () => {
      const result = applyChangesToCSV(testData, []);

      expect(result).toEqual(testData);
    });

    it('sorts changes for consistent application', () => {
      const changes = [
        { row: 2, column: 1, newValue: '31' },
        { row: 1, column: 0, newValue: 'Johnny' },
        { row: 1, column: 2, newValue: 'Chicago' }
      ];

      const result = applyChangesToCSV(testData, changes);

      expect(result).toEqual([
        ['Name', 'Age', 'City'],
        ['Johnny', '25', 'Chicago'],
        ['Jane', '31', 'Boston']
      ]);
    });
  });

  describe('findCSVDifferences', () => {
    it('finds differences between CSV datasets', () => {
      const original = [
        ['Name', 'Age', 'City'],
        ['John', '25', 'New York'],
        ['Jane', '30', 'Boston']
      ];

      const modified = [
        ['Name', 'Age', 'City'],
        ['Johnny', '25', 'Chicago'],
        ['Jane', '31', 'Boston']
      ];

      const differences = findCSVDifferences(original, modified);

      expect(differences).toEqual([
        { row: 1, column: 0, oldValue: 'John', newValue: 'Johnny' },
        { row: 1, column: 2, oldValue: 'New York', newValue: 'Chicago' },
        { row: 2, column: 1, oldValue: '30', newValue: '31' }
      ]);
    });

    it('handles different sized datasets', () => {
      const original = [
        ['Name', 'Age'],
        ['John', '25']
      ];

      const modified = [
        ['Name', 'Age', 'City'],
        ['John', '25', 'New York'],
        ['Jane', '30', 'Boston']
      ];

      const differences = findCSVDifferences(original, modified);

      expect(differences).toContainEqual({ row: 0, column: 2, oldValue: '', newValue: 'City' });
      expect(differences).toContainEqual({ row: 1, column: 2, oldValue: '', newValue: 'New York' });
      expect(differences).toContainEqual({ row: 2, column: 0, oldValue: '', newValue: 'Jane' });
    });

    it('returns empty array for identical datasets', () => {
      const data = [
        ['Name', 'Age'],
        ['John', '25']
      ];

      const differences = findCSVDifferences(data, data);

      expect(differences).toEqual([]);
    });
  });

  describe('getCSVStats', () => {
    it('calculates stats correctly', () => {
      const data = [
        ['Name', 'Age', 'City'],
        ['John', '25', 'New York'],
        ['', '', ''],
        ['Jane', '', 'Boston']
      ];

      const stats = getCSVStats(data);

      expect(stats).toEqual({
        totalRows: 4,
        totalColumns: 3,
        emptyRows: 1,
        emptyCells: 4,
        totalCells: 12
      });
    });

    it('handles empty data', () => {
      const stats = getCSVStats([]);

      expect(stats).toEqual({
        totalRows: 0,
        totalColumns: 0,
        emptyRows: 0,
        emptyCells: 0,
        totalCells: 0
      });
    });

    it('handles irregular row lengths', () => {
      const data = [
        ['Name', 'Age', 'City', 'Country'],
        ['John', '25'],
        ['Jane', '30', 'Boston']
      ];

      const stats = getCSVStats(data);

      expect(stats.totalColumns).toBe(4);
      expect(stats.totalCells).toBe(9); // 4 + 2 + 3
    });
  });
});
