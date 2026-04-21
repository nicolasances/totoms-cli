"""Core scaffolding logic for generating Toto microservice projects."""

import subprocess
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console

from totoms_cli.naming import derive_names
from totoms_cli.prompts import ProjectConfig

console = Console()

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _to_class_name(agent_id: str) -> str:
    """Convert an agent ID to a PascalCase class name.

    Examples:
        suppie -> SuppieAgent
        my-helper -> MyHelperAgent
    """
    parts = agent_id.replace("_", "-").split("-")
    return "".join(part.capitalize() for part in parts) + "Agent"


def _build_context(config: ProjectConfig) -> dict:
    """Build the Jinja2 template context from the project configuration."""
    names = derive_names(config.project_name, config.display_name, config.base_path)

    context = {
        **names,
        "service_type": config.service_type,
        "needs_mongodb": config.needs_mongodb,
    }

    if config.service_type == "agent":
        context["agent_manifest"] = {
            "agent_type": config.agent_manifest.agent_type,
            "agent_id": config.agent_manifest.agent_id,
            "agent_name": config.agent_manifest.agent_name,
            "agent_description": config.agent_manifest.agent_description,
        }
        context["agent_class_name"] = _to_class_name(config.agent_manifest.agent_id)

    return context


def _render_template(env: Environment, template_name: str, context: dict) -> str:
    """Render a single Jinja2 template."""
    template = env.get_template(template_name)
    return template.render(**context)


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

    context = _build_context(config)

    env = Environment(
        loader=PackageLoader("totoms_cli", "templates"),
        autoescape=select_autoescape([]),
        keep_trailing_newline=True,
    )

    # Define the file mapping: (template_name, output_relative_path)
    files = [
        ("app.py.j2", "app.py"),
        ("init.py.j2", "__init__.py"),
        ("Dockerfile.j2", "Dockerfile"),
        ("requirements.txt.j2", "requirements.txt"),
        ("gitignore.j2", ".gitignore"),
        # config/
        ("config.py.j2", "config/config.py"),
        ("init.py.j2", "config/__init__.py"),
        # dlg/
        ("hello.py.j2", "dlg/hello.py"),
        ("init.py.j2", "dlg/__init__.py"),
    ]

    # Terraform
    if config.service_type == "agent":
        files.append(("terraform/agent.tf.j2", f"gcp/terraform/{config.project_name}.tf"))
    else:
        files.append(("terraform/microservice.tf.j2", f"gcp/terraform/{config.project_name}.tf"))

    # GitHub Actions workflows
    files.append(("workflows/release-dev.yml.j2", "gcp/.github/workflows/release-dev.yml"))
    files.append(("workflows/release-prod.yml.j2", "gcp/.github/workflows/release-prod.yml"))

    # Agent-specific files
    if config.service_type == "agent":
        agent_id = config.agent_manifest.agent_id
        files.append(("init.py.j2", "agent/__init__.py"))
        files.append(("agent/agent.py.j2", f"agent/{agent_id}_agent.py"))
        files.append(("agent/tools.py.j2", "agent/tools.py"))

    # Create all files
    for template_name, rel_path in files:
        out_path = project_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = _render_template(env, template_name, context)
        out_path.write_text(content)
        console.print(f"  [dim]Created {rel_path}[/dim]")

    # Create empty docs/ directory
    (project_dir / "docs").mkdir(parents=True, exist_ok=True)

    # Initialize a fresh git repo — no remote, clean history
    try:
        subprocess.run(["git", "init", "-q", str(project_dir)], check=True)
    except subprocess.CalledProcessError:
        console.print("  [yellow]⚠ Could not initialize git repository. Run 'git init' manually.[/yellow]")
        return project_dir

    try:
        subprocess.run(["git", "add", "-A"], cwd=project_dir, check=True)
    except subprocess.CalledProcessError:
        console.print("  [yellow]⚠ Could not stage files. Run 'git add -A' manually.[/yellow]")
        return project_dir

    try:
        subprocess.run(
            ["git", "commit", "-q", "-m", "Initial commit"],
            cwd=project_dir,
            check=True,
        )
    except subprocess.CalledProcessError:
        console.print(
            "  [yellow]⚠ Could not create initial git commit "
            "(git user not configured). Run 'git commit' manually.[/yellow]"
        )

    return project_dir
