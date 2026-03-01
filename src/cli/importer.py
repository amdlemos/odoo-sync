import json
from pathlib import Path
from typing import List, Dict, Any


def load_tasks_from_file(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(
            "O arquivo de importação deve conter uma lista de tarefas (JSON array)"
        )

    return data


def normalize_task_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza campos comuns para o formato aceito por OdooClient.create_task

    Espera chaves: name, description, project_id, parent_id, stage_id, user_ids
    """
    vals = {"name": task.get("name")}
    if not vals["name"]:
        raise ValueError("Cada tarefa deve ter um campo 'name'.")

    if task.get("description"):
        vals["description"] = task["description"]
    if task.get("project_id"):
        vals["project_id"] = int(task["project_id"])
    if task.get("parent_id"):
        vals["parent_id"] = int(task["parent_id"])
    if task.get("stage_id"):
        vals["stage_id"] = int(task["stage_id"])
    if task.get("user_ids"):
        # Accept either list or string
        u = task["user_ids"]
        if isinstance(u, str):
            u = [int(x.strip()) for x in u.split(",") if x.strip()]
        vals["user_ids"] = [(6, 0, [int(x) for x in u])]

    return vals
