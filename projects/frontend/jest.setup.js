/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import '@testing-library/jest-dom'

// Mock react-oidc-context globally to prevent useAuth errors
jest.mock('react-oidc-context', () => ({
  useAuth: jest.fn(() => ({
    user: { id_token: 'mock-token' },
    isAuthenticated: true,
    isLoading: false,
  })),
}))
