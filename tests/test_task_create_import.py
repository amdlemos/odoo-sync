import json
from src.cli.importer import normalize_task_payload


def test_normalize_minimal():
    t = {"name": "Tarefa X"}
    p = normalize_task_payload(t)
    assert p["name"] == "Tarefa X"


def test_normalize_full():
    t = {
        "name": "Full",
        "description": "desc",
        "project_id": "5",
        "parent_id": 10,
        "stage_id": 3,
        "user_ids": "2,3",
    }
    p = normalize_task_payload(t)
    assert p["project_id"] == 5
    assert p["parent_id"] == 10
    assert p["stage_id"] == 3
    assert p["user_ids"] == [(6, 0, [2, 3])]
