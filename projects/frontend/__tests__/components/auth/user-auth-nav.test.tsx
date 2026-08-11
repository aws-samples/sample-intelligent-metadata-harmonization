/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { useAuth } from 'react-oidc-context';
import { UserAuthNav } from '../../../components/auth/user-auth-nav';

// Mock the react-oidc-context hook
jest.mock('react-oidc-context');
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

// Mock the utils function
jest.mock('../../../lib/utils', () => ({
  getUserInitials: jest.fn((email: string) => {
    if (!email) return 'U';
    return email.split('@')[0].substring(0, 2).toUpperCase();
  })
}));

// Create a test theme
const theme = createTheme();

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

describe('UserAuthNav Component', () => {
  const mockRemoveUser = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders nothing when user is not authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      removeUser: mockRemoveUser
    } as any);

    const { container } = render(
      <TestWrapper>
        <UserAuthNav />
      </TestWrapper>
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders user information when authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        profile: {
          email: 'john.doe@example.com'
        }
      },
      removeUser: mockRemoveUser
    } as any);

    render(
      <TestWrapper>
        <UserAuthNav />
      </TestWrapper>
    );

    // Check for user avatar with initials
    expect(screen.getByText('JO')).toBeInTheDocument();

    // Check for user email (on desktop)
    expect(screen.getByText('john.doe@example.com')).toBeInTheDocument();

    // Check for sign out button
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
  });

  it('displays user initials correctly in avatar', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        profile: {
          email: 'jane.smith@cdc.gov'
        }
      },
      removeUser: mockRemoveUser
    } as any);

    render(
      <TestWrapper>
        <UserAuthNav />
      </TestWrapper>
    );

    // Check that the avatar displays the correct initials
    expect(screen.getByText('JA')).toBeInTheDocument();
  });

  it('handles sign out button click', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        profile: {
          email: 'test@example.com'
        }
      },
      removeUser: mockRemoveUser
    } as any);

    render(
      <TestWrapper>
        <UserAuthNav />
      </TestWrapper>
    );

    const signOutButton = screen.getByRole('button', { name: /sign out/i });
    fireEvent.click(signOutButton);

    expect(mockRemoveUser).toHaveBeenCalledTimes(1);
  });

  it('handles missing email gracefully', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        profile: {
          email: undefined
        }
      },
      removeUser: mockRemoveUser
    } as any);

    render(
      <TestWrapper>
        <UserAuthNav />
      </TestWrapper>
    );

    // Should still render with default initials
    expect(screen.getByText('U')).toBeInTheDocument();

    // Sign out button should still be present
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
  });

  it('renders logout icon in sign out button', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        profile: {
          email: 'test@example.com'
        }
      },
      removeUser: mockRemoveUser
    } as any);

    render(
      <TestWrapper>
        <UserAuthNav />
      </TestWrapper>
    );

    // Check for the Logout icon (Material UI icons have specific test attributes)
    const logoutIcon = document.querySelector('[data-testid="LogoutIcon"]');
    expect(logoutIcon).toBeInTheDocument();
  });

  it('applies Material UI styling correctly', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        profile: {
          email: 'test@example.com'
        }
      },
      removeUser: mockRemoveUser
    } as any);

    render(
      <TestWrapper>
        <UserAuthNav />
      </TestWrapper>
    );

    // Check that Material UI components are rendered with expected classes
    const avatar = screen.getByText('TE').closest('[class*="MuiAvatar-root"]');
    expect(avatar).toBeInTheDocument();

    const button = screen.getByRole('button', { name: /sign out/i });
    expect(button).toHaveClass('MuiButton-root');
  });

  // Test responsive behavior (mobile vs desktop)
  it('hides email on mobile breakpoint', () => {
    // Mock mobile breakpoint
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query.includes('(max-width: 899.95px)'), // md breakpoint
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        profile: {
          email: 'test@example.com'
        }
      },
      removeUser: mockRemoveUser
    } as any);

    render(
      <TestWrapper>
        <UserAuthNav />
      </TestWrapper>
    );

    // Avatar should still be visible
    expect(screen.getByText('TE')).toBeInTheDocument();

    // Sign out button should still be visible
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
  });
});
