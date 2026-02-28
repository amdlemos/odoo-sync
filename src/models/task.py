"""
Modelos de dados para tarefas.
Define a estrutura de dados usada para sincronização.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TaskHierarchy(BaseModel):
    """Hierarquia da tarefa (pai/filho)"""

    parent_id: Optional[int] = None
    parent_name: Optional[str] = None
    child_ids: List[int] = Field(default_factory=list)
    child_count: int = 0
    is_subtask: bool = False
    ancestor_id: Optional[int] = None
    level: int = 0


class TaskAssignment(BaseModel):
    """Atribuição de usuários/funcionários"""

    user_ids: List[int] = Field(default_factory=list)
    user_names: List[str] = Field(default_factory=list)
    employee_ids: List[int] = Field(default_factory=list)
    employee_names: List[str] = Field(default_factory=list)


class TaskStatus(BaseModel):
    """Status e estágio da tarefa"""

    stage_id: int
    stage_name: str
    state: Optional[str] = None
    is_closed: bool = False
    priority: str = "0"  # 0=Normal, 1=Alta, 2=Urgente
    priority_label: str = "Normal"


class TaskDates(BaseModel):
    """Datas relevantes da tarefa"""

    date_deadline: Optional[str] = None
    planned_date_start: Optional[str] = None
    planned_date_end: Optional[str] = None
    date_assign: Optional[str] = None
    date_end: Optional[str] = None
    create_date: str
    write_date: str


class TaskTimeTracking(BaseModel):
    """Controle de tempo"""

    planned_hours: float = 0.0
    effective_hours: float = 0.0
    remaining_hours: float = 0.0
    progress_percent: float = 0.0
    subtask_effective_hours: float = 0.0
    has_active_timer: bool = False


class Timesheet(BaseModel):
    """Linha de timesheet"""

    id: int
    date_time: str
    date_time_end: Optional[str] = None
    duration_hours: float
    description: str
    employee_id: int
    employee_name: str


class TaskCategorization(BaseModel):
    """Categorização e tags"""

    type_id: Optional[int] = None
    type_name: Optional[str] = None
    version_id: Optional[int] = None
    version_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class AIMetadata(BaseModel):
    """Metadados de análise por IA"""

    last_ai_analysis: Optional[str] = None
    ai_suggestions: List[str] = Field(default_factory=list)
    ai_priority_score: Optional[float] = None
    complexity_estimate: Optional[str] = None


class SyncMetadata(BaseModel):
    """Metadados de sincronização"""

    last_sync_from_odoo: str
    last_sync_to_odoo: Optional[str] = None
    local_modifications: bool = False
    odoo_write_date: str
    conflict_detected: bool = False
    checksum: str


class Task(BaseModel):
    """Modelo completo de tarefa"""

    # Identificação
    id: int
    external_id: Optional[str] = None
    name: str
    description: str = ""
    description_plain: str = ""

    # Projeto
    project: Dict[str, Any]

    # Estruturas aninhadas
    hierarchy: TaskHierarchy
    assignment: TaskAssignment
    status: TaskStatus
    dates: TaskDates
    time_tracking: TaskTimeTracking
    timesheets: List[Timesheet] = Field(default_factory=list)
    categorization: TaskCategorization
    ai_metadata: AIMetadata
    sync_metadata: SyncMetadata

    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "name": "Implementar autenticação OAuth",
                "description": "<p>Implementar OAuth2...</p>",
                "project": {"id": 1, "name": "Projeto CMS"},
                "hierarchy": {
                    "parent_id": None,
                    "child_ids": [43, 44],
                    "child_count": 2,
                },
                "status": {
                    "stage_id": 3,
                    "stage_name": "Em Progresso",
                    "priority": "1",
                },
            }
        }


class TaskCollection(BaseModel):
    """Coleção de tarefas com metadados"""

    metadata: Dict[str, Any]
    tasks: List[Task]

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Buscar tarefa por ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_subtasks(self, parent_id: int) -> List[Task]:
        """Obter todas as subtarefas de uma tarefa"""
        return [task for task in self.tasks if task.hierarchy.parent_id == parent_id]

    def get_top_level_tasks(self) -> List[Task]:
        """Obter apenas tarefas de nível superior (sem pai)"""
        return [task for task in self.tasks if not task.hierarchy.is_subtask]
