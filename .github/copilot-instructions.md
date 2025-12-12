# Copilot Instructions for cybulde-data-preparation

## Project Overview
This is an MLOps data preparation project using a **Docker-first workflow** with Hydra configuration management and Poetry dependency management. All development happens inside containers - never run Python commands directly on the host.

## Critical Architecture Patterns

### Hydra + Pydantic Configuration System
The project uses a sophisticated config pattern combining Hydra and Pydantic:
- **Config schemas** live in `cybulde/config_schemas/config_schema.py` as Pydantic dataclasses
- **Config values** are in `cybulde/configs/config.yaml` using Hydra's composition system
- **Config registration**: `setup_config()` in `config_utils.py` registers schemas with Hydra's ConfigStore
- **Entry pattern**: Use `@get_config(config_path="../configs", config_name="config")` decorator on entry functions
  ```python
  @get_config(config_path="../configs", config_name="config")
  def entrypoint(config: Config) -> None:
      # config is a validated Pydantic object
  ```

### Logging Configuration
Custom logging is configured via `cybulde/configs/hydra/job_logging/custom.yaml`:
- Logs to both console and rotating file (`logs.log`)
- Hydra's default logging is disabled in `config.yaml`
- Use standard Python logging: `import logging; logger = logging.getLogger(__name__)`

## Development Workflow

### Docker-Centric Commands
**All work must use the Makefile** - do not run `poetry`, `pytest`, `python` directly:

```bash
make up              # Start containers (runs implicitly with other commands)
make exec-in         # Interactive shell in container
make format-and-sort # Format with black + isort
make lint            # Run flake8, black --check, isort --check
make test            # Run pytest
make full-check      # Lint + type check + coverage
make notebook        # Start JupyterLab on port 8888
```

### Building and Dependencies
```bash
make build                  # Rebuild image
make build-for-dependencies # Remove lock and rebuild
make lock-dependencies      # Lock deps with poetry (creates poetry.lock)
```

The Dockerfile copies `poetry.lock.build` to preserve lock files between builds.

## Code Standards

### Import Organization (isort config in pyproject.toml)
```python
# Sections: FUTURE → STDLIB → THIRDPARTY → FIRSTPARTY (cybulde) → LOCALFOLDER
from typing import Any  # stdlib

import hydra  # thirdparty
from omegaconf import DictConfig

from cybulde.config_schemas import config_schema  # firstparty
```

### Type Annotations (mypy strict mode)
- All functions require type hints: `def func(arg: str) -> None:`
- `mypy` has strict settings: `disallow_untyped_defs`, `disallow_untyped_calls`, etc.
- Use `type: ignore` sparingly (see `entrypoint.py` for Hydra decorator pattern)

### Formatting
- Line length: **120 characters** (black + isort configured)
- Use black's default style
- flake8 ignores: `E501,W503,W504,E203,I201,I202`

## Key Files and Their Roles

- `cybulde/entrypoint.py` - Template for creating new entry points with Hydra
- `cybulde/utils/config_utils.py` - Core infrastructure for config + logging setup
- `pyproject.toml` - Poetry dependencies, tool configs (black/isort/mypy)
- `Makefile` - Single source of truth for all commands
- `docker-compose.yaml` - Mounts `./` to `/app/`, uses user's GCloud credentials

## Integration Points

### GCP Integration
- GCloud SDK installed in Docker image (version 426.0.0)
- Host's `~/.config/gcloud/` mounted into container for authentication
- Environment expects `gcloud` commands to work inside container

### Volume Mounts
- Project root (`./`) mounted to `/app/` - changes sync immediately
- Working directory in container is `/app/`
- PYTHONPATH includes `/app/` - absolute imports from `cybulde` work everywhere

## Common Tasks

### Adding a New Entry Point
1. Create `cybulde/your_script.py` following `entrypoint.py` pattern
2. Add Makefile target:
   ```makefile
   your-task: up
       $(DOCKER_COMPOSE_EXEC) python ./cybulde/your_script.py
   ```
3. Update config schema if needed in `config_schemas/config_schema.py`

### Adding Dependencies
1. Edit `pyproject.toml` manually or use `poetry add <package>` inside container
2. Run `make lock-dependencies` to update `poetry.lock`
3. Run `make build` to rebuild with new dependencies

### Testing Changes
Always run the full pipeline before committing:
```bash
make full-check  # lint + type-check + test with coverage
```
