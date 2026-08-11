/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Metadata validation API models and interfaces

// Request Models (camelCase for frontend)
export interface ValidationCreateRequest {
  coreSchemaId: string;
  programSchemaId: string;
}

// File upload data interface for handling file uploads
export interface FileUploadData {
  file: File;
  validationRequest?: ValidationCreateRequest;
}
