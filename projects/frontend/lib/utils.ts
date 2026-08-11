/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Utils.

/**
 * Extracts user initials from an email address
 * @param email - User email address
 * @returns Two-character uppercase initials
 */
export function getUserInitials(email: string): string {
  if (!email) return "U";
  return email.split("@")[0].substring(0, 2).toUpperCase();
}

import {
  SchemaAlignmentChange,
  SchemaAlignmentChangeType,
  SchemaAlignmentChangeDetail
} from './types';

/**
 * Generates schema alignment change objects from detailed change information
 * @param changeDetails - Array of detailed schema alignment changes from API
 * @returns Array of schema alignment changes for user review
 */
export function generateSchemaAlignmentChangesFromDetails(
  changeDetails: SchemaAlignmentChangeDetail[]
): SchemaAlignmentChange[] {
  const changes: SchemaAlignmentChange[] = [];

  changeDetails.forEach((detail, index) => {
    let change: SchemaAlignmentChange;

    switch (detail.changeType) {
      case 'rename':
        change = {
          id: `rename-${detail.originalColumn}-${detail.newColumn}-${index}`,
          type: SchemaAlignmentChangeType.COLUMN_RENAMED,
          originalColumn: detail.originalColumn,
          alignedColumn: detail.newColumn,
          description: `Column "${detail.originalColumn}" was renamed to "${detail.newColumn}" to match the target schema`,
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
          description: `Column "${detail.newColumn}" was added to match the target schema requirements`,
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
          description: `Column "${detail.originalColumn}" was removed as it's not part of the target schema`,
          reason: detail.reason || 'Not required by target schema',
          canRevert: true,
          isAccepted: false
        };
        break;

      default:
        // Skip unknown change types
        return;
    }

    changes.push(change);
  });

  return changes;
}
