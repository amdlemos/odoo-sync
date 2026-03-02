"""
Parser de Markdown para tarefas do Odoo.

Suporta:
- Checkboxes: - [ ] e - [x]
- IDs do Odoo: (#123)
- Hierarquia por indentação
- Descrições inline (linhas indentadas após tarefa)
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MarkdownTask:
    """Representa uma tarefa parseada do Markdown"""

    name: str
    odoo_id: Optional[int] = None
    completed: bool = False
    level: int = 0  # Indentação (0=root, 1=child, 2=grandchild...)
    section: str = ""
    description: str = ""
    line_number: int = 0


def parse_tasks_from_markdown(content: str) -> List[MarkdownTask]:
    """
    Parse Markdown e extrai tarefas.

    Formato esperado:
    - [ ] Tarefa sem ID
    - [ ] Tarefa com ID (#123)
    - [x] Tarefa concluída (#124)
      - Detalhes técnicos (descrição inline)
      - Mais detalhes

    Args:
        content: Conteúdo do arquivo Markdown

    Returns:
        Lista de MarkdownTask
    """
    lines = content.split("\n")
    tasks = []
    current_section = ""
    current_task = None

    # Regex patterns
    section_pattern = re.compile(r"^#{1,6}\s+(.+)$")  # ## Seção
    task_pattern = re.compile(r"^(\s*)- \[([ x])\]\s+(.+)$")  # - [ ] Tarefa
    odoo_id_pattern = re.compile(r"\(#(\d+)\)")  # (#123)

    for line_num, line in enumerate(lines, start=1):
        # Detectar seção
        section_match = section_pattern.match(line)
        if section_match:
            current_section = section_match.group(1).strip()
            current_task = None  # Reset descrição
            continue

        # Detectar tarefa
        task_match = task_pattern.match(line)
        if task_match:
            indent = task_match.group(1)
            completed = task_match.group(2) == "x"
            task_text = task_match.group(3).strip()

            # Calcular nível de indentação (2 espaços ou 1 tab = 1 nível)
            level = len(indent.replace("\t", "  ")) // 2

            # Extrair ID do Odoo se presente
            odoo_id = None
            odoo_match = odoo_id_pattern.search(task_text)
            if odoo_match:
                odoo_id = int(odoo_match.group(1))
                # Remover (#ID) do nome da tarefa
                task_text = odoo_id_pattern.sub("", task_text).strip()
                # Remover traços finais (ex: "Tarefa - " → "Tarefa")
                task_text = task_text.rstrip(" -")

            current_task = MarkdownTask(
                name=task_text,
                odoo_id=odoo_id,
                completed=completed,
                level=level,
                section=current_section,
                description="",
                line_number=line_num,
            )
            tasks.append(current_task)
            continue

        # Linhas após tarefa são descrição (se indentadas)
        if current_task and line.strip() and not line.strip().startswith("#"):
            # Verificar se está mais indentada que a tarefa
            task_indent_level = current_task.level * 2
            line_indent = len(line) - len(line.lstrip())

            if line_indent > task_indent_level:
                # É descrição da tarefa
                desc_line = line.strip()
                if desc_line.startswith("- "):
                    desc_line = desc_line[2:]  # Remove marcador de lista
                if current_task.description:
                    current_task.description += "\n" + desc_line
                else:
                    current_task.description = desc_line

    return tasks


def build_hierarchy(tasks: List[MarkdownTask]) -> List[Dict[str, Any]]:
    """
    Constrói hierarquia parent/child baseado nos níveis de indentação.

    Args:
        tasks: Lista de MarkdownTask

    Returns:
        Lista de dicts com estrutura hierárquica:
        {
            'task': MarkdownTask,
            'parent': MarkdownTask | None,
            'children': List[MarkdownTask]
        }
    """
    hierarchy = []
    parent_stack = []  # Stack para rastrear parents por nível

    for task in tasks:
        # Ajustar stack ao nível atual
        while len(parent_stack) > task.level:
            parent_stack.pop()

        # Parent é o último item no stack (se houver)
        parent = parent_stack[-1] if parent_stack else None

        # Adicionar à hierarquia
        hierarchy.append({"task": task, "parent": parent, "children": []})

        # Se é parent, atualizar children do parent
        if parent:
            for item in hierarchy:
                if item["task"] == parent:
                    item["children"].append(task)
                    break

        # Adicionar ao stack para ser parent de próximos
        if task.level == len(parent_stack):
            parent_stack.append(task)

    return hierarchy


def format_task_to_markdown(
    task_name: str,
    odoo_id: Optional[int] = None,
    completed: bool = False,
    level: int = 0,
    description: str = "",
) -> str:
    """
    Formata uma tarefa para Markdown.

    Args:
        task_name: Nome da tarefa
        odoo_id: ID do Odoo (opcional)
        completed: Se está concluída
        level: Nível de indentação (0=root, 1=child)
        description: Descrição inline (opcional)

    Returns:
        String formatada em Markdown
    """
    indent = "  " * level
    checkbox = "[x]" if completed else "[ ]"
    id_suffix = f" (#{odoo_id})" if odoo_id else ""

    result = f"{indent}- {checkbox} {task_name}{id_suffix}"

    if description:
        desc_lines = description.split("\n")
        desc_indent = "  " * (level + 1)
        for line in desc_lines:
            result += f"\n{desc_indent}- {line}"

    return result


def find_task_by_name(
    tasks: List[MarkdownTask], name: str, threshold: float = 0.8
) -> Optional[MarkdownTask]:
    """
    Encontra tarefa por nome (match fuzzy).

    Args:
        tasks: Lista de tarefas
        name: Nome a buscar
        threshold: Similaridade mínima (0-1)

    Returns:
        MarkdownTask encontrada ou None
    """
    from difflib import SequenceMatcher

    best_match = None
    best_ratio = 0.0

    for task in tasks:
        ratio = SequenceMatcher(None, name.lower(), task.name.lower()).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = task

    return best_match


def update_markdown_with_ids(content: str, task_id_mapping: Dict[str, int]) -> str:
    """
    Atualiza Markdown adicionando IDs do Odoo.

    Args:
        content: Conteúdo Markdown original
        task_id_mapping: Dict {nome_tarefa: odoo_id}

    Returns:
        Markdown atualizado com IDs
    """
    lines = content.split("\n")
    updated_lines = []
    task_pattern = re.compile(r"^(\s*)- \[([ x])\]\s+(.+)$")
    odoo_id_pattern = re.compile(r"\(#(\d+)\)")

    for line in lines:
        task_match = task_pattern.match(line)
        if task_match:
            indent = task_match.group(1)
            checkbox = task_match.group(2)
            task_text = task_match.group(3).strip()

            # Se já tem ID, pular
            if odoo_id_pattern.search(task_text):
                updated_lines.append(line)
                continue

            # Buscar ID no mapping
            odoo_id = task_id_mapping.get(task_text)
            if odoo_id:
                # Adicionar ID
                updated_line = f"{indent}- [{checkbox}] {task_text} (#{odoo_id})"
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    return "\n".join(updated_lines)
