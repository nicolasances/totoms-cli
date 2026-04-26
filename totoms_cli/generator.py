"""Core scaffolding logic for generating Toto microservice projects."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console

from totoms_cli.naming import derive_names
from totoms_cli.prompts import ProjectConfig

console = Console()

NODE_TEMPLATE_REPO = "https://github.com/nicolasances/toto-node-template"
PYTHON_MS_TEMPLATE_REPO = "https://github.com/nicolasances/toto-python-ms-template"


def _to_class_name(agent_id: str) -> str:
    """Convert an agent ID to a PascalCase class name.

    Examples:
        suppie -> SuppieAgent
        my-helper -> MyHelperAgent
    """
    parts = agent_id.replace("_", "-").split("-")
    return "".join(part.capitalize() for part in parts) + "Agent"


def _clone_template(repo_url: str) -> Path:
    """Clone a template repository to a temporary directory.

    Args:
        repo_url: The URL of the template repository to clone.

    Returns:
        Path to the cloned repository (caller must clean up).

    Raises:
        RuntimeError: If cloning fails, with a user-friendly message.
    """
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", repo_url, str(tmp_dir)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        stderr = e.stderr.decode("utf-8", errors="replace").strip() if e.stderr else ""
        detail = f"\n{stderr}" if stderr else ""
        raise RuntimeError(
            f"Failed to clone template repository '{repo_url}'.{detail}\n"
            "Please check your internet connection and try again."
        ) from e
    return tmp_dir


def _is_text_file(path: Path) -> bool:
    """Determine if a file is a text file by trying to decode its first 8 KB as UTF-8."""
    try:
        with path.open("rb") as f:
            f.read(8192).decode("utf-8")
        return True
    except (UnicodeDecodeError, PermissionError):
        return False


def _apply_substitutions(content: str, subs: list[tuple[str, str]]) -> str:
    """Apply an ordered list of (find, replace) substitutions to content."""
    for find, replace in subs:
        content = content.replace(find, replace)
    return content


def _build_substitutions(config: ProjectConfig, names: dict) -> list[tuple[str, str]]:
    """Build an ordered list of (find, replace) substitutions based on runtime."""
    project_name = names["project_name"]
    display_name = names["display_name"]
    base_path = names["base_path"]
    mongo_var_prefix = names["mongo_var_prefix"]

    if config.runtime == "node":
        return [
            ("toto-node-template", project_name),
            ("Toto MS XXX", display_name),
            ("toto-ms-xxx", project_name),
            ("toto-ms-ex1", project_name),
            ("XXX", display_name),
            ("/ex1", base_path),
        ]
    else:
        return [
            ("toto-ms-ex1", project_name),
            ("toto_ms_ex1", mongo_var_prefix),
            ("Toto Ex1 API", display_name),
            ("/ex1", base_path),
        ]


def _build_mongodb_block(project_name: str, mongo_var_prefix: str) -> str:
    """Build the MongoDB Terraform block for the given project.

    Args:
        project_name: The project name used for resource IDs and secret names.
        mongo_var_prefix: The underscore-form of the project name used as a
            prefix for Terraform variable names (e.g. ``toto_ms_test`` for
            a project named ``toto-ms-test``).
    """
    return f"""
variable "{mongo_var_prefix}_mongo_user" {{
    description = "Mongo User for {project_name}"
    type = string
    sensitive = true
}}
variable "{mongo_var_prefix}_mongo_pswd" {{
    description = "Mongo Password for {project_name}"
    type = string
    sensitive = true
}}
resource "google_secret_manager_secret" "{project_name}-mongo-user" {{
    secret_id = "{project_name}-mongo-user"
    replication {{
        auto {{ }}
    }}
}}
resource "google_secret_manager_secret_version" "{project_name}-mongo-user-version" {{
    secret = google_secret_manager_secret.{project_name}-mongo-user.id
    secret_data = var.{mongo_var_prefix}_mongo_user
}}
resource "google_secret_manager_secret" "{project_name}-mongo-pswd" {{
    secret_id = "{project_name}-mongo-pswd"
    replication {{
        auto {{ }}
    }}
}}
resource "google_secret_manager_secret_version" "{project_name}-mongo-pswd-version" {{
    secret = google_secret_manager_secret.{project_name}-mongo-pswd.id
    secret_data = var.{mongo_var_prefix}_mongo_pswd
}}
"""


def generate_project(config: ProjectConfig, output_dir: Path) -> Path:
    """Generate a complete Toto microservice project.

    Args:
        config: The project configuration from the wizard.
        output_dir: The parent directory where the project folder will be created.

    Returns:
        The path to the generated project directory.
    """
    project_dir = output_dir / config.project_name
    if project_dir.exists():
        raise FileExistsError(f"Directory already exists: {project_dir}")

    names = derive_names(config.project_name, config.display_name, config.base_path)
    subs = _build_substitutions(config, names)

    if config.runtime == "node":
        template_repo = NODE_TEMPLATE_REPO
        tf_src_name = "toto-ms-xxx.tf"
    else:
        template_repo = PYTHON_MS_TEMPLATE_REPO
        tf_src_name = "toto-ms-ex1.tf"

    tmp_dir = None
    try:
        console.print(f"  [dim]Cloning template from {template_repo}...[/dim]")
        tmp_dir = _clone_template(template_repo)

        project_dir.mkdir(parents=True, exist_ok=True)

        # Walk all files in the cloned repo, skip .git/
        for src_path in sorted(tmp_dir.rglob("*")):
            if src_path.is_dir():
                continue
            rel = src_path.relative_to(tmp_dir)
            if rel.parts[0] == ".git":
                continue

            out_path = project_dir / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if _is_text_file(src_path):
                content = src_path.read_text(encoding="utf-8")
                content = _apply_substitutions(content, subs)
                out_path.write_text(content, encoding="utf-8")
            else:
                shutil.copy2(src_path, out_path)

            console.print(f"  [dim]Created {rel}[/dim]")

        # Rename TF file: toto-ms-xxx.tf / toto-ms-ex1.tf → {project_name}.tf
        tf_dir = project_dir / "gcp" / "terraform"
        old_tf = tf_dir / tf_src_name
        new_tf = tf_dir / f"{config.project_name}.tf"
        if old_tf.exists():
            old_tf.rename(new_tf)

        # [Python agent only] Add agent-specific files via embedded Jinja2
        if config.runtime == "python" and config.service_type == "agent":
            agent_context = {
                **names,
                "runtime": config.runtime,
                "service_type": config.service_type,
                "needs_mongodb": config.needs_mongodb,
                "agent_manifest": {
                    "agent_type": config.agent_manifest.agent_type,
                    "agent_id": config.agent_manifest.agent_id,
                    "agent_name": config.agent_manifest.agent_name,
                    "agent_description": config.agent_manifest.agent_description,
                },
                "agent_class_name": _to_class_name(config.agent_manifest.agent_id),
            }
            env = Environment(
                loader=PackageLoader("totoms_cli", "templates"),
                autoescape=select_autoescape([]),
                keep_trailing_newline=True,
            )
            agent_id = config.agent_manifest.agent_id
            agent_files = [
                ("init.py.j2", "agent/__init__.py"),
                ("agent/agent.py.j2", f"agent/{agent_id}_agent.py"),
                ("agent/tools.py.j2", "agent/tools.py"),
            ]
            for template_name, rel_path in agent_files:
                out_path = project_dir / rel_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                template = env.get_template(template_name)
                content = template.render(**agent_context)
                out_path.write_text(content, encoding="utf-8")
                console.print(f"  [dim]Created {rel_path}[/dim]")

        # [Python + needs_mongodb=True] Append MongoDB Terraform block to .tf file
        if config.runtime == "python" and config.needs_mongodb:
            if new_tf.exists():
                mongodb_block = _build_mongodb_block(
                    config.project_name, names["mongo_var_prefix"]
                )
                with new_tf.open("a", encoding="utf-8") as f:
                    f.write("\n# ---------------------------------------------------------------\n")
                    f.write("# MongoDB (Secret Manager)\n")
                    f.write("# ---------------------------------------------------------------\n")
                    f.write(mongodb_block)
                console.print(
                    f"  [dim]Appended MongoDB block to gcp/terraform/{config.project_name}.tf[/dim]"
                )

        # Create empty docs/ directory
        (project_dir / "docs").mkdir(parents=True, exist_ok=True)

    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # Initialize a fresh git repo — no remote, clean history
    try:
        subprocess.run(["git", "init", "-q", str(project_dir)], check=True)
    except subprocess.CalledProcessError:
        console.print("  [yellow]⚠ Could not initialize git repository. Run 'git init' manually.[/yellow]")

    return project_dir
