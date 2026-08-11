# Documentation Index

Quick reference guide to documentation in the Metadata Harmonization Platform.

## Cross-Cutting Documentation

Core documentation covering architecture, development, and deployment:

- **[Architecture Overview](getting-started/architecture-overview.md)** - System design and components
- **[Data Flow](architecture/DataFlow.md)** - How data moves through the system
- **[Schema Management](developer-guides/schema-management.md)** - Schema system and validation

## Security Documentation

Security review findings and their status:

- **[Production Considerations](security/production-considerations.md)** - Controls intentionally deferred for this sample; required before any real deployment

## Deployment Documentation

Infrastructure and operational guides:

- **[Deployment Guide](deployment/deployment-guide.md)** - AWS infrastructure setup
- **[Configuration Reference](deployment/configuration.md)** - Configuration options
- **[Troubleshooting Guide](deployment/troubleshooting.md)** - Common issues and solutions

## Project READMEs

Individual project documentation:

### Backend Services
- **[API](../projects/api/README.md)** - FastAPI backend service
- **[Processor](../projects/metadata-harmonization-processor/README.md)** - Core metadata processing engine
- **[Agent](../projects/agent/README.md)** - CLI and interactive validation agent


### Frontend
- **[Frontend](../projects/frontend/README.md)** - Next.js web application

### Testing and Infrastructure
- **[Evaluation](../projects/eval/README.md)** - Evaluation and benchmarking system
- **[Infrastructure](../projects/infra/README.md)** - AWS CDK infrastructure as code

## Quick Start

New to the platform? Start here:

1. Read the root **[README](../README.md)** for project overview and setup
2. Review the **[Architecture Overview](getting-started/architecture-overview.md)** to understand the system
3. Follow setup instructions in the relevant project README above
4. Check the **[Troubleshooting Guide](deployment/troubleshooting.md)** if you encounter issues

## Local Development URLs

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8080/docs
- **API Health Check**: http://localhost:8080/api/health

---

**Need help?** Check the [Troubleshooting Guide](deployment/troubleshooting.md) or create an issue in the repository.
