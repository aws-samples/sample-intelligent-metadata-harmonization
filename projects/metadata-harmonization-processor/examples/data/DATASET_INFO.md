# Example Metadata Dataset

This directory contains example data and schema files for testing the MetadataHarmonizationProcessor.

## example_metadata.csv

Sample patient metadata with intentional validation errors to demonstrate the processor's capabilities.

### Data Fields
- **patient_id**: Unique patient identifier (expected format: P### where ### is 3-6 digits)
- **age**: Patient age in years (expected: integer 0-150)
- **gender**: Patient gender (expected: M, F, or Other)
- **diagnosis**: Patient diagnosis (expected: Cyclospora or Other)
- **collection_date**: Sample collection date (expected: YYYY-MM-DD format)

### Validation Scenarios

| Row | Patient ID | Issue Type | Description |
|-----|------------|------------|-------------|
| 1-2 | P001, P002 | ✅ Valid | Properly formatted data |
| 3 | P003 | INVALID_PATTERN | age="invalid_age", gender="X" |
| 4 | P004 | INVALID_OPTION | gender="Male" (should be "M") |
| 5 | P005 | REQUIRED_VALUE | Missing age and diagnosis |
| 6 | INVALID_ID | INVALID_PATTERN | patient_id doesn't match P### pattern |
| 7 | P006 | INVALID_PATTERN | age=200 (out of range), diagnosis not in enum |
| 8 | P007 | INVALID_OPTION | gender="Female" (should be "F"), date format wrong |
| 9 | P008 | INVALID_OPTION | gender="m" (should be "M") |
| 10 | P009 | INVALID_OPTION | gender="f" (should be "F") |
| 11 | P010 | ✅ Valid | Properly formatted data |

### Expected AI Recommendations

When AI features are enabled, the processor should provide:

- **Semantic Recommendations** (INVALID_OPTION errors):
  - "Male" → "M"
  - "Female" → "F"
  - "m" → "M"
  - "f" → "F"

- **Pattern Recommendations** (INVALID_PATTERN errors):
  - "invalid_age" → suggest removing or replacing with valid number
  - "INVALID_ID" → suggest proper P### format
  - "2023/01/22" → "2023-01-22"

This dataset provides a comprehensive test of the validation and recommendation capabilities without requiring real patient data.
