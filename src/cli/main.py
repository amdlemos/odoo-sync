import sys
import os
from pathlib import Path
import click
from dotenv import load_dotenv
from rich.console import Console

# Ensure src modules can be found
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.sync.odoo_client import OdooClient
from src.sync.sync_manager import SyncManager

console = Console()


def load_config():
    """Load configuration from global and local env files"""
    # 1. Load global config
    global_env = Path.home() / ".config" / "odoo-sync" / ".env"
    if global_env.exists():
        load_dotenv(global_env)

    # 2. Load local config (overrides global)
    local_env = Path.cwd() / ".odoo-sync.env"
    if local_env.exists():
        load_dotenv(local_env)

    # Fallback to standard .env if we are in the source directory
    source_env = Path(__file__).parent.parent.parent / ".env"
    if source_env.exists() and not local_env.exists():
        load_dotenv(source_env)


def get_client():
    load_config()
    host = os.getenv("ODOO_HOST")
    port = int(os.getenv("ODOO_PORT", 443))
    protocol = os.getenv("ODOO_PROTOCOL", "jsonrpc")
    db = os.getenv("ODOO_DB")
    user = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")

    if not all([host, db, user, password]):
        console.print("[red]❌ Erro: Configurações do Odoo não encontradas.[/red]")
        console.print("Execute [cyan]odoo-sync init[/cyan] para configurar.")
        sys.exit(1)

    try:
        return OdooClient(host, port, db, user, password, protocol)
    except Exception as e:
        console.print(f"[red]❌ Erro de conexão: {e}[/red]")
        sys.exit(1)


@click.group()
def cli():
    """CLI para sincronizar tarefas do Odoo e gerenciar agentes de IA."""
    pass


@cli.command()
def init():
    """Inicializar configuração no diretório atual"""
    local_env = Path.cwd() / ".odoo-sync.env"
    prompt_file = Path.cwd() / ".odoo-agent-rules.md"

    if local_env.exists():
        console.print(
            "[yellow]Aviso: .odoo-sync.env já existe neste diretório.[/yellow]"
        )
    else:
        with open(local_env, "w") as f:
            f.write("# Configuração Local do Odoo Sync\n")
            f.write("DEFAULT_PROJECT_ID=\n")
            f.write(
                "\n# Odoo Configuração (Descomente se este projeto usar credenciais específicas ao invés da global ~/.config/odoo-sync/.env)\n"
            )
            f.write("# ODOO_HOST=localhost\n")
            f.write("# ODOO_PORT=8069\n")
            f.write("# ODOO_PROTOCOL=jsonrpc\n")
            f.write("# ODOO_DB=odoo\n")
            f.write("# ODOO_USER=user@email.com\n")
            f.write("# ODOO_PASSWORD=password\n")
            f.write(
                "\n# AI Agents Worker Pool (Descomente para sobrescrever a global)\n"
            )
            f.write("# AI_AGENT_IDS=2,3,4\n")

    # Criar template de prompt para IAs se não existir
    if not prompt_file.exists():
        prompt_content = """# Odoo-Task-Sync AI System Prompt

Você é um agente de IA especializado em desenvolvimento de software e tem permissão para gerenciar a própria tarefa que está resolvendo diretamente no Odoo do usuário.

## Ferramenta Disponível
O usuário empacotou uma ferramenta de linha de comando chamada `odoo-sync`. Você deve usar essa ferramenta via bash para iniciar cronômetros de trabalho (timesheets), baixar tarefas e mudar as tarefas de estágio ao final.

## Seu Fluxo de Trabalho Obrigatório

1. **Entender a Tarefa**: Leia os arquivos `.json` na pasta local `data/tasks/` se o usuário não tiver detalhado o que você deve fazer.
2. **Iniciar Cronômetro**: SEMPRE que começar a atuar numa tarefa, você DEVE ligar o seu cronômetro para que o esforço seja registrado no seu nome.
   ```bash
   odoo-sync timer start --task <ID_DA_TAREFA> --desc "<DESCRICAO DO QUE VAI FAZER>" --model "<SEU_NOME_EX_OPENCODE>"
   ```
   **MUITO IMPORTANTE:** Guarde o ID do cronômetro retornado por este comando!
3. **Executar**: Escreva e altere os arquivos conforme solicitado pelo usuário.
4. **Parar Cronômetro**: Assim que você finalizar o código ou a etapa proposta, PARE O CRONÔMETRO IMEDIATAMENTE usando o ID que você guardou no passo 2.
   ```bash
   odoo-sync timer stop --id <ID_DO_CRONOMETRO>
   ```
5. **Mover Estágio (Se Concluído)**: Se o usuário disser que a tarefa está 100% resolvida e pedir para fechar:
   Primeiro descubra os estágios: `odoo-sync task stages`
   Depois mova: `odoo-sync task move --task <ID_DA_TAREFA> --stage <ID_DO_ESTAGIO_CONCLUIDO>`

## Comandos da CLI `odoo-sync`

- `odoo-sync init` -> Inicializa as variáveis locais para o projeto atual.
- `odoo-sync pull [--project ID]` -> Baixa e atualiza o json de tarefas na máquina.
- `odoo-sync timer start --task ID --desc "Texto" --model "nome_da_ia"` -> Liga timer.
- `odoo-sync timer stop --id TIMER_ID` -> Desliga timer.
- `odoo-sync task stages` -> Lista os IDs e Nomes de estágios de projetos.
- `odoo-sync task move --task ID --stage STAGE_ID` -> Muda o status da tarefa.
"""
        with open(prompt_file, "w") as f:
            f.write(prompt_content)

    # Create data directory structure in current working directory
    data_dir = Path.cwd() / "data" / "tasks"
    data_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]✓ Projeto inicializado![/green]")
    console.print(f"Edite [cyan]{local_env}[/cyan] para definir o ID do projeto.")
    console.print(
        f"Instruções para Agentes IA geradas em [cyan].odoo-agent-rules.md[/cyan]"
    )


@cli.command()
@click.option("--project", "-p", type=int, help="ID do projeto")
@click.option(
    "--user", "-u", type=int, help="ID do usuário (padrão: usuário autenticado)"
)
@click.option("--include-completed", is_flag=True, help="Incluir tarefas completadas")
def pull(project, user, include_completed):
    """Baixar tarefas do Odoo para arquivo JSON local"""
    load_config()

    # Use env defaults if not provided via CLI
    if not project and os.getenv("DEFAULT_PROJECT_ID"):
        try:
            project = int(os.getenv("DEFAULT_PROJECT_ID"))
        except ValueError:
            pass

    client = get_client()
    data_dir = Path.cwd() / "data"
    sync_manager = SyncManager(client, data_dir)

    console.print("[yellow]Baixando tarefas...[/yellow]")
    filepath = sync_manager.pull_tasks(
        project_id=project, user_id=user, include_completed=include_completed
    )
    console.print(f"[green]✓ Tarefas salvas em:[/green] [cyan]{filepath}[/cyan]")


@cli.group()
def timer():
    """Gerenciar cronômetros de tarefas (Timesheet)"""
    pass


@timer.command(name="start")
@click.option("--task", required=True, type=int, help="ID da tarefa")
@click.option("--desc", required=True, help="Descrição do trabalho")
@click.option("--model", required=True, help="Nome do modelo IA (ex: opencode)")
def timer_start(task, desc, model):
    """Iniciar cronômetro para uma tarefa usando um agente livre"""
    client = get_client()
    try:
        res = client.start_ai_task_timer(task, desc, model)
        console.print(f"[green]✓ Cronômetro iniciado![/green]")
        console.print(f"Timer ID: [bold cyan]{res['timer_id']}[/bold cyan]")
        console.print(f"Agente alocado: [yellow]{res['agent_name']}[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Erro ao iniciar cronômetro: {e}[/red]")
        sys.exit(1)


@timer.command(name="stop")
@click.option("--id", required=True, type=int, help="ID do cronômetro (Timesheet ID)")
def timer_stop(id):
    """Parar cronômetro em andamento"""
    client = get_client()
    success = client.stop_ai_task_timer(id)
    if success:
        console.print(f"[green]✓ Cronômetro {id} parado com sucesso![/green]")
    else:
        console.print(f"[red]❌ Falha ao parar o cronômetro {id}[/red]")
        sys.exit(1)


@cli.group()
def task():
    """Gerenciar e modificar tarefas"""
    pass


@task.command(name="move")
@click.option("--task", required=True, type=int, help="ID da tarefa")
@click.option("--stage", required=True, type=int, help="ID do novo estágio")
def task_move(task, stage):
    """Mover tarefa para um novo estágio"""
    client = get_client()
    success = client.update_task(task, {"stage_id": stage})
    if success:
        console.print(f"[green]✓ Tarefa {task} movida para estágio {stage}[/green]")
    else:
        console.print(f"[red]❌ Falha ao mover tarefa {task}[/red]")
        sys.exit(1)


@task.command(name="stages")
@click.option("--project", "-p", type=int, help="ID do projeto para filtrar estágios")
def list_stages(project):
    """Listar todos os estágios disponíveis"""
    client = get_client()
    stages = client.get_task_stages(project)

    if not stages:
        console.print("[yellow]Nenhum estágio encontrado.[/yellow]")
        return

    console.print("\n[bold]Estágios Disponíveis:[/bold]")
    for stage in stages:
        console.print(f"[{stage['id']}] {stage['name']}")


if __name__ == "__main__":
    cli()
