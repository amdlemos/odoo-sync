"""
Cliente para interação com Odoo 18 via OdooRPC.
Responsável por autenticação e operações CRUD em tarefas.
"""

import odoorpc
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime


class OdooClient:
    """Cliente para comunicação com Odoo via RPC"""

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
        "planned_hours",
        "effective_hours",
        "remaining_hours",
        "progress",
        "subtask_effective_hours",
        # Timesheets
        "timesheet_ids",
        "allow_timesheets",
        # Auditoria
        "create_uid",
        "write_uid",
    ]

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

        try:
            self.logger.info(
                f"Conectando ao Odoo em {host}:{port} (protocolo: {protocol})"
            )
            self.odoo = odoorpc.ODOO(host, protocol=protocol, port=port)
            self.uid = self.odoo.login(db, user, password)
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
        self, task_id: int, fields: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Buscar uma tarefa específica por ID.

        Args:
            task_id: ID da tarefa
            fields: Campos para retornar

        Returns:
            Dicionário com dados da tarefa ou None se não encontrada
        """
        tasks = self.get_tasks(domain=[("id", "=", task_id)], fields=fields, limit=1)
        return tasks[0] if tasks else None

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

    def update_task(self, task_id: int, values: Dict[str, Any]) -> bool:
        """
        Atualizar tarefa existente.

        Args:
            task_id: ID da tarefa
            values: Dicionário com valores para atualizar

        Returns:
            True se sucesso, False se falha
        """
        Task = self.env["project.task"]

        try:
            Task.write([task_id], values)
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
