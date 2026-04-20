"""Interactive prompts for the totoms CLI wizard."""

from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from totoms_cli.naming import derive_base_path, validate_base_path_slug, validate_project_name

console = Console()


@dataclass
class AgentManifest:
    agent_type: str = "conversational"
    agent_id: str = ""
    agent_name: str = ""
    agent_description: str = ""


@dataclass
class ProjectConfig:
    project_name: str = ""
    display_name: str = ""
    base_path: str = ""
    output_dir: Path = field(default_factory=lambda: Path("."))
    service_type: str = "microservice"  # "microservice" or "agent"
    needs_mongodb: bool = False
    agent_manifest: AgentManifest = field(default_factory=AgentManifest)


def ask_output_dir() -> Path:
    """Ask for the parent directory where the project folder will be created."""
    while True:
        raw = typer.prompt("\n📁 Where should the project be created? (parent directory)", default=str(Path.cwd()))
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            console.print(f"  [red]✗ Directory does not exist: {path}[/red]")
            continue
        if not path.is_dir():
            console.print(f"  [red]✗ Not a directory: {path}[/red]")
            continue
        return path


def ask_project_name() -> str:
    """Ask for the project name with validation."""
    while True:
        name = typer.prompt("\n📦 What is the project name? (e.g., toto-ms-expenses, agent-foo)")
        error = validate_project_name(name)
        if error:
            console.print(f"  [red]✗ {error}[/red]")
            continue
        return name


def ask_display_name(project_name: str) -> str:
    """Ask for a user-friendly display name."""
    default = project_name.replace("-", " ").title()
    return typer.prompt("\n🏷️  Display name (user-friendly)", default=default)


def ask_base_path(project_name: str) -> str:
    """Ask for the base path slug (without leading slash)."""
    default = derive_base_path(project_name).lstrip("/")
    while True:
        slug = typer.prompt("\n🔗 What is the base path? (no leading slash needed)", default=default)
        slug = slug.lstrip("/")  # gracefully accept if user types a slash anyway
        error = validate_base_path_slug(slug)
        if error:
            console.print(f"  [red]✗ {error}[/red]")
            continue
        return "/" + slug


def ask_service_type() -> str:
    """Ask whether this is a microservice or an agent."""
    console.print("\n🧩 What type of service is this?")
    console.print("  [bold]1.[/bold] Microservice")
    console.print("  [bold]2.[/bold] Agent (Gale conversational agent)")
    while True:
        choice = typer.prompt("  Choose", default="1")
        if choice in ("1", "microservice"):
            return "microservice"
        if choice in ("2", "agent"):
            return "agent"
        console.print("  [red]✗ Please enter 1 or 2[/red]")


def ask_mongodb() -> bool:
    """Ask whether MongoDB is needed."""
    return typer.confirm("\n🗄️  Does this service need MongoDB?", default=False)


def ask_agent_manifest() -> AgentManifest:
    """Ask for agent manifest fields."""
    console.print("\n🤖 [bold]Agent Manifest Configuration[/bold]")

    agent_type = typer.prompt("  Agent type", default="conversational")
    agent_id = typer.prompt("  Agent ID (short identifier, e.g., 'suppie')")
    agent_name = typer.prompt("  Agent display name (e.g., 'Suppie')")
    agent_description = typer.prompt("  Agent description")

    return AgentManifest(
        agent_type=agent_type,
        agent_id=agent_id,
        agent_name=agent_name,
        agent_description=agent_description,
    )


def show_summary(config: ProjectConfig) -> bool:
    """Show a summary of the configuration and ask for confirmation."""
    table = Table(title="Project Configuration Summary", show_header=False, border_style="blue")
    table.add_column("Setting", style="bold")
    table.add_column("Value", style="green")

    table.add_row("Project Name", config.project_name)
    table.add_row("Display Name", config.display_name)
    table.add_row("Output Directory", str(config.output_dir))
    table.add_row("Base Path", config.base_path)
    table.add_row("Service Type", config.service_type)
    table.add_row("MongoDB", "Yes" if config.needs_mongodb else "No")

    if config.service_type == "agent":
        table.add_row("Agent Type", config.agent_manifest.agent_type)
        table.add_row("Agent ID", config.agent_manifest.agent_id)
        table.add_row("Agent Name", config.agent_manifest.agent_name)
        table.add_row("Agent Description", config.agent_manifest.agent_description)

    console.print()
    console.print(table)

    return typer.confirm("\n✅ Generate project with these settings?", default=True)


def run_wizard() -> ProjectConfig | None:
    """Run the full interactive wizard. Returns ProjectConfig or None if cancelled."""
    console.print(Panel("[bold blue]totoms[/bold blue] — Toto Microservice Scaffolding", expand=False))

    config = ProjectConfig()
    config.project_name = ask_project_name()
    config.display_name = ask_display_name(config.project_name)
    config.output_dir = ask_output_dir()
    config.base_path = ask_base_path(config.project_name)
    config.service_type = ask_service_type()
    config.needs_mongodb = ask_mongodb()

    if config.service_type == "agent":
        config.agent_manifest = ask_agent_manifest()

    if not show_summary(config):
        console.print("[yellow]Cancelled.[/yellow]")
        return None

    return config
