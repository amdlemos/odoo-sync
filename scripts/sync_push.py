#!/usr/bin/env python3
"""
Script para enviar mudanças aprovadas para o Odoo.

Uso:
    python sync_push.py approved_changes.json           # Aplicar mudanças
    python sync_push.py approved_changes.json --dry-run # Apenas validar
"""

import sys
import os
import logging
from pathlib import Path
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sync.odoo_client import OdooClient
from src.sync.sync_manager import SyncManager

# Carregar variáveis de ambiente
load_dotenv()

console = Console()


@click.command()
@click.argument("changes_file", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Apenas validar sem aplicar mudanças")
@click.option("--output-dir", default="data", help="Diretório de dados")
def main(changes_file: str, dry_run: bool, output_dir: str):
    """Enviar mudanças aprovadas para o Odoo"""

    # Configurar logging
    logging.basicConfig(level=logging.INFO)

    data_dir = Path(__file__).parent.parent / output_dir
    changes_path = Path(changes_file)

    # Carregar configurações
    host = os.getenv("ODOO_HOST")
    port = int(os.getenv("ODOO_PORT", 443))
    protocol = os.getenv("ODOO_PROTOCOL", "jsonrpc+ssl")
    db = os.getenv("ODOO_DB")
    odoo_user = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")

    if not all([host, db, odoo_user, password]):
        console.print("[red]❌ Erro: Configurações do Odoo não encontradas[/red]")
        sys.exit(1)

    try:
        # Conectar
        console.print("[yellow]Conectando ao Odoo...[/yellow]")
        client = OdooClient(host, port, db, odoo_user, password, protocol)
        console.print(f"[green]✓[/green] Conectado\n")

        # Sync manager
        sync_manager = SyncManager(client, data_dir)

        # Push mudanças
        console.print(
            f"[yellow]{'[DRY-RUN] ' if dry_run else ''}Aplicando mudanças...[/yellow]\n"
        )

        results = sync_manager.push_changes(changes_path, dry_run=dry_run)

        # Mostrar resultados
        table = Table(title="Resultado da Sincronização")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")

        table.add_row("Total de mudanças", str(results["total"]))
        table.add_row("Sucessos", str(results["success"]))
        table.add_row("Falhas", str(results["failed"]))
        table.add_row("Conflitos", str(results["conflicts"]))
        table.add_row("Ignoradas", str(results["skipped"]))

        console.print(table)

        # Mostrar detalhes de conflitos
        if results["conflicts"] > 0:
            console.print("\n[yellow]⚠️  Conflitos detectados![/yellow]")
            console.print("Execute: [cyan]python scripts/resolve_conflicts.py[/cyan]")

        # Mostrar detalhes de falhas
        if results["failed"] > 0:
            console.print("\n[red]❌ Algumas mudanças falharam:[/red]")
            for detail in results["details"]:
                if detail["status"] == "failed":
                    console.print(
                        f"  - {detail.get('change_id')}: {detail.get('message')}"
                    )

        if dry_run:
            console.print(
                "\n[yellow]ℹ️  Modo dry-run: Nenhuma mudança foi aplicada[/yellow]"
            )
        else:
            console.print("\n[green]✅ Sincronização concluída![/green]")

    except Exception as e:
        console.print(f"\n[red]❌ Erro: {e}[/red]")
        logging.exception("Erro durante push")
        sys.exit(1)


if __name__ == "__main__":
    main()
