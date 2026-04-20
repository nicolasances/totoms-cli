"""totoms CLI — Toto Microservice Scaffolding tool."""

import typer
from rich.console import Console
from rich.panel import Panel

from totoms_cli.generator import generate_project
from totoms_cli.prompts import run_wizard

app = typer.Typer(
    name="totoms",
    help="CLI tool to scaffold Toto microservices and agents.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def create():
    """Interactively scaffold a new Toto microservice or agent."""
    config = run_wizard()
    if config is None:
        raise typer.Abort()

    try:
        project_dir = generate_project(config, config.output_dir)
    except FileExistsError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Abort()

    console.print(f"\n[green]✅ Project generated at:[/green] {project_dir}\n")
    console.print(Panel(
        "\n".join([
            "[bold]Next steps:[/bold]",
            "",
            f"1. Create a GitHub repository named [cyan]{config.project_name}[/cyan]",
            f"2. Copy [cyan]gcp/terraform/{config.project_name}.tf[/cyan] to your [cyan]toto-terra/[/cyan] repo",
            f"3. Move [cyan]gcp/.github/[/cyan] to the project root as [cyan].github/[/cyan]",
            f"4. Create Terraform workspaces: [cyan]{config.project_name}-dev[/cyan] and [cyan]{config.project_name}-prod[/cyan]",
            "5. Apply Terraform, then push your code",
            "",
            f"  cd {project_dir}",
            "  python -m venv .venv && source .venv/bin/activate",
            "  pip install -r requirements.txt",
        ]),
        title="🚀 What's next",
        expand=False,
    ))


if __name__ == "__main__":
    app()
