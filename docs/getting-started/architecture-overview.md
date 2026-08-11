# Architecture Overview

This document provides an overview of the Metadata Harmonization Platform architecture, helping you understand how the system components work together.

## System Overview

The platform is designed as a modern, cloud-native application with four main components that work together to provide metadata validation, harmonization, and management capabilities.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│    Frontend     │◄──►│       API       │◄──►│   Processor     │
│   (Next.js)     │    │   (FastAPI)     │    │   (Python)      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure (AWS)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  DynamoDB   │  │     S3      │  │   Cognito   │  │   ECS   │ │
│  │             │  │             │  │             │  │         │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

The platform architecture is built on four core principles:

1. **Plugin Architecture**: All storage and processing components use interfaces, allowing seamless switching between local file-based implementations and cloud services (DynamoDB, S3). This enables local-first development without infrastructure dependencies.

2. **Pipeline Pattern**: The processor uses sequential processing with parallel prediction nodes. Each pipeline stage (schema alignment, validation, semantic prediction) is an independent node that can be developed and tested in isolation.

3. **Schema-Agnostic Design**: New schemas work by simply adding JSON files to the schemas directory. No code changes required - the system dynamically loads and validates against any conforming schema definition.

4. **Local-First Development**: File-based implementations mirror cloud services exactly, providing identical interfaces. Developers can work entirely offline, then deploy to AWS without code changes.

## Component Architecture

### 1. Frontend (Next.js + Material UI)

**Purpose**: User interface for metadata upload, editing, and validation

**Key Features**:
- Interactive file upload with drag-and-drop
- Professional spreadsheet editor with advanced scrolling
- Real-time validation feedback and error highlighting
- Schema alignment review and management
- Bulk operations with progress tracking

**Technology Stack**:
- **Next.js 14** - React framework with App Router
- **Material UI** - Component library for consistent design
- **TypeScript** - Type safety and developer experience
- **React Query** - Data fetching and caching

### 2. API (FastAPI)

**Purpose**: REST API for metadata validation, job management, and processor orchestration

**Key Features**:
- ProcessorManager for lifecycle management
- Dynamic environment configuration
- Single file results.json approach
- CamelCase JSON responses for frontend compatibility
- Shared dependency injection system for resource efficiency

**Technology Stack**:
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation and serialization
- **Uvicorn** - ASGI server for production

**Architecture Patterns**:
- **Layered Architecture**: Clear separation of concerns
- **Dependency Injection**: FastAPI's built-in DI system with shared dependency management
- **Shared Component Architecture**: Centralized dependency injection for REST API and MCP server consistency
- **Async/Await**: Non-blocking I/O operations

```python
# API Layer Structure
api/
├── v1/
│   ├── endpoints/          # Route handlers
│   ├── models/            # Request/response models
│   └── dependencies/      # Shared dependencies
├── services/              # Business logic
└── core/                 # Configuration and utilities
```

### 3. Processor (Python Package)

**Purpose**: Standalone metadata harmonization with complete pipeline orchestration

**Key Features**:
- LLM-enhanced schema alignment using Amazon Bedrock
- Pluggable interfaces for storage and job management
- AWS Strands MultiAgentBase integration
- Comprehensive validation with error categorization
- AI-powered semantic predictions

**Technology Stack**:
- **Python 3.12+** - Core language
- **Pandas** - Data manipulation and analysis
- **Boto3** - AWS SDK for Python
- **Pydantic** - Data validation and models
- **Amazon Bedrock** - LLM integration for schema alignment

**Architecture Patterns**:
- **Plugin Architecture**: Pluggable interfaces for different backends
- **Pipeline Pattern**: Sequential processing nodes
- **Strategy Pattern**: Different algorithms for schema alignment

```python
# Processor Architecture
processor/
├── interfaces/           # Abstract interfaces
│   ├── job_status_saver.py
│   ├── schema_collector.py
│   └── result_saver.py
├── implementations/      # Concrete implementations
│   ├── dynamodb/        # DynamoDB implementations
│   ├── s3/             # S3 implementations
│   └── local/          # Local file implementations
└── nodes/              # Processing pipeline nodes
    ├── schema_alignment.py
    ├── validation.py
    └── semantic_prediction.py
```

### 4. Infrastructure (AWS CDK)

**Purpose**: Cloud infrastructure deployment and management

**Key Components**:
- **ECS Fargate**: Containerized application hosting
- **DynamoDB**: NoSQL database for job status and metadata
- **S3**: Object storage for validation results and schemas
- **Cognito**: User authentication and authorization
- **VPC**: Network isolation and security

**Technology Stack**:
- **AWS CDK** - Infrastructure as Code
- **TypeScript** - CDK language
- **Docker** - Container packaging

## Data Flow Architecture

### File Upload and Validation Flow

```
User Upload → Frontend → API → Processor → Storage
     │           │        │        │         │
     │           │        │        │         ▼
     │           │        │        │    ┌─────────────┐
     │           │        │        │    │ Validation  │
     │           │        │        │    │  Results    │
     │           │        │        │    │     S3      │
     │           │        │        │    └─────────────┘
     │           │        │        │
     │           │        │        ▼
     │           │        │   ┌─────────────┐
     │           │        │   │ Job Status  │
     │           │        │   │  DynamoDB   │
     │           │        │   └─────────────┘
     │           │        │
     │           │        ▼
     │           │   ┌─────────────────┐
     │           │   │ ProcessorManager│
     │           │   │    Lifecycle    │
     │           │   └─────────────────┘
     │           │
     │           ▼
     │      ┌─────────────┐
     │      │ Real-time   │
     │      │  Updates    │
     │      └─────────────┘
     │
     ▼
┌─────────────┐
│ Interactive │
│  Feedback   │
└─────────────┘
```

### Schema Alignment Flow

```
CSV Data → Schema Detection → LLM Analysis → Column Mapping → User Review
    │            │               │              │             │
    │            │               │              │             ▼
    │            │               │              │        ┌─────────────┐
    │            │               │              │        │   Accept/   │
    │            │               │              │        │   Reject    │
    │            │               │              │        └─────────────┘
    │            │               │              │             │
    │            │               │              │             ▼
    │            │               │              │        ┌─────────────┐
    │            │               │              │        │  Applied    │
    │            │               │              │        │ Transform   │
    │            │               │              │        └─────────────┘
    │            │               │              │
    │            │               │              ▼
    │            │               │         ┌─────────────┐
    │            │               │         │ Semantic    │
    │            │               │         │  Matching   │
    │            │               │         └─────────────┘
    │            │               │
    │            │               ▼
    │            │          ┌─────────────┐
    │            │          │   Amazon    │
    │            │          │   Bedrock   │
    │            │          └─────────────┘
    │            │
    │            ▼
    │       ┌─────────────┐
    │       │   Schema    │
    │       │ Collection  │
    │       └─────────────┘
    │
    ▼
┌─────────────┐
│   Source    │
│    Data     │
└─────────────┘
```

## Environment Architecture

### Local Development Environment

```
┌─────────────────────────────────────────────────────────────────┐
│                    Local Development                            │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Frontend   │    │     API     │    │     Processor       │  │
│  │ localhost:  │◄──►│ localhost:  │◄──►│   File-based        │  │
│  │    3000     │    │    8080     │    │     Storage         │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│                                                                 │
│  Storage:                                                       │
│  • Job Status: ./job_status/                                    │
│  • Results: ./validation-results/                               │
│  • Sessions: ./sessions/                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Cloud/Production Environment

```
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Cloud                                  │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  CloudFront │    │     ALB     │    │      ECS Fargate    │  │
│  │     CDN     │◄──►│ Load Balancer│◄──►│   API + Frontend   │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│                                                │                │
│                                                ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  DynamoDB   │    │     S3      │    │      Cognito        │  │
│  │ Job Status  │    │  Results &  │    │  Authentication     │  │
│  │  Metadata   │    │   Schemas   │    │                     │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Next Steps

Now that you understand the architecture:

1. **[Schema Management Guide](../developer-guides/schema-management.md)** - Learn how to work with schemas
2. **[Configuration Reference](../deployment/configuration.md)** - Detailed configuration options
3. **[Deployment Guide](../deployment/deployment-guide.md)** - Deploy to AWS
4. **[Troubleshooting Guide](../deployment/troubleshooting.md)** - Common architectural issues

## Additional Resources

- **API README**: `/Users/joehcott/Projects/metadata-harmonization/projects/api/README.md`
- **Processor README**: `/Users/joehcott/Projects/metadata-harmonization/projects/processor/README.md`
- **Frontend README**: `/Users/joehcott/Projects/metadata-harmonization/projects/frontend/README.md`

---

This architecture is designed for scalability, maintainability, and developer productivity. Each component can be developed and deployed independently while maintaining strong integration points.
