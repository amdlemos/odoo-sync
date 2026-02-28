"""
Interface para agentes de IA processarem tarefas.
Facilita leitura, análise e geração de sugestões.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging


class AIAgentInterface:
    """Interface simplificada para agentes de IA consumirem tarefas"""

    def __init__(self, tasks_file: Path):
        """
        Inicializar interface.

        Args:
            tasks_file: Arquivo JSON com tarefas sincronizadas
        """
        self.tasks_file = Path(tasks_file)
        self.logger = logging.getLogger(__name__)
        self.tasks_data = self._load_tasks()

    def _load_tasks(self) -> Dict:
        """Carregar tarefas do arquivo JSON"""
        with open(self.tasks_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_tasks_summary(self, format: str = "markdown") -> str:
        """
        Obter resumo das tarefas em texto legível para IA.

        Args:
            format: 'markdown' ou 'plain'

        Returns:
            Texto formatado com resumo das tarefas
        """
        metadata = self.tasks_data.get("metadata", {})
        tasks = self.tasks_data.get("tasks", [])

        if format == "markdown":
            return self._format_markdown(metadata, tasks)
        else:
            return self._format_plain(metadata, tasks)

    def _format_markdown(self, metadata: Dict, tasks: List[Dict]) -> str:
        """Formatar resumo em Markdown"""
        lines = []

        # Cabeçalho
        project_name = metadata.get("project_name", "Todas as Tarefas")
        lines.append(f"# {project_name}\n")
        lines.append(f"**Total de tarefas:** {metadata.get('total_tasks', 0)}")
        lines.append(f"**Última sincronização:** {metadata.get('last_sync', 'N/A')}\n")

        # Agrupar por status
        by_status = {}
        for task in tasks:
            status = task.get("status", {}).get("stage_name", "Sem estágio")
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(task)

        # Listar tarefas por estágio
        for status, status_tasks in by_status.items():
            lines.append(f"\n## {status} ({len(status_tasks)} tarefas)\n")

            for task in status_tasks:
                task_id = task.get("id")
                name = task.get("name")
                priority = task.get("status", {}).get("priority_label", "Normal")
                deadline = task.get("dates", {}).get("date_deadline", "Sem prazo")
                progress = task.get("time_tracking", {}).get("progress_percent", 0)

                # Ícone de prioridade
                priority_icon = {"Normal": "⚪", "Alta": "🟡", "Urgente": "🔴"}.get(
                    priority, "⚪"
                )

                lines.append(f"### {priority_icon} [{task_id}] {name}")
                lines.append(f"- **Prioridade:** {priority}")
                lines.append(f"- **Prazo:** {deadline}")
                lines.append(f"- **Progresso:** {progress:.1f}%")

                # Atribuição
                assignment = task.get("assignment", {})
                if assignment.get("user_names"):
                    users = ", ".join(assignment["user_names"])
                    lines.append(f"- **Responsável:** {users}")

                # Hierarquia
                hierarchy = task.get("hierarchy", {})
                if hierarchy.get("is_subtask"):
                    lines.append(f"  └─ Subtarefa de: {hierarchy.get('parent_name')}")

                if hierarchy.get("child_count", 0) > 0:
                    lines.append(f"  └─ {hierarchy['child_count']} subtarefas")

                lines.append("")  # Linha em branco

        return "\n".join(lines)

    def _format_plain(self, metadata: Dict, tasks: List[Dict]) -> str:
        """Formatar resumo em texto plano"""
        lines = []

        lines.append(f"PROJETO: {metadata.get('project_name', 'N/A')}")
        lines.append(f"Total de tarefas: {metadata.get('total_tasks', 0)}")
        lines.append(f"Sincronizado em: {metadata.get('last_sync', 'N/A')}")
        lines.append("")

        for i, task in enumerate(tasks, 1):
            lines.append(f"{i}. [{task.get('id')}] {task.get('name')}")
            lines.append(
                f"   Status: {task.get('status', {}).get('stage_name', 'N/A')}"
            )
            lines.append(
                f"   Prioridade: {task.get('status', {}).get('priority_label', 'Normal')}"
            )
            lines.append(
                f"   Prazo: {task.get('dates', {}).get('date_deadline', 'Sem prazo')}"
            )
            lines.append("")

        return "\n".join(lines)

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """
        Buscar tarefa específica por ID.

        Args:
            task_id: ID da tarefa

        Returns:
            Dicionário com dados da tarefa ou None
        """
        for task in self.tasks_data.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None

    def get_tasks_by_status(self, stage_name: str) -> List[Dict]:
        """
        Filtrar tarefas por estágio.

        Args:
            stage_name: Nome do estágio

        Returns:
            Lista de tarefas naquele estágio
        """
        return [
            task
            for task in self.tasks_data.get("tasks", [])
            if task.get("status", {}).get("stage_name") == stage_name
        ]

    def get_overdue_tasks(self) -> List[Dict]:
        """
        Obter tarefas atrasadas.

        Returns:
            Lista de tarefas com prazo vencido
        """
        from datetime import date

        today = date.today().isoformat()

        overdue = []
        for task in self.tasks_data.get("tasks", []):
            deadline = task.get("dates", {}).get("date_deadline")
            is_closed = task.get("status", {}).get("is_closed", False)

            if deadline and deadline < today and not is_closed:
                overdue.append(task)

        return overdue

    def get_tasks_without_assignee(self) -> List[Dict]:
        """Obter tarefas sem responsável"""
        return [
            task
            for task in self.tasks_data.get("tasks", [])
            if not task.get("assignment", {}).get("user_ids")
        ]

    def get_tasks_with_empty_description(self) -> List[Dict]:
        """Obter tarefas com descrição vazia"""
        return [
            task
            for task in self.tasks_data.get("tasks", [])
            if not task.get("description_plain", "").strip()
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Obter estatísticas das tarefas.

        Returns:
            Dicionário com estatísticas gerais
        """
        tasks = self.tasks_data.get("tasks", [])

        total = len(tasks)
        by_priority = {"Normal": 0, "Alta": 0, "Urgente": 0}
        by_status = {}
        total_planned = 0.0
        total_effective = 0.0
        with_deadline = 0
        overdue = len(self.get_overdue_tasks())
        without_assignee = len(self.get_tasks_without_assignee())
        empty_description = len(self.get_tasks_with_empty_description())

        for task in tasks:
            # Contar por prioridade
            priority = task.get("status", {}).get("priority_label", "Normal")
            by_priority[priority] = by_priority.get(priority, 0) + 1

            # Contar por status
            status = task.get("status", {}).get("stage_name", "Desconhecido")
            by_status[status] = by_status.get(status, 0) + 1

            # Horas
            total_planned += task.get("time_tracking", {}).get("planned_hours", 0.0)
            total_effective += task.get("time_tracking", {}).get("effective_hours", 0.0)

            # Com prazo
            if task.get("dates", {}).get("date_deadline"):
                with_deadline += 1

        return {
            "total_tasks": total,
            "by_priority": by_priority,
            "by_status": by_status,
            "total_planned_hours": total_planned,
            "total_effective_hours": total_effective,
            "avg_progress": sum(
                task.get("time_tracking", {}).get("progress_percent", 0)
                for task in tasks
            )
            / total
            if total > 0
            else 0,
            "tasks_with_deadline": with_deadline,
            "tasks_overdue": overdue,
            "tasks_without_assignee": without_assignee,
            "tasks_empty_description": empty_description,
        }

    def save_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        output_file: Optional[Path] = None,
        agent_name: str = "AI Agent",
    ) -> Path:
        """
        Salvar sugestões geradas pela IA.

        Args:
            suggestions: Lista de sugestões
            output_file: Arquivo de saída (None = usar padrão)
            agent_name: Nome do agente que gerou as sugestões

        Returns:
            Path do arquivo criado
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = (
                self.tasks_file.parent.parent
                / "ai_workspace"
                / f"suggestions_{timestamp}.json"
            )

        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "ai_agent": agent_name,
                "tasks_file": str(self.tasks_file),
                "total_suggestions": len(suggestions),
            },
            "suggestions": suggestions,
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Sugestões salvas em: {output_file}")
        return output_file

    def export_for_ai_prompt(self, include_full_data: bool = True) -> str:
        """
        Exportar dados em formato otimizado para prompt de IA.

        Args:
            include_full_data: Se True, inclui JSON completo

        Returns:
            Texto formatado para uso em prompt
        """
        summary = self.get_tasks_summary(format="markdown")
        stats = self.get_statistics()

        prompt_data = [
            "# DADOS DAS TAREFAS PARA ANÁLISE\n",
            "## Resumo Visual\n",
            summary,
            "\n## Estatísticas\n",
            f"- Total de tarefas: {stats['total_tasks']}",
            f"- Horas planejadas: {stats['total_planned_hours']:.1f}h",
            f"- Horas efetivas: {stats['total_effective_hours']:.1f}h",
            f"- Progresso médio: {stats['avg_progress']:.1f}%",
            f"- Tarefas atrasadas: {stats['tasks_overdue']}",
            f"- Tarefas sem responsável: {stats['tasks_without_assignee']}",
            f"- Tarefas sem descrição: {stats['tasks_empty_description']}",
        ]

        if include_full_data:
            prompt_data.append("\n## Dados Completos (JSON)\n")
            prompt_data.append("```json")
            prompt_data.append(
                json.dumps(self.tasks_data, indent=2, ensure_ascii=False)
            )
            prompt_data.append("```")

        return "\n".join(prompt_data)
