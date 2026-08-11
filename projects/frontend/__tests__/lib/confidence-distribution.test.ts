/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import {
  calculateConfidenceDistribution,
  getConfidenceLevelFromScore,
  getConfidenceColor
} from '../../lib/transformation-operations';
import { SchemaAlignmentChangeDetail } from '../../lib/types';

describe('Confidence Distribution', () => {
  const mockChanges: SchemaAlignmentChangeDetail[] = [
    {
      changeType: 'rename',
      originalColumn: 'old_name',
      newColumn: 'new_name',
      reason: 'Test change',
      confidenceScore: 0.9,
      confidenceLevel: 'High'
    },
    {
      changeType: 'add',
      newColumn: 'added_column',
      reason: 'Test addition',
      confidenceScore: 0.7,
      confidenceLevel: 'Medium'
    },
    {
      changeType: 'remove',
      originalColumn: 'removed_column',
      reason: 'Test removal',
      confidenceScore: 0.3,
      confidenceLevel: 'Low'
    }
  ];

  describe('calculateConfidenceDistribution', () => {
    it('should calculate correct distribution for mixed confidence levels', () => {
      const distribution = calculateConfidenceDistribution(mockChanges);

      expect(distribution.high).toBe(1);
      expect(distribution.medium).toBe(1);
      expect(distribution.low).toBe(1);
      expect(distribution.averageScore).toBeCloseTo(0.63, 2);
      expect(distribution.minScore).toBe(0.3);
      expect(distribution.maxScore).toBe(0.9);
    });

    it('should handle empty changes array', () => {
      const distribution = calculateConfidenceDistribution([]);

      expect(distribution.high).toBe(0);
      expect(distribution.medium).toBe(0);
      expect(distribution.low).toBe(0);
      expect(distribution.averageScore).toBe(0);
      expect(distribution.minScore).toBe(0);
      expect(distribution.maxScore).toBe(0);
    });

    it('should handle all high confidence changes', () => {
      const highConfidenceChanges = mockChanges.map(change => ({
        ...change,
        confidenceScore: 0.9,
        confidenceLevel: 'High'
      }));

      const distribution = calculateConfidenceDistribution(highConfidenceChanges);

      expect(distribution.high).toBe(3);
      expect(distribution.medium).toBe(0);
      expect(distribution.low).toBe(0);
      expect(distribution.averageScore).toBe(0.9);
    });
  });

  describe('getConfidenceLevelFromScore', () => {
    it('should return correct confidence levels', () => {
      expect(getConfidenceLevelFromScore(0.9)).toBe('High');
      expect(getConfidenceLevelFromScore(0.8)).toBe('High');
      expect(getConfidenceLevelFromScore(0.7)).toBe('Medium');
      expect(getConfidenceLevelFromScore(0.5)).toBe('Medium');
      expect(getConfidenceLevelFromScore(0.4)).toBe('Low');
      expect(getConfidenceLevelFromScore(0.0)).toBe('Low');
    });
  });

  describe('getConfidenceColor', () => {
    it('should return correct colors for confidence levels', () => {
      expect(getConfidenceColor('High')).toBe('#4caf50');
      expect(getConfidenceColor('Medium')).toBe('#ff9800');
      expect(getConfidenceColor('Low')).toBe('#f44336');
      expect(getConfidenceColor('Unknown')).toBe('#757575');
    });
  });
});
