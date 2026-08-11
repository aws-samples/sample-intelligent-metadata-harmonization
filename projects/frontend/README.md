# Frontend - Metadata Validation Web Interface

Interactive web application for uploading, validating, and managing CSV metadata files with AI-powered schema alignment and real-time error correction.

## Quick Start

Prerequisites: API must be running locally (see ../api/README.md)

```bash
npm install
cp .env.example .env.local
npm run dev
```

Local Development: http://localhost:3000

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Next.js 15 with App Router |
| UI Library | Material UI v6 |
| Authentication | React OIDC Context (AWS Cognito) |
| Language | TypeScript |
| Testing | Jest, React Testing Library |
| Linting | ESLint |

## Core Features

- Upload CSV files with schema selection
- Interactive spreadsheet editing with validation
- AI-powered schema alignment and error correction
- Manual data structure management (add/remove/rename columns/rows)
- Change tracking and audit trails
- Bulk operations and transformations

## Configuration

### Environment Variables (.env.local)

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080  # API server URL
NEXT_PUBLIC_AUTH_DOMAIN=your-cognito-domain     # AWS Cognito domain
NEXT_PUBLIC_CLIENT_ID=your-cognito-client-id    # Cognito client ID
```

### Running API and Frontend

```bash
# Terminal 1 - Start API first
cd ../api && python -m uvicorn src.metadata_harmonization_api.main:app --reload

# Terminal 2 - Start frontend
cd ../frontend && npm run dev
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm test` | Run test suite |
| `npm run test:watch` | Run tests in watch mode |
| `npm run test:coverage` | Run tests with coverage report |

## Project Structure

```
projects/frontend/
├── app/                    # Next.js App Router pages
├── components/            # React components
│   ├── auth/             # Authentication components
│   ├── metadata/         # Metadata validation components
│   └── app.tsx           # Main application component
├── lib/                  # Utility libraries
│   ├── api.ts           # API client
│   ├── csv-utils.ts     # CSV utilities
│   ├── utils.ts         # Schema alignment utilities
│   ├── theme.ts         # Material UI theme
│   └── types.ts         # TypeScript types
├── __tests__/           # Test files
├── styles/              # Global styles
└── public/              # Static assets
```

## Key User-Modifiable Components

| Path | Purpose |
|------|---------|
| `components/metadata/` | Core validation interface components |
| `lib/api.ts` | API client configuration and endpoints |
| `lib/theme.ts` | UI theme and branding customization |
| `.env.local` | Environment configuration |

## Main Components

### MetadataEditor
Main editing interface with 70/30 layout:
- Spreadsheet area for interactive data editing
- Validation sidebar with error management
- Manual schema change management
- Change tracking and audit trails

### SpreadsheetEditor
Interactive spreadsheet with:
- Excel-like functionality
- Column/row selection and management
- Context menus for operations
- Undo/redo support (Ctrl+Z, Ctrl+Y)
- Keyboard shortcuts (F2 rename, Ctrl+Shift+C add column, etc.)
- Drag-and-drop support

### ValidationSidebar
Tabbed sidebar featuring:
- Job ID display and tracking
- Submit button for validation
- Real-time status updates
- Validation errors tab with correction tools
- Schema changes tab for alignment management

## Authentication

Uses React OIDC Context with AWS Cognito:
- Provider configured in `app/layout.tsx`
- `AuthWrapper` component handles authentication state
- `UserAuthNav` component provides login/logout functionality
- Bearer token authentication for API requests

## API Integration

Frontend communicates with the metadata harmonization API through:
- `lib/api.ts` - API client with camelCase response parsing
- `lib/error-handling.ts` - Centralized error management
- `lib/types.ts` - TypeScript interfaces for API responses
- Automatic token management and refresh
- Retry logic with exponential backoff
- Enhanced polling for long-running operations

## Material UI Theme

Custom theme with application branding:
- Primary Color: Primary Blue (#005fcc)
- Secondary Color: Secondary Orange (#f57c00)
- System font stack with consistent sizing
- Custom component styling

Theme configuration: `lib/theme.ts`

## Testing

Run tests:
```bash
npm test
npm run test:watch
npm run test:coverage
```

Test coverage includes:
- Unit tests for components and utilities
- Integration tests for authentication and workflows
- Manual data structure management operations
- Schema alignment and change tracking
- CSV parsing and validation

## Development Guidelines

1. Follow existing TypeScript conventions
2. Write tests for new functionality
3. Ensure all tests pass before committing
4. Use Material UI best practices for accessibility
5. Update documentation when modifying components

## Platform Notes

Apple Silicon (M1/M2/M3): Next.js automatically includes optimized SWC binaries for native ARM64 compilation. Ensure you're using Node.js 18+ with native ARM64 support.
