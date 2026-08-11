/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// UI helpers.

/**
 * Material UI responsive breakpoint helpers
 */
export const breakpoints = {
  xs: 0,
  sm: 600,
  md: 900,
  lg: 1200,
  xl: 1536,
} as const;

/**
 * Common Material UI sx prop patterns for consistent styling
 */
export const commonStyles = {
  // Centered content container
  centeredContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
  },

  // Full height flex column
  fullHeightColumn: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100vh',
  },

  // Card with consistent shadow and border radius
  elevatedCard: {
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
    borderRadius: 2,
  },

  // Loading state container
  loadingContainer: {
    textAlign: 'center',
    py: 4,
  },
} as const;

/**
 * Helper function to create consistent spacing values
 * @param multiplier - Spacing multiplier (1 = 8px in Material UI)
 * @returns Spacing value for sx prop
 */
export function spacing(multiplier: number): number {
  return multiplier * 8;
}
