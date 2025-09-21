# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI project demonstrating Clean Architecture principles, serving as example code for the book "FastAPI로 배우는 백엔드 프로그래밍 with 클린 아키텍처" (Backend Programming with FastAPI and Clean Architecture).

## Development Commands

### Environment Setup
- **Virtual Environment**: Use `.venv` directory (Python 3.12+)
- **Activate**: `source .venv/bin/activate`
- **Install Dependencies**: Dependencies are managed via `pyproject.toml`

### Running the Application
```bash
# Development server with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --host 127.0.0.1 --reload
```

### Testing
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest user/application/user_service_test.py

# Run tests with specific pattern
python -m pytest -k "test_create_user"

# Run tests in specific module
python -m pytest user/
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "migration message"

# Apply migrations
alembic upgrade head

# Check current migration status
alembic current

# View migration history
alembic history
```

## Architecture Overview

### Clean Architecture Layers

The project implements Clean Architecture with strict layer separation:

1. **Domain Layer** (`domain/`): Business entities and repository interfaces
   - Contains business rules and entities (User, Note, Tag)
   - Repository interfaces (IUserRepository, INoteRepository)
   - No dependencies on external frameworks

2. **Application Layer** (`application/`): Business logic and use cases
   - Service classes implementing business use cases
   - Orchestrates domain objects and repository calls
   - Depends only on domain layer

3. **Infrastructure Layer** (`infra/`): External concerns implementation
   - Database models and repository implementations
   - External service integrations
   - Implements domain repository interfaces

4. **Interface Layer** (`interface/`): API controllers and request/response models
   - FastAPI routers and request handlers
   - Request/response DTOs using Pydantic
   - Depends on application and domain layers

### Dependency Injection

The project uses `dependency-injector` for IoC:
- **Container**: `containers.py` defines all service dependencies
- **Wiring**: Automatic injection in controllers using `@inject` decorator
- **Providers**: Factory patterns for service instantiation

### Key Architectural Patterns

- **Repository Pattern**: Abstract data access through interfaces
- **Service Layer**: Business logic encapsulation in service classes
- **DTO Pattern**: Request/response models separate from domain entities
- **Value Objects**: Domain entities as dataclasses with immutable data

### Module Structure

Each business domain (user, note) follows the same structure:
```
user/
├── domain/
│   ├── user.py              # Domain entity
│   └── repository/
│       └── user_repo.py     # Repository interface
├── application/
│   └── user_service.py      # Business logic
├── infra/
│   ├── db_models/
│   │   └── user.py          # SQLAlchemy model
│   └── repository/
│       └── user_repo.py     # Repository implementation
└── interface/
    └── controllers/
        └── user_controller.py  # FastAPI router
```

### Database Integration

- **ORM**: SQLAlchemy 2.0+ with declarative models
- **Migration**: Alembic for schema versioning
- **Session Management**: Context managers for transaction handling
- **Models**: Separate domain entities from SQLAlchemy models

### Testing Strategy

- **Unit Tests**: Per-layer testing with mocks for dependencies
- **Fixtures**: pytest fixtures for dependency mocking
- **Time Mocking**: freezegun for datetime testing
- **Dependency Mocking**: pytest-mock for service isolation

### Configuration Management

- **Settings**: Pydantic Settings for environment-based configuration
- **Environment Variables**: Database credentials, JWT secrets, etc.
- **Caching**: LRU cache for settings to avoid repeated environment reads

## Important Implementation Notes

### Dependency Injection Wiring
Controllers use `@inject` decorator and `Provide[Container.service]` for dependency injection. The container is configured in `main.py`.

### Database Session Handling
Always use context managers (`with SessionLocal() as db:`) for proper session cleanup and transaction management.

### Domain Entity Conversion
Infrastructure layer converts between domain entities (dataclasses) and SQLAlchemy models using explicit mapping in repository implementations.

### Authentication Flow
The project includes JWT-based authentication with role-based access control implemented through FastAPI dependency injection.

### Migration Workflow
- Database models must be imported in `database_models.py` for Alembic autogeneration
- Migration files use timestamp prefixes for ordering
- Always review generated migrations before applying

## Example Code Reference

The `example/` directory contains chapter-specific code demonstrations:
- `ch06_02/`: Synchronous vs asynchronous endpoint examples
- `ch08_03/`: Environment variable configuration examples
- `ch10_02/`: Celery task examples
- `ch11_01/`: Middleware and context examples