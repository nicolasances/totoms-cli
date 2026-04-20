# totoms-cli

CLI tool to scaffold Toto microservices and agents for GCP Cloud Run deployment.

## Index

- [Installation](#installation)
- [Usage](#usage)
  - [Options](#options)
- [Next Steps After Generation](#next-steps-after-generation)
- [Building and Publishing to PyPI](#building-and-publishing-to-pypi)
  - [Prerequisites](#prerequisites)
  - [Build the package](#build-the-package)
  - [Bump the version](#bump-the-version)
  - [Publish to PyPI](#publish-to-pypi)
  - [Publish to TestPyPI (dry run)](#publish-to-testpypi-dry-run)
  - [After publishing](#after-publishing)

## Installation

```bash
cd totoms-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
totoms
```

This launches an interactive wizard that asks:

1. **Project name** — e.g., `toto-ms-expenses` or `agent-foo`
2. **Display name** — user-friendly name, e.g., `Expenses Service` (used in Terraform service account etc.)
3. **Output directory** — the parent directory where the project folder will be created (the project folder itself is created inside; defaults to current directory)
4. **Base path** — URL prefix without leading slash, e.g., `expenses` (slash added automatically)
5. **Service type** — microservice or agent
6. **MongoDB** — whether the service needs MongoDB
7. **Agent manifest** (if agent) — type, id, display name, description

After confirming your choices, the CLI generates:

- Full Python project skeleton (FastAPI + toto SDK)
- GCP Terraform file (in `gcp/terraform/`)
- GitHub Actions workflows (in `gcp/.github/workflows/`)
- If agent: `agent/` directory with Gale agent skeleton + MCP client scaffolding (commented out)

### Options

Run `totoms --help` for a list of available flags.

## Next Steps After Generation

1. Create a GitHub repository with the project name
2. Copy the Terraform file from `gcp/terraform/` to `toto-terra/`
3. Move `gcp/.github/` to the project root as `.github/`
4. Create Terraform workspaces: `{project}-dev` and `{project}-prod`
5. Apply Terraform and push code

## Building and Publishing to PyPI

### Prerequisites

```bash
pip install build twine
```

### Build the package

From the `totoms-cli` directory:

```bash
python -m build
```

This produces two artifacts inside `dist/`:
- `totoms_cli-<version>-py3-none-any.whl` — wheel (preferred)
- `totoms_cli-<version>.tar.gz` — source distribution

### Bump the version

Edit the `version` field in `pyproject.toml` before each release:

```toml
[project]
version = "0.2.0"
```

### Publish to PyPI

```bash
python -m twine upload dist/*
```

You will be prompted for your PyPI credentials (or use a `~/.pypirc` file / API token).

### Publish to TestPyPI (dry run)

```bash
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI to verify before the real release:

```bash
pip install --index-url https://test.pypi.org/simple/ totoms-cli
```

### After publishing

Users can install directly with:

```bash
pip install totoms-cli
```
