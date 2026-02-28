#!/usr/bin/env python3
"""
Script para baixar tarefas do Odoo para arquivos JSON locais.

Uso:
    python sync_pull.py                      # Baixar todas as minhas tarefas
    python sync_pull.py --project 1          # Baixar tarefas do projeto 1
    python sync_pull.py --project 1 --user 2 # Baixar tarefas do projeto 1 do usuário 2
"""

import sys
import os
import logging
from pathlib import Path
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sync.odoo_client import OdooClient
from src.sync.sync_manager import SyncManager

# Carregar variáveis de ambiente
load_dotenv()

console = Console()


def setup_logging(level: str = "INFO"):
    """Configurar logging"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("logs/sync_pull.log"), logging.StreamHandler()],
    )


@click.command()
@click.option("--project", "-p", type=int, help="ID do projeto")
@click.option(
    "--user", "-u", type=int, help="ID do usuário (padrão: usuário autenticado)"
)
@click.option("--include-completed", is_flag=True, help="Incluir tarefas completadas")
@click.option("--output-dir", default="data", help="Diretório de saída")
@click.option(
    "--log-level", default="INFO", help="Nível de log (DEBUG, INFO, WARNING, ERROR)"
)
def main(
    project: int, user: int, include_completed: bool, output_dir: str, log_level: str
):
    """Baixar tarefas do Odoo para JSON local"""

    # Setup
    setup_logging(log_level)
    data_dir = Path(__file__).parent.parent / output_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    # Carregar configurações
    host = os.getenv("ODOO_HOST")
    port = int(os.getenv("ODOO_PORT", 443))
    protocol = os.getenv("ODOO_PROTOCOL", "jsonrpc+ssl")
    db = os.getenv("ODOO_DB")
    odoo_user = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")

    if not all([host, db, odoo_user, password]):
        console.print(
            "[red]❌ Erro: Configurações do Odoo não encontradas no .env[/red]"
        )
        console.print("Configure ODOO_HOST, ODOO_DB, ODOO_USER, ODOO_PASSWORD")
        sys.exit(1)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Conectar ao Odoo
            task = progress.add_task("Conectando ao Odoo...", total=None)
            client = OdooClient(host, port, db, odoo_user, password, protocol)
            progress.update(task, description=f"✅ Conectado como: {odoo_user}")
            progress.stop()

            current_user = client.get_current_user()
            console.print(
                f"\n[green]✓[/green] Autenticado como: [cyan]{current_user['name']}[/cyan]"
            )

            # Criar sync manager
            sync_manager = SyncManager(client, data_dir)

            # Pull tarefas
            console.print("\n[yellow]Baixando tarefas...[/yellow]")

            filepath = sync_manager.pull_tasks(
                project_id=project, user_id=user, include_completed=include_completed
            )

            console.print(
                f"\n[green]✓ Tarefas salvas em:[/green] [cyan]{filepath}[/cyan]"
            )

            # Mostrar estatísticas
            with open(filepath, "r") as f:
                import json

                data = json.load(f)
                total = data["metadata"]["total_tasks"]
                project_name = data["metadata"].get("project_name", "Todas as tarefas")

                console.print(f"\n[bold]Resumo:[/bold]")
                console.print(f"  Projeto: {project_name}")
                console.print(f"  Total de tarefas: {total}")
                console.print(
                    f"  Incluir completadas: {'Sim' if include_completed else 'Não'}"
                )

            console.print("\n[green]✅ Sincronização concluída![/green]")

    except Exception as e:
        console.print(f"\n[red]❌ Erro: {e}[/red]")
        logging.exception("Erro durante pull")
        sys.exit(1)


if __name__ == "__main__":
    # Criar diretório de logs
    Path("logs").mkdir(exist_ok=True)
    main()
