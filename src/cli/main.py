import sys
import os
from pathlib import Path
import click
from dotenv import load_dotenv
import json
import shutil
from datetime import datetime
from rich.console import Console

# Ensure src modules can be found
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.sync.odoo_client import OdooClient

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
@click.option(
    "--migrate",
    is_flag=True,
    help="Migrar .odoo-agent-rules.md legado para o novo diretório .odoo-agent-rules/",
)
def init(migrate):
    """Inicializar configuração no diretório atual"""
    local_env = Path.cwd() / ".odoo-sync.env"

    # New layout: a project-local directory holding agent rules and full specs
    rules_dir = Path.cwd() / ".odoo-agent-rules"
    main_file = rules_dir / "main.md"
    specs_file = rules_dir / "specs.md"
    legacy_file = Path.cwd() / ".odoo-agent-rules.md"

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

    # Create rules directory if missing
    if not rules_dir.exists():
        rules_dir.mkdir(parents=True, exist_ok=True)

    # If a legacy single-file prompt exists, offer to migrate when requested
    if legacy_file.exists() and migrate:
        # Migrate legacy file into rules/main.md and move a backup of legacy file
        legacy_content = legacy_file.read_text(encoding="utf-8")
        if not main_file.exists():
            main_file.write_text(legacy_content, encoding="utf-8")
            # move legacy into the new directory as a backup
            backup = rules_dir / "legacy_main.md"
            legacy_file.rename(backup)
            console.print(
                f"[green]✓ Migrated legacy {legacy_file} -> {main_file} (backup: {backup})[/green]"
            )
        else:
            # main already exists; keep legacy as backup inside rules dir
            backup = rules_dir / "legacy_main.md"
            legacy_file.rename(backup)
            console.print(
                f"[yellow]Aviso: {main_file} já existe; legacy salvo em {backup}[/yellow]"
            )

    # Create main.md from packaged AI_SYSTEM_PROMPT.md if available, otherwise write a default
    if not main_file.exists():
        packaged_prompt = Path(__file__).parent.parent.parent / "AI_SYSTEM_PROMPT.md"
        if packaged_prompt.exists():
            try:
                shutil.copyfile(packaged_prompt, main_file)
                console.print(
                    f"[green]✓ Copiado {packaged_prompt} -> {main_file}[/green]"
                )
            except Exception:
                console.print(
                    f"[yellow]Aviso: falha ao copiar {packaged_prompt} para {main_file}[/yellow]"
                )
                # fallback to a minimal default
                default = "# Regras do Agente — Odoo Task Sync (em Português)\n\nIdioma obrigatório: Todas as tarefas, títulos e descrições devem estar em Português (pt-BR).\n"
                main_file.write_text(default, encoding="utf-8")
        else:
            # fallback to a minimal default if packaged prompt not available
            default = "# Regras do Agente — Odoo Task Sync (em Português)\n\nIdioma obrigatório: Todas as tarefas, títulos e descrições devem estar em Português (pt-BR).\n"
            main_file.write_text(default, encoding="utf-8")

    # Copy packaged full HTML spec into specs.md if available and missing
    packaged_spec = Path(__file__).parent.parent.parent / "docs" / "task-html-spec.md"
    if packaged_spec.exists() and not specs_file.exists():
        try:
            shutil.copyfile(packaged_spec, specs_file)
            console.print(f"[green]✓ Specs copiadas para {specs_file}[/green]")
        except Exception:
            console.print(
                f"[yellow]Aviso: falha ao copiar specs de {packaged_spec}[/yellow]"
            )

    console.print(f"[green]✓ Projeto inicializado![/green]")
    console.print(f"Edite [cyan]{local_env}[/cyan] para definir o ID do projeto.")
    console.print(f"Instruções para Agentes IA: [cyan]{main_file}[/cyan]")
    if specs_file.exists():
        console.print(f"Especificação completa: [cyan]{specs_file}[/cyan]")

    # Add .odoo-agent-rules/ to .gitignore when in a git repo (append only)
    git_dir = Path.cwd() / ".git"
    if git_dir.exists():
        gitignore = Path.cwd() / ".gitignore"
        entry = ".odoo-agent-rules/"
        if gitignore.exists():
            gi_text = gitignore.read_text(encoding="utf-8")
            if entry not in gi_text:
                with open(gitignore, "a") as f:
                    if not gi_text.endswith("\n"):
                        f.write("\n")
                    f.write(entry + "\n")
                console.print(f"[green]✓ Adicionado {entry} ao .gitignore[/green]")
        else:
            gitignore.write_text(entry + "\n", encoding="utf-8")
            console.print(f"[green]✓ Criado .gitignore e adicionado {entry}[/green]")


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


@cli.group()
def doc():
    """Mostrar documentação empacotada ou local"""
    pass


@doc.command(name="rules")
def doc_rules():
    """Imprimir regras/especificação HTML usadas para descrições de tarefas"""
    rules_dir = Path.cwd() / ".odoo-agent-rules"
    specs_file = rules_dir / "specs.md"
    main_file = rules_dir / "main.md"

    if specs_file.exists():
        content = specs_file.read_text(encoding="utf-8")
        console.print(f"[bold]Project specs: {specs_file}[/bold]\n")
        console.print(content)
        return

    # Fallback to packaged docs
    packaged_spec = Path(__file__).parent.parent.parent / "docs" / "task-html-spec.md"
    if packaged_spec.exists():
        content = packaged_spec.read_text(encoding="utf-8")
        console.print(f"[bold]Packaged specs: {packaged_spec}[/bold]\n")
        console.print(content)
        return

    # If neither available, show concise main.md if present
    if main_file.exists():
        content = main_file.read_text(encoding="utf-8")
        console.print(f"[bold]Project rules: {main_file}[/bold]\n")
        console.print(content)
        return

    console.print(
        "[yellow]Nenhuma especificação encontrada. Rode `odoo-sync init` para gerar arquivos locais ou instale o pacote com os docs incluídos.[/yellow]"
    )


@cli.command()
@click.option(
    "--rules",
    is_flag=True,
    help="Atualizar arquivos de regras locais (.odoo-agent-rules/) a partir dos arquivos empacotados",
)
@click.option("--yes", "-y", is_flag=True, help="Sobrescrever sem perguntar")
def update(rules, yes):
    """Atualizar artefatos locais a partir dos arquivos empacotados no pacote"""
    if not rules:
        console.print(
            "[yellow]Nada para atualizar. Use --rules para atualizar as regras do agente.[/yellow]"
        )
        return

    rules_dir = Path.cwd() / ".odoo-agent-rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    packaged_prompt = Path(__file__).parent.parent.parent / "AI_SYSTEM_PROMPT.md"
    packaged_spec = Path(__file__).parent.parent.parent / "docs" / "task-html-spec.md"

    targets = [
        (packaged_prompt, rules_dir / "main.md"),
        (packaged_spec, rules_dir / "specs.md"),
    ]

    for src, dst in targets:
        if not src.exists():
            console.print(
                f"[yellow]Aviso: arquivo empacotado não encontrado: {src} (pulando)[/yellow]"
            )
            continue

        do_copy = True
        if dst.exists() and not yes:
            prompt = f"{dst} já existe. Deseja sobrescrever com {src.name}?"
            do_copy = click.confirm(prompt, default=False)

        if not do_copy:
            console.print(f"[yellow]Pulando {dst}[/yellow]")
            continue

        # backup existing
        if dst.exists():
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            backup = dst.with_name(dst.name + f".bak.{ts}")
            try:
                shutil.copyfile(dst, backup)
                console.print(f"[green]✓ Backup criado: {backup}[/green]")
            except Exception:
                console.print(f"[yellow]Aviso: falha ao criar backup de {dst}[/yellow]")

        try:
            shutil.copyfile(src, dst)
            console.print(f"[green]✓ Atualizado {dst} a partir de {src.name}[/green]")
        except Exception as e:
            console.print(f"[red]Erro ao copiar {src} -> {dst}: {e}[/red]")


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


@task.command(name="show")
@click.option("--task", "-t", required=True, type=int, help="ID da tarefa")
@click.option("--json", "-j", "output_json", is_flag=True, help="Saída em formato JSON")
def task_show(task, output_json):
    """Mostrar detalhes completos de uma tarefa (busca ao vivo no Odoo)"""
    client = get_client()

    try:
        task_data = client.get_task_by_id(task)
    except Exception as e:
        console.print(f"[red]❌ Erro ao buscar tarefa: {e}[/red]")
        sys.exit(1)

    if not task_data:
        console.print(f"[red]❌ Tarefa {task} não encontrada.[/red]")
        sys.exit(1)

    if output_json:
        console.print(json.dumps(task_data, indent=2, ensure_ascii=False, default=str))
        return

    # Pretty print
    console.print(f"\n[bold cyan]Tarefa #{task_data['id']}[/bold cyan]")
    console.print(f"[bold]{task_data['name']}[/bold]\n")

    # Projeto
    if task_data.get("project_id"):
        project_name = (
            task_data["project_id"][1]
            if isinstance(task_data["project_id"], (list, tuple))
            else task_data["project_id"]
        )
        console.print(f"📁 Projeto: {project_name}")

    # Stage
    if task_data.get("stage_id"):
        stage_name = (
            task_data["stage_id"][1]
            if isinstance(task_data["stage_id"], (list, tuple))
            else task_data["stage_id"]
        )
        console.print(f"📊 Estágio: {stage_name}")

    # Atribuídos
    if task_data.get("user_ids"):
        console.print(f"👥 Atribuído a: {len(task_data['user_ids'])} usuário(s)")

    # Datas
    if task_data.get("date_deadline"):
        console.print(f"📅 Prazo: {task_data['date_deadline']}")

    # Horas
    allocated = task_data.get("allocated_hours", 0.0)
    effective = task_data.get("effective_hours", 0.0)
    remaining = task_data.get("remaining_hours", 0.0)
    if allocated > 0 or effective > 0:
        console.print(
            f"⏱️  Horas: {effective:.1f}h / {allocated:.1f}h (restante: {remaining:.1f}h)"
        )

    # Parent/Children
    if task_data.get("parent_id"):
        parent_name = (
            task_data["parent_id"][1]
            if isinstance(task_data["parent_id"], (list, tuple))
            else f"ID {task_data['parent_id']}"
        )
        console.print(f"⬆️  Tarefa pai: {parent_name}")

    if task_data.get("child_ids"):
        console.print(f"⬇️  Subtarefas: {len(task_data['child_ids'])}")

    # Descrição
    description = task_data.get("description") or ""
    if description:
        console.print(f"\n[bold]Descrição:[/bold]")
        # Remove HTML tags simplificadamente
        import re

        plain = re.sub("<[^<]+?>", "", description)
        plain = (
            plain.replace("&nbsp;", " ")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
        )
        console.print(plain.strip()[:500] + ("..." if len(plain) > 500 else ""))


@task.command(name="list")
@click.option("--project", "-p", type=int, help="Filtrar por ID do projeto")
@click.option("--stage", "-s", type=int, help="Filtrar por ID do estágio")
@click.option("--user", "-u", type=int, help="Filtrar por usuário atribuído")
@click.option("--limit", "-l", default=50, help="Limite de resultados (padrão: 50)")
@click.option("--json", "-j", "output_json", is_flag=True, help="Saída em formato JSON")
def task_list(project, stage, user, limit, output_json):
    """Listar tarefas (query ao vivo no Odoo)"""
    load_config()
    client = get_client()

    # Construir domain
    domain = []
    if project:
        domain.append(("project_id", "=", project))
    if stage:
        domain.append(("stage_id", "=", stage))
    if user:
        domain.append(("user_ids", "in", [user]))

    # Se nenhum filtro, usar projeto padrão do .env
    if not domain and os.getenv("DEFAULT_PROJECT_ID"):
        try:
            default_project = int(os.getenv("DEFAULT_PROJECT_ID"))
            domain.append(("project_id", "=", default_project))
            console.print(f"[yellow]Usando projeto padrão: {default_project}[/yellow]")
        except ValueError:
            pass

    try:
        tasks = client.get_tasks(domain=domain, limit=limit)
    except Exception as e:
        console.print(f"[red]❌ Erro ao listar tarefas: {e}[/red]")
        sys.exit(1)

    if not tasks:
        console.print("[yellow]Nenhuma tarefa encontrada.[/yellow]")
        return

    if output_json:
        console.print(json.dumps(tasks, indent=2, ensure_ascii=False, default=str))
        return

    # Pretty print
    console.print(f"\n[bold]Encontradas {len(tasks)} tarefa(s):[/bold]\n")
    for t in tasks:
        tid = t.get("id")
        name = t.get("name") or t.get("display_name") or "<sem nome>"
        stage = t.get("stage_id")
        stage_name = (
            stage[1] if isinstance(stage, (list, tuple)) and len(stage) > 1 else "?"
        )

        console.print(f"[cyan][{tid}][/cyan] {name}")
        console.print(f"  └─ Estágio: {stage_name}\n")


@task.command(name="children")
@click.option("--task", "-t", required=True, type=int, help="ID da tarefa pai")
@click.option(
    "--fields",
    "-f",
    multiple=True,
    help="Campos a retornar (use múltiplas vezes). Se ausente, retorna campos padrões.",
)
@click.option(
    "--json",
    "-j",
    "is_json",
    is_flag=True,
    help="Imprimir JSON cru com as tarefas filhas",
)
def task_children(task, fields, is_json):
    """Listar tarefas filhas diretas de uma tarefa pai"""
    client = get_client()
    fields_list = list(fields) if fields else None

    try:
        children = client.get_child_tasks(task, fields=fields_list)
    except Exception as e:
        console.print(f"[red]❌ Erro ao buscar tarefas filhas: {e}[/red]")
        sys.exit(1)

    if not children:
        console.print("[yellow]Nenhuma tarefa filha encontrada.[/yellow]")
        return

    if is_json:
        console.print(json.dumps(children, indent=2, ensure_ascii=False))
        return

    console.print("\n[bold]Tarefas Filhas:[/bold]")
    for c in children:
        tid = c.get("id")
        name = c.get("name") or c.get("display_name") or "<sem nome>"
        stage = c.get("stage_id")
        if isinstance(stage, (list, tuple)):
            stage = stage[0] if stage else None
        console.print(f"[{tid}] {name} (stage: {stage})")


@task.command(name="create")
@click.option("--name", required=True, help="Nome da tarefa")
@click.option("--desc", default="", help="Descrição da tarefa")
@click.option("--project", "-p", type=int, help="ID do projeto")
@click.option("--parent", type=int, help="ID da tarefa pai (opcional)")
@click.option("--stage", type=int, help="ID do estágio (opcional)")
@click.option(
    "--assign",
    "-a",
    type=int,
    multiple=True,
    help="IDs de usuários para atribuir (use múltiplas vezes)",
)
@click.option("--dry-run", is_flag=True, help="Mostrar payload e não criar a tarefa")
def task_create(name, desc, project, parent, stage, assign, dry_run):
    """Criar uma nova tarefa no Odoo a partir da linha de comando"""
    # Carrega configuração para obter DEFAULT_PROJECT_ID se necessário
    load_config()

    # Se project não foi informado na CLI, tenta pegar do .odoo-sync.env
    if not project and os.getenv("DEFAULT_PROJECT_ID"):
        try:
            project = int(os.getenv("DEFAULT_PROJECT_ID"))
        except ValueError:
            project = None

    values = {"name": name}
    if desc:
        values["description"] = desc
    if project:
        values["project_id"] = project
    if parent:
        values["parent_id"] = parent
    if stage:
        values["stage_id"] = stage
    if assign:
        # user_ids uses the Odoo (6, 0, [ids]) command for many2many replacement
        values["user_ids"] = [(6, 0, list(assign))]

    if dry_run:
        console.print("[yellow]DRY RUN - Payload preparado para criação:[/yellow]")
        console.print(values)
        return

    client = get_client()

    try:
        task_id = client.create_task(values)
        console.print(
            f"[green]✓ Tarefa criada com sucesso! ID: [bold cyan]{task_id}[/bold cyan][/green]"
        )
    except Exception as e:
        console.print(f"[red]❌ Erro ao criar tarefa: {e}[/red]")
        sys.exit(1)


@task.command(name="update")
@click.option(
    "--task", "-t", required=True, type=int, help="ID da tarefa a ser atualizada"
)
@click.option("--name", help="Novo nome da tarefa")
@click.option("--desc", help="Nova descrição")
@click.option("--project", "-p", type=int, help="ID do projeto")
@click.option("--parent", help="ID da tarefa pai. Use 'none' para desvincular")
@click.option(
    "--clear-parent",
    is_flag=True,
    help="Remover vínculo de parent_id (equivalente a --parent none)",
)
@click.option("--stage", type=int, help="ID do estágio")
@click.option(
    "--assign",
    "-a",
    type=int,
    multiple=True,
    help="IDs de usuários para atribuir (substitui os atuais)",
)
@click.option(
    "--clear-assign",
    is_flag=True,
    help="Remove todos os usuários atribuídos (user_ids=[])",
)
@click.option("--dry-run", is_flag=True, help="Mostrar payload e não executar")
def task_update(
    task,
    name,
    desc,
    project,
    parent,
    clear_parent,
    stage,
    assign,
    clear_assign,
    dry_run,
):
    """Atualizar campos de uma tarefa existente. Permite desvincular parent_id."""
    load_config()

    values = {}
    if name is not None:
        values["name"] = name
    if desc is not None:
        values["description"] = desc
    if project is not None:
        values["project_id"] = project
    # parent handling: explicit clear flag has precedence
    if clear_parent:
        values["parent_id"] = False
    elif parent is not None:
        # allow 'none' or 'null' to clear
        if str(parent).lower() in ("none", "null", "false", "0", ""):
            values["parent_id"] = False
        else:
            try:
                values["parent_id"] = int(parent)
            except ValueError:
                console.print(f"[red]Valor inválido para --parent: {parent}[/red]")
                sys.exit(1)

    if stage is not None:
        values["stage_id"] = stage

    if clear_assign:
        values["user_ids"] = [(6, 0, [])]
    elif assign:
        values["user_ids"] = [(6, 0, list(assign))]

    if not values:
        console.print(
            "[yellow]Nenhum campo informado para atualizar. Nada a fazer.[/yellow]"
        )
        return

    if dry_run:
        console.print("[yellow]DRY RUN - Payload de atualização:[/yellow]")
        console.print(values)
        return

    client = get_client()
    try:
        success = client.update_task(task, values)
        if success:
            console.print(f"[green]✓ Tarefa {task} atualizada com sucesso[/green]")
        else:
            console.print(f"[red]❌ Falha ao atualizar a tarefa {task}[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Erro ao atualizar tarefa: {e}[/red]")
        sys.exit(1)


@task.command(name="delete")
@click.option(
    "--task", "-t", required=True, type=int, help="ID da tarefa a ser deletada"
)
@click.option("--yes", "-y", is_flag=True, help="Confirmar exclusão sem perguntar")
def task_delete(task, yes):
    """Deletar/arquivar uma tarefa no Odoo"""
    load_config()

    if not yes:
        if not click.confirm(
            f"Tem certeza que deseja deletar a tarefa {task}? Esta ação não pode ser desfeita."
        ):
            console.print("[yellow]Operação cancelada pelo usuário.[/yellow]")
            return

    client = get_client()
    try:
        success = client.delete_task(task)
        if success:
            console.print(f"[green]✓ Tarefa {task} deletada com sucesso.[/green]")
        else:
            console.print(f"[red]❌ Falha ao deletar a tarefa {task}[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Erro ao deletar tarefa: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
