"""
Cliente para interação com Odoo 18 via OdooRPC.
Responsável por autenticação e operações CRUD em tarefas.
"""

import odoorpc
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta


class OdooClient:
    """Cliente para comunicação com Odoo via RPC (stateless com cache em memória)"""

    DEFAULT_TASK_FIELDS = [
        # Identificação
        "id",
        "name",
        "description",
        "display_name",
        # Relacionamentos
        "project_id",
        "parent_id",
        "child_ids",
        "partner_id",
        "user_ids",
        "company_id",
        # Status e estágios
        "stage_id",
        "priority",
        "active",
        # Datas
        "date_deadline",
        "date_assign",
        "date_end",
        "create_date",
        "write_date",
        # Controle de tempo
        "allocated_hours",
        "effective_hours",
        "remaining_hours",
        "progress",
        "subtask_effective_hours",
        # Timesheets
        "timesheet_ids",
        "allow_timesheets",
        # Tags (many2many)
        "tag_ids",
        # Auditoria
        "create_uid",
        "write_uid",
    ]

    def get_tags(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Buscar tags (etiquetas) usadas em tarefas/projetos.

        Args:
            project_id: Se informado, filtra tags relacionadas ao projeto

        Returns:
            Lista de dicionários com campos `id` e `name`
        """
        # Model name may vary between Odoo installs / custom modules. Try common names.
        candidates = [
            "project.tags",
            "project.tag",
            "project.task.tag",
            "project.task.tags",
        ]
        for model in candidates:
            try:
                Tag = self.env[model]
            except Exception:
                continue

            domain = []
            if project_id:
                # Many2many relation is commonly `project_ids`
                domain.append(("project_ids", "in", [project_id]))

            try:
                tags = Tag.search_read(domain, ["id", "name"])
                # Normalize to simple dicts
                return tags
            except Exception:
                continue

        # If none found, return empty list
        return []

    def __init__(
        self,
        host: str,
        port: int,
        db: str,
        user: str,
        password: str,
        protocol: str = "jsonrpc+ssl",
    ):
        """
        Inicializar cliente Odoo.

        Args:
            host: Hostname do servidor Odoo
            port: Porta (443 para SSL, 8069 para HTTP)
            db: Nome do banco de dados
            user: Email/login do usuário
            password: Senha
            protocol: 'jsonrpc+ssl' ou 'jsonrpc' ou 'xmlrpc' ou 'xmlrpc+ssl'
        """
        self.logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self.db = db
        self.user = user

        # Cache em memória (TTL 5min)
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)

        try:
            self.logger.info(
                f"Conectando ao Odoo em {host}:{port} (protocolo: {protocol})"
            )
            self.odoo = odoorpc.ODOO(host, protocol=protocol, port=port)
            self.uid = self.odoo.login(db, user, password)
            if self.uid is None:
                # Se login retorna None (em versões antigas do odoorpc ou setups específicos),
                # tenta buscar o uid atual
                self.uid = self.odoo.env.uid
            self.logger.info(f"Autenticado com sucesso. UID: {self.uid}")
        except Exception as e:
            self.logger.error(f"Falha na autenticação: {e}")
            raise

    @property
    def env(self):
        """Acesso ao environment do Odoo (similar ao server-side)"""
        return self.odoo.env

    def get_current_user(self) -> Dict[str, Any]:
        """Obter informações do usuário autenticado"""
        User = self.env["res.users"]
        return User.read([self.uid], ["name", "email", "company_id"])[0]

    def get_tasks(
        self,
        domain: Optional[List] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: str = "date_deadline asc",
    ) -> List[Dict]:
        """
        Buscar tarefas do Odoo.

        Args:
            domain: Filtros no formato Odoo (ex: [('project_id', '=', 1)])
            fields: Lista de campos para retornar (None = usar DEFAULT_TASK_FIELDS)
            limit: Limite de registros (None = sem limite)
            offset: Offset para paginação
            order: Ordenação

        Returns:
            Lista de dicionários com dados das tarefas
        """
        Task = self.env["project.task"]
        domain = domain or []
        fields = fields or self.DEFAULT_TASK_FIELDS

        try:
            self.logger.debug(f"Buscando tarefas com domain: {domain}")
            tasks = Task.search_read(
                domain, fields, offset=offset, limit=limit, order=order
            )
            self.logger.info(f"Encontradas {len(tasks)} tarefas")
            return tasks
        except Exception as e:
            self.logger.error(f"Erro ao buscar tarefas: {e}")
            raise

    def get_task_by_id(
        self, task_id: int, fields: Optional[List[str]] = None, use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Buscar uma tarefa específica por ID (com cache em memória).

        Args:
            task_id: ID da tarefa
            fields: Campos para retornar
            use_cache: Se False, sempre busca do Odoo (ignora cache)

        Returns:
            Dicionário com dados da tarefa ou None se não encontrada
        """
        cache_key = f"task_{task_id}_{','.join(fields or self.DEFAULT_TASK_FIELDS)}"

        # Verificar cache
        if use_cache and cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                self.logger.debug(f"Cache hit para tarefa {task_id}")
                return cached_data

        # Buscar do Odoo
        tasks = self.get_tasks(domain=[("id", "=", task_id)], fields=fields, limit=1)
        result = tasks[0] if tasks else None

        # Atualizar cache
        if use_cache and result:
            self._cache[cache_key] = (result, datetime.now())
            self.logger.debug(f"Cache atualizado para tarefa {task_id}")

        return result

    def get_my_tasks(
        self, include_completed: bool = False, fields: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Buscar tarefas do usuário atual.

        Args:
            include_completed: Se True, inclui tarefas em estágios fechados
            fields: Campos para retornar

        Returns:
            Lista de tarefas do usuário
        """
        domain = [("user_ids", "in", [self.uid])]

        if not include_completed:
            domain.append(("stage_id.fold", "=", False))

        return self.get_tasks(domain=domain, fields=fields)

    def get_project_tasks(
        self,
        project_id: int,
        include_completed: bool = False,
        user_id: Optional[int] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Buscar tarefas de um projeto específico.

        Args:
            project_id: ID do projeto
            include_completed: Se True, inclui tarefas completadas
            user_id: Filtrar por usuário específico (None = todas)
            fields: Campos para retornar

        Returns:
            Lista de tarefas do projeto
        """
        domain = [("project_id", "=", project_id)]

        if not include_completed:
            domain.append(("stage_id.fold", "=", False))

        if user_id:
            domain.append(("user_ids", "in", [user_id]))

        return self.get_tasks(domain=domain, fields=fields)

    def create_task(self, values: Dict[str, Any]) -> int:
        """
        Criar nova tarefa no Odoo.

        Args:
            values: Dicionário com valores da tarefa

        Returns:
            ID da tarefa criada

        Exemplo:
            task_id = client.create_task({
                'name': 'Nova tarefa',
                'project_id': 1,
                'user_ids': [(6, 0, [2])],
                'date_deadline': '2026-03-15',
            })
        """
        Task = self.env["project.task"]

        try:
            task_id = Task.create(values)
            self.logger.info(f"Tarefa criada com ID: {task_id}")
            return task_id
        except Exception as e:
            self.logger.error(f"Erro ao criar tarefa: {e}")
            raise

    def get_available_agent(self, agent_employee_ids: List[int]) -> Optional[int]:
        """
        Retorna o ID do primeiro funcionário agente que não tem nenhum timer rodando.

        Args:
            agent_employee_ids: Lista de IDs de empregados que representam os agentes de IA

        Returns:
            ID do empregado agente disponível ou None se todos estiverem ocupados
        """
        # Buscamos todas as linhas de timesheet que estão rodando atualmente (unit_amount == 0)
        # e que pertencem aos nossos agentes.
        running_timers = self.env["account.analytic.line"].search_read(
            [
                ("date_time", "!=", False),
                ("employee_id", "in", agent_employee_ids),
                ("unit_amount", "=", 0),  # Timer aberto
            ],
            ["employee_id"],
        )

        # Extraímos os IDs dos funcionários que estão ocupados
        busy_employee_ids = [
            timer["employee_id"][0]
            for timer in running_timers
            if timer.get("employee_id")
        ]

        # Retornamos o primeiro agente que NÃO está na lista de ocupados
        for employee_id in agent_employee_ids:
            if employee_id not in busy_employee_ids:
                return employee_id

        return None

    def start_ai_task_timer(
        self, task_id: int, description: str, llm_model: str
    ) -> Dict[str, Any]:
        """
        Inicia um timesheet para a tarefa usando um agente de IA disponível.

        Args:
            task_id: ID da tarefa no Odoo
            description: Descrição do trabalho sendo realizado
            llm_model: Nome do modelo (ex: 'gpt-4o', 'claude-3.5-sonnet')

        Returns:
            Dicionário com timer_id, agent_id e agent_name
        """
        import os

        # 1. Pega os IDs configurados no .env (se não existir, tenta 2, 3, 4 que achamos no banco)
        agent_ids_str = os.getenv("AI_AGENT_IDS", "2,3,4")
        pool_ids = [int(id.strip()) for id in agent_ids_str.split(",") if id.strip()]

        # 2. Acha quem tá livre
        agent_id = self.get_available_agent(pool_ids)
        if not agent_id:
            raise Exception(
                "Nenhum Agente de IA está livre no momento. Todos estão com timers rodando."
            )

        # 3. Formata a assinatura
        agent_name = self.env["hr.employee"].browse(agent_id).read(["name"])[0]["name"]
        full_desc = f"{description} [{agent_name} | {llm_model}]"

        # Pega info do projeto
        task = self.env["project.task"].browse(task_id).read(["project_id"])[0]
        if not task.get("project_id"):
            raise ValueError(f"A tarefa {task_id} não tem um projeto vinculado.")
        project_id = task["project_id"][0]

        # Regra: sempre que um agente inicia uma tarefa, movemos a tarefa
        # para o estágio de desenvolvimento (se existir). Procuramos por
        # estágios com nomes comuns (pt/en) e aplicamos se encontrado.
        dev_stage = self.get_development_stage_id(project_id)
        if dev_stage:
            try:
                self.env["project.task"].browse(task_id).write({"stage_id": dev_stage})
                self.logger.info(
                    f"Tarefa {task_id} movida para estágio de desenvolvimento ({dev_stage}) antes de iniciar o timer"
                )
            except Exception as e:
                self.logger.warning(
                    f"Falha ao mover tarefa {task_id} para estágio de desenvolvimento: {e}"
                )

        # 4. Inicia o timesheet NO NOME DO AGENTE
        vals = {
            "task_id": task_id,
            "project_id": project_id,
            "employee_id": agent_id,
            "name": full_desc,
            "unit_amount": 0.0,
        }

        try:
            timer_id = self.env["account.analytic.line"].create(vals)
            self.logger.info(
                f"Timer {timer_id} iniciado para tarefa {task_id} pelo {agent_name}"
            )
            return {
                "timer_id": timer_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
            }
        except Exception as e:
            self.logger.error(f"Erro ao iniciar timer para tarefa {task_id}: {e}")
            raise

    def get_development_stage_id(self, project_id: int) -> Optional[int]:
        """
        Tenta localizar o estágio 'desenvolvimento' (ou equivalente) para um projeto.

        Procura por estágios cujo nome contenha palavras-chave como
        'desenvolv', 'desenvolvimento', 'development', 'dev'. Retorna o primeiro
        stage_id encontrado (int) ou None se não achar.
        """
        Stage = self.env["project.task.type"]
        keywords = ["desenvolv", "desenvolvimento", "development", "dev"]

        # Pesquisa por nome aproximado no contexto do projeto
        for kw in keywords:
            domain = [("name", "ilike", kw), ("project_ids", "in", [project_id])]
            stages = Stage.search_read(domain, ["id", "name"], limit=1)
            if stages:
                return stages[0]["id"]

        # Se não encontrou restringido ao projeto, busca globalmente por keyword
        for kw in keywords:
            domain = [("name", "ilike", kw)]
            stages = Stage.search_read(domain, ["id", "name"], limit=1)
            if stages:
                return stages[0]["id"]

        return None

    def stop_ai_task_timer(self, timesheet_id: int) -> bool:
        """
        Para um cronômetro específico de uma IA.

        Args:
            timesheet_id: ID do timesheet (retornado pelo start_ai_task_timer)

        Returns:
            True se sucesso, False se falha
        """
        try:
            self.env["account.analytic.line"].browse(timesheet_id).button_end_work()
            self.logger.info(f"Timer {timesheet_id} parado com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao parar timer {timesheet_id}: {e}")
            return False

    def invalidate_cache(self, task_id: Optional[int] = None):
        """
        Limpar cache em memória.

        Args:
            task_id: ID específico para invalidar. Se None, limpa todo o cache.
        """
        if task_id:
            # Remover todas as entradas que começam com task_{task_id}_
            keys_to_remove = [
                k for k in self._cache if k.startswith(f"task_{task_id}_")
            ]
            for key in keys_to_remove:
                self._cache.pop(key, None)
            self.logger.debug(f"Cache invalidado para tarefa {task_id}")
        else:
            self._cache.clear()
            self.logger.debug("Cache completo invalidado")

    def update_task(self, task_id: int, values: Dict[str, Any]) -> bool:
        """
        Atualizar tarefa existente (invalida cache automaticamente).

        Args:
            task_id: ID da tarefa
            values: Dicionário com valores para atualizar

        Returns:
            True se sucesso, False se falha
        """
        Task = self.env["project.task"]

        try:
            Task.write([task_id], values)
            self.invalidate_cache(task_id)  # Limpar cache após update
            self.logger.info(f"Tarefa {task_id} atualizada com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar tarefa {task_id}: {e}")
            return False

    def delete_task(self, task_id: int) -> bool:
        """
        Deletar tarefa.

        Args:
            task_id: ID da tarefa

        Returns:
            True se sucesso, False se falha
        """
        Task = self.env["project.task"]

        try:
            Task.unlink([task_id])
            self.logger.info(f"Tarefa {task_id} deletada com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao deletar tarefa {task_id}: {e}")
            return False

    def get_task_timesheets(self, task_id: int) -> List[Dict]:
        """
        Buscar timesheets de uma tarefa.

        Args:
            task_id: ID da tarefa

        Returns:
            Lista de timesheets
        """
        Timesheet = self.env["account.analytic.line"]

        timesheets = Timesheet.search_read(
            [("task_id", "=", task_id)],
            ["id", "date", "unit_amount", "name", "employee_id", "project_id"],
        )

        return timesheets

    def get_projects(self, domain: Optional[List] = None) -> List[Dict]:
        """
        Buscar projetos.

        Args:
            domain: Filtros Odoo

        Returns:
            Lista de projetos
        """
        Project = self.env["project.project"]
        domain = domain or []

        projects = Project.search_read(
            domain,
            ["id", "name", "active", "user_id", "partner_id", "allow_timesheets"],
        )

        return projects

    def get_task_stages(self, project_id: Optional[int] = None) -> List[Dict]:
        """
        Buscar estágios de tarefas.

        Args:
            project_id: Filtrar por projeto (None = todos)

        Returns:
            Lista de estágios
        """
        Stage = self.env["project.task.type"]
        domain = []

        if project_id:
            domain.append(("project_ids", "in", [project_id]))

        stages = Stage.search_read(
            domain, ["id", "name", "sequence", "fold", "project_ids"]
        )

        return stages

    def search_tasks(
        self,
        search_text: str,
        project_id: Optional[int] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Buscar tarefas por texto (busca em nome e descrição).

        Args:
            search_text: Texto para buscar
            project_id: Filtrar por projeto
            fields: Campos para retornar

        Returns:
            Lista de tarefas encontradas
        """
        domain = [
            "|",
            ("name", "ilike", search_text),
            ("description", "ilike", search_text),
        ]

        if project_id:
            domain = ["&"] + domain + [("project_id", "=", project_id)]

        return self.get_tasks(domain=domain, fields=fields)

    def get_task_hierarchy(self, task_id: int) -> Dict[str, Any]:
        """
        Obter hierarquia completa de uma tarefa (pais e filhos).

        Args:
            task_id: ID da tarefa

        Returns:
            Dicionário com tarefa e suas relações hierárquicas
        """
        task = self.get_task_by_id(
            task_id, fields=["id", "name", "parent_id", "child_ids"]
        )

        if not task:
            return {}

        # Buscar tarefa pai se existir
        parent = None
        if task.get("parent_id"):
            parent = self.get_task_by_id(
                task["parent_id"][0], fields=["id", "name", "parent_id"]
            )

        # Buscar subtarefas
        children = []
        if task.get("child_ids"):
            children = self.get_tasks(
                domain=[("id", "in", task["child_ids"])],
                fields=["id", "name", "stage_id", "user_ids", "child_ids"],
            )

        return {"task": task, "parent": parent, "children": children}

    def get_child_tasks(
        self, parent_task_id: int, fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna as tarefas filhas diretas de uma tarefa pai.

        Args:
            parent_task_id: ID da tarefa pai
            fields: lista de campos a serem retornados (None = DEFAULT_TASK_FIELDS)

        Returns:
            Lista de dicionários com as tarefas filhas
        """
        domain = [("parent_id", "=", parent_task_id)]
        return self.get_tasks(domain=domain, fields=fields)
