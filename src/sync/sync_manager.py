"""
Gerenciador de sincronização entre Odoo e arquivos JSON locais.
Coordena download, upload, transformação de dados e detecção de conflitos.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from .odoo_client import OdooClient
from ..models.task import (
    Task,
    TaskCollection,
    TaskHierarchy,
    TaskAssignment,
    TaskStatus,
    TaskDates,
    TaskTimeTracking,
    Timesheet,
    TaskCategorization,
    AIMetadata,
    SyncMetadata,
)


class SyncManager:
    """Orquestrador principal da sincronização Odoo <-> JSON"""

    def __init__(self, odoo_client: OdooClient, data_dir: Path):
        """
        Inicializar gerenciador de sincronização.

        Args:
            odoo_client: Cliente Odoo autenticado
            data_dir: Diretório raiz para dados
        """
        self.odoo = odoo_client
        self.data_dir = Path(data_dir)
        self.tasks_dir = self.data_dir / "tasks"
        self.metadata_dir = self.data_dir / "metadata"
        self.ai_workspace_dir = self.data_dir / "ai_workspace"
        self.logger = logging.getLogger(__name__)

        # Criar diretórios se não existirem
        for dir_path in [self.tasks_dir, self.metadata_dir, self.ai_workspace_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def pull_tasks(
        self,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        include_completed: bool = False,
    ) -> Path:
        """
        Baixar tarefas do Odoo para arquivo JSON local.

        Args:
            project_id: ID do projeto (None = todos projetos do usuário)
            user_id: ID do usuário (None = usuário autenticado atual)
            include_completed: Incluir tarefas completadas

        Returns:
            Path do arquivo JSON criado
        """
        self.logger.info(
            f"Iniciando pull de tarefas (projeto={project_id}, user={user_id})"
        )

        # Se user_id não fornecido, usar usuário autenticado
        if user_id is None:
            user_id = self.odoo.uid

        # Buscar tarefas do Odoo
        if project_id:
            raw_tasks = self.odoo.get_project_tasks(
                project_id=project_id,
                user_id=user_id,
                include_completed=include_completed,
            )
        else:
            raw_tasks = self.odoo.get_my_tasks(include_completed=include_completed)

        self.logger.info(f"Encontradas {len(raw_tasks)} tarefas no Odoo")

        # Transformar para formato estruturado
        tasks = self._transform_tasks(raw_tasks)

        # Obter informações do projeto (se aplicável)
        project_name = None
        if project_id:
            projects = self.odoo.get_projects([("id", "=", project_id)])
            project_name = projects[0]["name"] if projects else f"Projeto {project_id}"

        # Criar estrutura de dados
        task_collection = TaskCollection(
            metadata={
                "project_id": project_id,
                "project_name": project_name,
                "user_id": user_id,
                "last_sync": datetime.now().isoformat(),
                "sync_version": "1.0",
                "total_tasks": len(tasks),
                "filters_applied": {
                    "project_id": project_id,
                    "user_id": user_id,
                    "include_completed": include_completed,
                },
            },
            tasks=tasks,
        )

        # Salvar em arquivo JSON
        filename = self._generate_filename(project_id, user_id)
        filepath = self.tasks_dir / filename

        self._save_json(filepath, task_collection.model_dump(mode="json"))

        # Atualizar estado de sincronização
        self._update_sync_state(filepath, task_collection)

        self.logger.info(f"Tarefas salvas em: {filepath}")
        return filepath

    def push_changes(self, changes_file: Path, dry_run: bool = False) -> Dict[str, Any]:
        """
        Enviar mudanças aprovadas para o Odoo.

        Args:
            changes_file: Arquivo JSON com mudanças aprovadas
            dry_run: Se True, não aplica mudanças, apenas valida

        Returns:
            Resumo das operações realizadas
        """
        self.logger.info(f"Iniciando push de mudanças (dry_run={dry_run})")

        # Carregar mudanças
        with open(changes_file, "r", encoding="utf-8") as f:
            changes_data = json.load(f)

        changes = changes_data.get("changes", [])

        results = {
            "total": len(changes),
            "success": 0,
            "failed": 0,
            "conflicts": 0,
            "skipped": 0,
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "details": [],
        }

        for change in changes:
            if not change.get("approved", False):
                results["skipped"] += 1
                continue

            result = self._apply_change(change, dry_run=dry_run)
            results["details"].append(result)

            if result["status"] == "success":
                results["success"] += 1
            elif result["status"] == "conflict":
                results["conflicts"] += 1
            elif result["status"] == "failed":
                results["failed"] += 1

        # Salvar relatório
        report_file = (
            self.metadata_dir
            / f"push_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        self._save_json(report_file, results)

        self.logger.info(
            f"Push concluído: {results['success']} sucessos, {results['failed']} falhas, {results['conflicts']} conflitos"
        )
        return results

    def _apply_change(
        self, change: Dict[str, Any], dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Aplicar uma mudança individual.

        Args:
            change: Dicionário com detalhes da mudança
            dry_run: Se True, não aplica, apenas valida

        Returns:
            Resultado da operação
        """
        change_id = change.get("suggestion_id", "unknown")
        action = change.get("suggestion", {}).get("action")

        try:
            # Verificar conflitos
            if action in ["update", "delete"] and self._has_conflict(change):
                return {
                    "change_id": change_id,
                    "status": "conflict",
                    "message": "Tarefa modificada no Odoo após última sincronização",
                    "task_id": change.get("task_id"),
                }

            if dry_run:
                return {
                    "change_id": change_id,
                    "status": "success",
                    "message": "Validação OK (dry-run)",
                    "action": action,
                }

            # Aplicar mudança
            if action == "create":
                task_id = self._apply_create(change)
                return {
                    "change_id": change_id,
                    "status": "success",
                    "action": "create",
                    "task_id": task_id,
                }

            elif action == "update":
                success = self._apply_update(change)
                return {
                    "change_id": change_id,
                    "status": "success" if success else "failed",
                    "action": "update",
                    "task_id": change.get("task_id"),
                }

            elif action == "delete":
                success = self._apply_delete(change)
                return {
                    "change_id": change_id,
                    "status": "success" if success else "failed",
                    "action": "delete",
                    "task_id": change.get("task_id"),
                }

            else:
                return {
                    "change_id": change_id,
                    "status": "failed",
                    "message": f"Ação desconhecida: {action}",
                }

        except Exception as e:
            self.logger.error(f"Erro ao aplicar mudança {change_id}: {e}")
            return {"change_id": change_id, "status": "failed", "message": str(e)}

    def _apply_create(self, change: Dict[str, Any]) -> int:
        """Criar nova tarefa no Odoo"""
        values = change.get("suggestion", {}).get("values", {})
        return self.odoo.create_task(values)

    def _apply_update(self, change: Dict[str, Any]) -> bool:
        """Atualizar tarefa existente no Odoo"""
        task_id = change.get("task_id")
        values = change.get("suggestion", {}).get("changes", {})
        return self.odoo.update_task(task_id, values)

    def _apply_delete(self, change: Dict[str, Any]) -> bool:
        """Deletar tarefa do Odoo"""
        task_id = change.get("task_id")
        return self.odoo.delete_task(task_id)

    def _has_conflict(self, change: Dict[str, Any]) -> bool:
        """
        Verificar se há conflito de versão.

        Compara o write_date esperado com o atual no Odoo.
        """
        task_id = change.get("task_id")
        if not task_id:
            return False

        # Buscar versão atual no Odoo
        current_task = self.odoo.get_task_by_id(task_id, fields=["write_date"])

        if not current_task:
            return True  # Tarefa não existe mais = conflito

        # Comparar write_date
        expected_write_date = (
            change.get("suggestion", {}).get("previous_values", {}).get("write_date")
        )
        if not expected_write_date:
            # Se não tem write_date esperado, assumir que não há conflito
            return False

        current_write_date = current_task.get("write_date")

        # Conflito se datas diferentes
        return current_write_date != expected_write_date

    def _transform_tasks(self, raw_tasks: List[Dict]) -> List[Task]:
        """
        Transformar tarefas do formato Odoo para modelo estruturado.

        Args:
            raw_tasks: Lista de dicionários do Odoo

        Returns:
            Lista de objetos Task
        """
        transformed = []

        for raw_task in raw_tasks:
            try:
                task = self._transform_single_task(raw_task)
                transformed.append(task)
            except Exception as e:
                self.logger.error(
                    f"Erro ao transformar tarefa {raw_task.get('id')}: {e}"
                )
                continue

        return transformed

    def _transform_single_task(self, raw: Dict) -> Task:
        """Transformar uma única tarefa do formato Odoo"""

        # Helper para extrair ID e nome de campos Many2one
        def extract_m2o(field_value):
            if not field_value:
                return None, None
            if isinstance(field_value, (list, tuple)) and len(field_value) >= 2:
                return field_value[0], field_value[1]
            return field_value, None

        # Helper para extrair IDs e nomes de Many2many
        def extract_m2m(field_value, name_field="name"):
            ids = []
            names = []
            if isinstance(field_value, list):
                ids = field_value
            return ids, names  # Nomes precisariam de busca adicional

        # Extrair dados básicos
        task_id = raw["id"]
        name = raw.get("name", "Sem título")
        description = raw.get("description") or ""

        # Projeto
        project_id, project_name = extract_m2o(raw.get("project_id"))
        project = {"id": project_id, "name": project_name or f"Projeto {project_id}"}

        # Hierarquia
        parent_id, parent_name = extract_m2o(raw.get("parent_id"))
        child_ids = raw.get("child_ids", [])

        hierarchy = TaskHierarchy(
            parent_id=parent_id,
            parent_name=parent_name,
            child_ids=child_ids,
            child_count=len(child_ids),
            is_subtask=parent_id is not None,
            level=1 if parent_id else 0,
        )

        # Atribuição
        user_ids, _ = extract_m2m(raw.get("user_ids", []))
        assignment = TaskAssignment(user_ids=user_ids)

        # Status
        stage_id, stage_name = extract_m2o(raw.get("stage_id"))
        priority = raw.get("priority", "0")
        priority_labels = {"0": "Normal", "1": "Alta", "2": "Urgente"}

        status = TaskStatus(
            stage_id=stage_id or 0,
            stage_name=stage_name or "Sem estágio",
            priority=priority,
            priority_label=priority_labels.get(priority, "Normal"),
        )

        # Datas
        dates = TaskDates(
            date_deadline=raw.get("date_deadline"),
            date_assign=raw.get("date_assign"),
            date_end=raw.get("date_end"),
            create_date=raw.get("create_date", datetime.now().isoformat()),
            write_date=raw.get("write_date", datetime.now().isoformat()),
        )

        # Controle de tempo
        time_tracking = TaskTimeTracking(
            planned_hours=raw.get("planned_hours", 0.0),
            effective_hours=raw.get("effective_hours", 0.0),
            remaining_hours=raw.get("remaining_hours", 0.0),
            progress_percent=raw.get("progress", 0.0),
        )

        # Timesheets (simplificado - IDs apenas)
        timesheets = []

        # Categorização
        categorization = TaskCategorization(tags=[])

        # Metadados IA
        ai_metadata = AIMetadata()

        # Metadados de sincronização
        current_time = datetime.now().isoformat()
        checksum = self._calculate_checksum(raw)

        sync_metadata = SyncMetadata(
            last_sync_from_odoo=current_time,
            odoo_write_date=raw.get("write_date", current_time),
            checksum=checksum,
        )

        return Task(
            id=task_id,
            name=name,
            description=description,
            description_plain=self._html_to_plain(description),
            project=project,
            hierarchy=hierarchy,
            assignment=assignment,
            status=status,
            dates=dates,
            time_tracking=time_tracking,
            timesheets=timesheets,
            categorization=categorization,
            ai_metadata=ai_metadata,
            sync_metadata=sync_metadata,
        )

    def _calculate_checksum(self, task_data: Dict) -> str:
        """Calcular checksum MD5 dos dados da tarefa"""
        # Usar campos relevantes para detectar mudanças
        relevant_fields = [
            task_data.get("name", ""),
            task_data.get("description", ""),
            str(task_data.get("stage_id", "")),
            str(task_data.get("priority", "")),
            task_data.get("write_date", ""),
        ]

        data_str = "|".join(str(f) for f in relevant_fields)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _html_to_plain(self, html: str) -> str:
        """Converter HTML para texto plano (simplificado)"""
        if not html:
            return ""

        # Remover tags HTML básicas (implementação simples)
        import re

        text = re.sub("<[^<]+?>", "", html)
        text = text.replace("&nbsp;", " ")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")

        return text.strip()

    def _generate_filename(self, project_id: Optional[int], user_id: int) -> str:
        """Gerar nome de arquivo para tarefas"""
        if project_id:
            return f"project_{project_id}_tasks.json"
        else:
            return f"user_{user_id}_all_tasks.json"

    def _save_json(self, filepath: Path, data: Any):
        """Salvar dados em arquivo JSON"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _update_sync_state(self, tasks_file: Path, task_collection: TaskCollection):
        """Atualizar estado de sincronização"""
        state_file = self.metadata_dir / "sync_state.json"

        # Carregar estado existente ou criar novo
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        else:
            state = {"syncs": []}

        # Adicionar novo sync
        sync_record = {
            "timestamp": datetime.now().isoformat(),
            "tasks_file": str(tasks_file),
            "total_tasks": task_collection.total_tasks,
            "project_id": task_collection.metadata.get("project_id"),
            "user_id": task_collection.metadata.get("user_id"),
        }

        state["syncs"].insert(0, sync_record)  # Mais recente primeiro
        state["syncs"] = state["syncs"][:10]  # Manter últimos 10

        # Salvar
        self._save_json(state_file, state)
