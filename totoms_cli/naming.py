"""Naming normalization and validation for Toto service names."""

import re

MAX_SERVICE_ACCOUNT_LENGTH = 30


def validate_project_name(name: str) -> str | None:
    """Validate project name. Returns error message or None if valid."""
    if not name:
        return "Project name cannot be empty"
    if not re.match(r"^[a-z][a-z0-9-]*[a-z0-9]$", name):
        return "Project name must be lowercase, start with a letter, and contain only letters, digits, and hyphens"
    if "--" in name:
        return "Project name cannot contain consecutive hyphens"
    if len(name) > MAX_SERVICE_ACCOUNT_LENGTH:
        return f"Project name must be {MAX_SERVICE_ACCOUNT_LENGTH} characters or less (GCP service account limit)"
    return None


def validate_base_path_slug(slug: str) -> str | None:
    """Validate base path slug (without leading slash). Returns error or None if valid."""
    if not slug:
        return "Base path cannot be empty"
    if not re.match(r"^[a-z][a-z0-9]*$", slug):
        return "Base path must be lowercase alphanumeric (e.g., expenses)"
    return None


def validate_base_path(path: str) -> str | None:
    """Validate base path including leading slash. Returns error message or None if valid."""
    if not path:
        return "Base path cannot be empty"
    if not path.startswith("/"):
        return "Base path must start with /"
    if not re.match(r"^/[a-z][a-z0-9]*$", path):
        return "Base path must be lowercase alphanumeric (e.g., /expenses)"
    return None


def derive_base_path(project_name: str) -> str:
    """Derive a default base path from the project name.

    Examples:
        toto-ms-expenses -> /expenses
        agent-suppie -> /suppieagent
        my-service -> /myservice
    """
    name = project_name
    # Strip common prefixes
    for prefix in ("toto-ms-", "toto-ml-", "agent-"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            if prefix == "agent-":
                return "/" + name.replace("-", "") + "agent"
            break

    return "/" + name.replace("-", "")


def to_underscore(name: str) -> str:
    """Convert hyphenated name to underscored (for TF resource names and Python vars)."""
    return name.replace("-", "_")


def derive_names(project_name: str, display_name: str, base_path: str) -> dict:
    """Derive all naming variants from the project name, display name and base path.

    Returns a dict with all the name variants needed across templates.
    """
    return {
        "project_name": project_name,
        "display_name": display_name,
        "base_path": base_path,
        "base_path_no_slash": base_path.lstrip("/"),
        "tf_resource_prefix": to_underscore(project_name),
        "service_account_id": project_name,
        "mongo_secret_prefix": project_name,
        "mongo_var_prefix": to_underscore(project_name),
    }
