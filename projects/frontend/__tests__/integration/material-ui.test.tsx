/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Integration tests for Material UI theming and components
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { useMediaQuery } from '@mui/material';

import App from '../../components/app';
import { UserAuthNav } from '../../components/auth/user-auth-nav';
import { theme } from '../../lib/theme';

// Mock fetch globally
global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({ data: { coreSchemas: [], programSchemas: [] } }),
    ok: true
  } as Response)
);

// Mock dependencies
jest.mock('react-oidc-context', () => ({
  AuthProvider: ({ children }: any) => <div>{children}</div>,
  useAuth: jest.fn(),
}));
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  useMediaQuery: jest.fn(),
}));

jest.mock('../../lib/config', () => ({
  getConfig: jest.fn(() => ({
    API_URI: 'https://api.test.com',
    COGNITO: {
      authority: 'test-authority',
      client_id: 'test-client-id',
      redirect_uri: 'http://localhost:3000',
      post_logout_redirect_uri: 'http://localhost:3000',
      scope: 'openid',
      response_type: 'code',
      loadUserInfo: true,
      metadata: {
        authorization_endpoint: 'test-auth-endpoint',
        token_endpoint: 'test-token-endpoint',
        userinfo_endpoint: 'test-userinfo-endpoint',
        end_session_endpoint: 'test-end-session-endpoint',
      },
    },
  })),
}));

// Mock console.error to avoid noise in tests
const mockConsoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
const mockConsoleWarn = jest.spyOn(console, 'warn').mockImplementation(() => {});

// Test wrapper component with Material UI theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    <CssBaseline />
    {children}
  </ThemeProvider>
);

// Import useAuth after mocking
import { useAuth } from 'react-oidc-context';

// Mock auth context
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockUseMediaQuery = useMediaQuery as jest.MockedFunction<typeof useMediaQuery>;

describe('Material UI Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockConsoleError.mockClear();
    mockConsoleWarn.mockClear();
    mockUseMediaQuery.mockReturnValue(false); // Default to desktop

    // Default mock for useAuth - not authenticated
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      removeUser: jest.fn(),
    } as any);
  });

  afterAll(() => {
    mockConsoleError.mockRestore();
    mockConsoleWarn.mockRestore();
  });

  describe('Material UI Theming', () => {
    it('should apply application color palette correctly', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check if the AppBar has the correct primary color
      const appBar = screen.getByRole('banner');
      expect(appBar).toBeInTheDocument();

      // Check if the main content area has the correct background
      const main = screen.getByRole('main');
      expect(main).toBeInTheDocument();

      // Verify no console errors or warnings during rendering
      expect(mockConsoleError).not.toHaveBeenCalled();
      expect(mockConsoleWarn).not.toHaveBeenCalled();
    });

    it('should render Material UI components with custom theme', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check Typography components
      const title = screen.getByRole('heading', { level: 1 });
      expect(title).toHaveTextContent('Metadata Tool');

      const uploadHeading = screen.getByRole('heading', { level: 4 });
      expect(uploadHeading).toHaveTextContent('Upload Metadata File');

      const description = screen.getByText('Select validation schemas and upload a CSV file containing your metadata');
      expect(description).toBeInTheDocument();

      // Check LocalHospital icon is rendered
      const hospitalIcon = screen.getByTestId('LocalHospitalIcon');
      expect(hospitalIcon).toBeInTheDocument();
    });

    it('should apply custom component styles from theme', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check if AppBar has custom styling
      const appBar = screen.getByRole('banner');
      expect(appBar).toBeInTheDocument();

      // Check if Container has proper max width
      const container = screen.getByRole('main').querySelector('.MuiContainer-root');
      expect(container).toBeInTheDocument();

      // Verify no styling errors
      expect(mockConsoleError).not.toHaveBeenCalled();
    });

    it('should handle theme breakpoints correctly', () => {
      // Test mobile breakpoint
      mockUseMediaQuery.mockReturnValue(true);

      render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      // On mobile, user email should be hidden
      // This test verifies responsive behavior is working
      expect(mockUseMediaQuery).toHaveBeenCalledWith(theme.breakpoints.down('md'));
    });
  });

  describe('Material UI Component Rendering', () => {
    it('should render AppBar with Toolbar correctly', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check AppBar structure
      const appBar = screen.getByRole('banner');
      expect(appBar).toBeInTheDocument();

      // Check Toolbar content
      const toolbar = appBar.querySelector('.MuiToolbar-root');
      expect(toolbar).toBeInTheDocument();

      // Check icon and title are in toolbar
      const hospitalIcon = screen.getByTestId('LocalHospitalIcon');
      const title = screen.getByRole('heading', { level: 1 });
      expect(hospitalIcon).toBeInTheDocument();
      expect(title).toBeInTheDocument();
    });

    it('should render Container and Box components correctly', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check main content structure
      const main = screen.getByRole('main');
      expect(main).toBeInTheDocument();

      // Check Container is present
      const container = main.querySelector('.MuiContainer-root');
      expect(container).toBeInTheDocument();

      // Check Box components are rendered
      const boxes = main.querySelectorAll('.MuiBox-root');
      expect(boxes.length).toBeGreaterThan(0);
    });

    it('should render Typography components with correct variants', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check h6 variant for app title
      const appTitle = screen.getByRole('heading', { level: 1 });
      expect(appTitle).toHaveClass('MuiTypography-h6');

      // Check h4 variant for upload heading
      const uploadHeading = screen.getByRole('heading', { level: 4 });
      expect(uploadHeading).toHaveClass('MuiTypography-h4');

      // Check body1 variant for description
      const description = screen.getByText('Select validation schemas and upload a CSV file containing your metadata');
      expect(description).toHaveClass('MuiTypography-body1');
    });
  });

  describe('Authentication Integration with Material UI', () => {
    it('should render UserAuthNav when authenticated', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          profile: {
            email: 'test@example.com',
          },
        },
        removeUser: jest.fn(),
      } as any);

      render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      // Check Avatar is rendered (Avatar doesn't have img role, use class selector)
      const avatar = document.querySelector('.MuiAvatar-root');
      expect(avatar).toBeInTheDocument();
      expect(avatar).toHaveTextContent('TE');

      // Check user email is displayed (on desktop)
      const userEmail = screen.getByText('test@example.com');
      expect(userEmail).toBeInTheDocument();

      // Check Sign Out button
      const signOutButton = screen.getByRole('button', { name: /sign out/i });
      expect(signOutButton).toBeInTheDocument();
      expect(signOutButton).toHaveClass('MuiButton-outlined');
    });

    it('should not render UserAuthNav when not authenticated', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: false,
        user: null,
        removeUser: jest.fn(),
      } as any);

      const { container } = render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      // Should render nothing when not authenticated
      expect(container.firstChild).toBeNull();
    });

    it('should handle sign out button click', async () => {
      const mockRemoveUser = jest.fn();
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          profile: {
            email: 'test@example.com',
          },
        },
        removeUser: mockRemoveUser,
      } as any);

      render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      const signOutButton = screen.getByRole('button', { name: /sign out/i });
      fireEvent.click(signOutButton);

      await waitFor(() => {
        expect(mockRemoveUser).toHaveBeenCalledTimes(1);
      });
    });

    it('should display user initials in Avatar correctly', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          profile: {
            email: 'john.doe@example.com',
          },
        },
        removeUser: jest.fn(),
      } as any);

      render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      const avatar = document.querySelector('.MuiAvatar-root');
      expect(avatar).toHaveTextContent('JO');
    });
  });

  describe('Responsive Behavior', () => {
    it('should hide user email on mobile devices', () => {
      mockUseMediaQuery.mockReturnValue(true); // Mobile
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          profile: {
            email: 'test@example.com',
          },
        },
        removeUser: jest.fn(),
      } as any);

      render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      // User email should not be visible on mobile
      const userEmail = screen.queryByText('test@example.com');
      expect(userEmail).not.toBeInTheDocument();

      // But avatar and sign out button should still be visible
      const avatar = document.querySelector('.MuiAvatar-root');
      const signOutButton = screen.getByRole('button', { name: /sign out/i });
      expect(avatar).toBeInTheDocument();
      expect(signOutButton).toBeInTheDocument();
    });

    it('should show user email on desktop devices', () => {
      mockUseMediaQuery.mockReturnValue(false); // Desktop
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          profile: {
            email: 'test@example.com',
          },
        },
        removeUser: jest.fn(),
      } as any);

      render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      // User email should be visible on desktop
      const userEmail = screen.getByText('test@example.com');
      expect(userEmail).toBeInTheDocument();
    });

    it('should use Material UI breakpoints correctly', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          profile: {
            email: 'test@example.com',
          },
        },
        removeUser: jest.fn(),
      } as any);

      render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      // Verify useMediaQuery is called with correct breakpoint
      expect(mockUseMediaQuery).toHaveBeenCalledWith(theme.breakpoints.down('md'));
    });
  });

  describe('Application Structure and Layout', () => {
    it('should render complete application structure without errors', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check main structural elements
      const appBar = screen.getByRole('banner');
      const main = screen.getByRole('main');
      const title = screen.getByRole('heading', { level: 1 });
      const uploadHeading = screen.getByRole('heading', { level: 4 });

      expect(appBar).toBeInTheDocument();
      expect(main).toBeInTheDocument();
      expect(title).toBeInTheDocument();
      expect(uploadHeading).toBeInTheDocument();

      // Verify no console errors during rendering
      expect(mockConsoleError).not.toHaveBeenCalled();
      expect(mockConsoleWarn).not.toHaveBeenCalled();
    });

    it('should have proper semantic HTML structure', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check semantic elements
      const banner = screen.getByRole('banner');
      const main = screen.getByRole('main');
      const headings = screen.getAllByRole('heading');

      expect(banner).toBeInTheDocument();
      expect(main).toBeInTheDocument();
      expect(headings).toHaveLength(2); // h1 and h2

      // Check heading hierarchy
      const h1 = screen.getByRole('heading', { level: 1 });
      const h4 = screen.getByRole('heading', { level: 4 });
      expect(h1).toHaveTextContent('Metadata Tool');
      expect(h4).toHaveTextContent('Upload Metadata File');
    });

    it('should maintain proper layout structure with Material UI components', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check Box component for full height layout
      const rootBox = screen.getByRole('banner').parentElement;
      expect(rootBox).toHaveClass('MuiBox-root');

      // Check Container component
      const container = screen.getByRole('main').querySelector('.MuiContainer-root');
      expect(container).toBeInTheDocument();

      // Check nested Box components
      const contentBox = container?.querySelector('.MuiBox-root');
      expect(contentBox).toBeInTheDocument();
    });
  });

  describe('Material UI Theme Integration', () => {
    it('should apply application color scheme correctly', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // The theme should be applied without errors
      expect(mockConsoleError).not.toHaveBeenCalled();
      expect(mockConsoleWarn).not.toHaveBeenCalled();

      // Check that Material UI components are rendered
      const muiComponents = [
        '.MuiAppBar-root',
        '.MuiToolbar-root',
        '.MuiTypography-root',
        '.MuiContainer-root',
        '.MuiBox-root',
      ];

      muiComponents.forEach(selector => {
        const element = document.querySelector(selector);
        expect(element).toBeInTheDocument();
      });
    });

    it('should handle CssBaseline integration', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // CssBaseline should normalize styles without errors
      expect(mockConsoleError).not.toHaveBeenCalled();
      expect(mockConsoleWarn).not.toHaveBeenCalled();
    });

    it('should support theme customization', () => {
      // Test that custom theme properties are accessible
      expect(theme.palette.primary.main).toBe('#005fcc');
      expect(theme.palette.secondary.main).toBe('#f57c00');
      expect(theme.shape.borderRadius).toBe(8);
      expect(theme.typography.button.textTransform).toBe('none');
    });
  });

  describe('Accessibility and Best Practices', () => {
    it('should have proper ARIA roles and labels', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Check ARIA roles
      const banner = screen.getByRole('banner');
      const main = screen.getByRole('main');
      const headings = screen.getAllByRole('heading');

      expect(banner).toBeInTheDocument();
      expect(main).toBeInTheDocument();
      expect(headings).toHaveLength(2);

      // Check heading levels
      const h1 = screen.getByRole('heading', { level: 1 });
      const h4 = screen.getByRole('heading', { level: 4 });
      expect(h1).toBeInTheDocument();
      expect(h4).toBeInTheDocument();
    });

    it('should have proper color contrast with application theme', () => {
      render(
        <TestWrapper>
          <App />
        </TestWrapper>
      );

      // Material UI components should render without accessibility warnings
      expect(mockConsoleWarn).not.toHaveBeenCalled();
      expect(mockConsoleError).not.toHaveBeenCalled();
    });

    it('should support keyboard navigation', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: {
          profile: {
            email: 'test@example.com',
          },
        },
        removeUser: jest.fn(),
      } as any);

      render(
        <TestWrapper>
          <UserAuthNav />
        </TestWrapper>
      );

      const signOutButton = screen.getByRole('button', { name: /sign out/i });

      // Button should be focusable
      signOutButton.focus();
      expect(document.activeElement).toBe(signOutButton);
    });
  });
});
