#!/usr/bin/env python3
"""
Exemplos Práticos de Integração com API Odoo 18
Gerenciamento de Projetos e Tarefas

Este arquivo contém exemplos completos e prontos para uso de:
- XML-RPC
- JSON-RPC
- Sincronização Bidirecional
- Tratamento de Hierarquia de Tarefas (parent_id)
- Filtragem por usuário
- CRUD completo

Autor: Documentação Técnica API Odoo
Data: Fev 28, 2026
Versão Odoo: 18.0
"""

import xmlrpc.client
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# Configurações do Odoo
ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'odoo'
ODOO_USERNAME = 'admin@example.com'
ODOO_PASSWORD = 'admin'

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('odoo_api')


# ============================================================================
# CLIENTE XML-RPC
# ============================================================================

class OdooXMLRPCClient:
    """
    Cliente XML-RPC completo para Odoo 18
    
    Uso:
        client = OdooXMLRPCClient(url, db, username, password)
        projects = client.get_projects()
        task_id = client.create_task('Nova Tarefa', project_id=1)
    """
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        
        # Endpoints
        self.common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Autenticar
        self.uid = self.authenticate()
        logger.info(f"Authenticated as UID {self.uid}")
    
    def authenticate(self) -> int:
        """Autenticar e retornar UID"""
        uid = self.common.authenticate(
            self.db, self.username, self.password, {}
        )
        if not uid:
            raise Exception("Authentication failed")
        return uid
    
    def execute_kw(self, model: str, method: str, args: list = None, kwargs: dict = None):
        """Executar método em modelo Odoo"""
        args = args or []
        kwargs = kwargs or {}
        
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs
        )
    
    # ========================================================================
    # PROJECT METHODS
    # ========================================================================
    
    def get_projects(self, filters: list = None) -> List[Dict]:
        """
        Buscar projetos
        
        Args:
            filters: Lista de filtros Odoo domain
                    Exemplo: [['active', '=', True], ['name', 'ilike', 'API']]
        
        Returns:
            Lista de projetos
        """
        filters = filters or [['active', '=', True]]
        
        return self.execute_kw(
            'project.project', 'search_read',
            [filters],
            {
                'fields': [
                    'id', 'name', 'user_id', 'partner_id',
                    'date_start', 'date', 'task_count', 'active'
                ]
            }
        )
    
    def get_project_by_id(self, project_id: int) -> Optional[Dict]:
        """Buscar projeto específico por ID"""
        projects = self.execute_kw(
            'project.project', 'search_read',
            [[['id', '=', project_id]]],
            {
                'fields': [
                    'id', 'name', 'user_id', 'partner_id',
                    'task_ids', 'date_start', 'date'
                ]
            }
        )
        return projects[0] if projects else None
    
    def create_project(self, name: str, **kwargs) -> int:
        """
        Criar novo projeto
        
        Args:
            name: Nome do projeto
            **kwargs: Campos adicionais (user_id, partner_id, etc.)
        
        Returns:
            ID do projeto criado
        """
        values = {'name': name}
        values.update(kwargs)
        
        return self.execute_kw('project.project', 'create', [values])
    
    def update_project(self, project_id: int, **kwargs) -> bool:
        """Atualizar projeto"""
        return self.execute_kw(
            'project.project', 'write',
            [[project_id], kwargs]
        )
    
    # ========================================================================
    # TASK METHODS
    # ========================================================================
    
    def get_tasks(self, filters: list = None, fields: list = None, 
                  limit: int = None, order: str = None) -> List[Dict]:
        """
        Buscar tarefas
        
        Args:
            filters: Filtros Odoo domain
            fields: Lista de campos para retornar
            limit: Número máximo de registros
            order: Ordenação (ex: 'name asc', 'create_date desc')
        
        Returns:
            Lista de tarefas
        """
        filters = filters or [['active', '=', True]]
        fields = fields or [
            'id', 'name', 'description', 'project_id',
            'parent_id', 'child_ids', 'user_ids',
            'stage_id', 'priority', 'date_deadline',
            'kanban_state', 'tag_ids', 'active',
            'write_date', 'create_date'
        ]
        
        kwargs = {'fields': fields}
        if limit:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
        
        return self.execute_kw(
            'project.task', 'search_read',
            [filters], kwargs
        )
    
    def get_task_by_id(self, task_id: int, fields: list = None) -> Optional[Dict]:
        """Buscar tarefa específica por ID"""
        tasks = self.get_tasks([['id', '=', task_id]], fields=fields)
        return tasks[0] if tasks else None
    
    def get_tasks_by_project(self, project_id: int, include_archived: bool = False) -> List[Dict]:
        """Buscar todas as tarefas de um projeto"""
        filters = [['project_id', '=', project_id]]
        if not include_archived:
            filters.append(['active', '=', True])
        
        return self.get_tasks(filters)
    
    def get_tasks_by_user(self, user_id: int, include_done: bool = False) -> List[Dict]:
        """
        Buscar tarefas atribuídas a um usuário
        
        Args:
            user_id: ID do usuário
            include_done: Incluir tarefas concluídas
        """
        filters = [
            ['user_ids', 'in', [user_id]],
            ['active', '=', True]
        ]
        
        if not include_done:
            filters.append(['kanban_state', '!=', 'done'])
        
        return self.get_tasks(filters)
    
    def get_root_tasks(self, project_id: int = None) -> List[Dict]:
        """
        Buscar apenas tarefas raiz (sem parent_id)
        
        Args:
            project_id: Se fornecido, filtra por projeto
        """
        filters = [
            ['active', '=', True],
            ['parent_id', '=', False]
        ]
        
        if project_id:
            filters.append(['project_id', '=', project_id])
        
        return self.get_tasks(filters)
    
    def get_subtasks(self, parent_task_id: int, recursive: bool = False) -> List[Dict]:
        """
        Buscar subtarefas de uma tarefa
        
        Args:
            parent_task_id: ID da tarefa pai
            recursive: Se True, busca toda a hierarquia
        """
        direct_children = self.get_tasks([['parent_id', '=', parent_task_id]])
        
        if not recursive:
            return direct_children
        
        # Buscar recursivamente
        all_children = []
        for child in direct_children:
            all_children.append(child)
            grand_children = self.get_subtasks(child['id'], recursive=True)
            all_children.extend(grand_children)
        
        return all_children
    
    def get_task_hierarchy(self, task_id: int) -> Dict:
        """
        Obter tarefa com toda sua hierarquia (pai, filhos, netos, etc.)
        
        Returns:
            Dicionário com estrutura aninhada
        """
        task = self.get_task_by_id(task_id)
        if not task:
            return None
        
        # Buscar subtarefas recursivamente
        children = []
        for child_id in task.get('child_ids', []):
            child_hierarchy = self.get_task_hierarchy(child_id)
            if child_hierarchy:
                children.append(child_hierarchy)
        
        return {
            'id': task['id'],
            'name': task['name'],
            'description': task.get('description', ''),
            'parent_id': task['parent_id'][0] if task.get('parent_id') else None,
            'project_id': task['project_id'][0] if task.get('project_id') else None,
            'user_ids': task.get('user_ids', []),
            'stage_id': task['stage_id'][0] if task.get('stage_id') else None,
            'priority': task.get('priority', '0'),
            'date_deadline': task.get('date_deadline'),
            'children': children
        }
    
    def create_task(self, name: str, project_id: int, **kwargs) -> int:
        """
        Criar nova tarefa
        
        Args:
            name: Nome da tarefa
            project_id: ID do projeto
            **kwargs: Campos adicionais
                description: str
                parent_id: int (para criar subtarefa)
                user_ids: list[int] (IDs dos usuários)
                priority: str ('0' ou '1')
                date_deadline: str (formato 'YYYY-MM-DD')
                tag_ids: list[int]
        
        Returns:
            ID da tarefa criada
        
        Example:
            task_id = client.create_task(
                'Implementar login',
                project_id=1,
                description='<p>Implementar OAuth2</p>',
                user_ids=[2, 3],
                priority='1',
                date_deadline='2026-03-15'
            )
        """
        values = {
            'name': name,
            'project_id': project_id,
        }
        
        # Processar user_ids (Many2many)
        if 'user_ids' in kwargs:
            user_ids = kwargs.pop('user_ids')
            values['user_ids'] = [(6, 0, user_ids)]
        
        # Processar tag_ids (Many2many)
        if 'tag_ids' in kwargs:
            tag_ids = kwargs.pop('tag_ids')
            values['tag_ids'] = [(6, 0, tag_ids)]
        
        values.update(kwargs)
        
        task_id = self.execute_kw('project.task', 'create', [values])
        logger.info(f"Created task {task_id}: {name}")
        return task_id
    
    def create_task_with_subtasks(self, parent_name: str, project_id: int,
                                  subtask_names: List[str], **kwargs) -> Dict:
        """
        Criar tarefa pai com múltiplas subtarefas
        
        Args:
            parent_name: Nome da tarefa pai
            project_id: ID do projeto
            subtask_names: Lista de nomes para subtarefas
            **kwargs: Campos adicionais para tarefa pai
        
        Returns:
            {
                'parent_id': int,
                'subtask_ids': list[int]
            }
        """
        # Criar tarefa pai
        parent_id = self.create_task(parent_name, project_id, **kwargs)
        
        # Criar subtarefas
        subtask_ids = []
        for subtask_name in subtask_names:
            subtask_id = self.create_task(
                subtask_name,
                project_id,
                parent_id=parent_id
            )
            subtask_ids.append(subtask_id)
        
        logger.info(f"Created parent task {parent_id} with {len(subtask_ids)} subtasks")
        
        return {
            'parent_id': parent_id,
            'subtask_ids': subtask_ids
        }
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """
        Atualizar tarefa
        
        Args:
            task_id: ID da tarefa
            **kwargs: Campos para atualizar
        
        Example:
            client.update_task(
                5,
                name='Novo nome',
                priority='1',
                user_ids=[2, 3, 4]  # Substituir assignees
            )
        """
        values = {}
        
        # Processar user_ids (Many2many)
        if 'user_ids' in kwargs:
            user_ids = kwargs.pop('user_ids')
            values['user_ids'] = [(6, 0, user_ids)]
        
        # Processar tag_ids (Many2many)
        if 'tag_ids' in kwargs:
            tag_ids = kwargs.pop('tag_ids')
            values['tag_ids'] = [(6, 0, tag_ids)]
        
        values.update(kwargs)
        
        result = self.execute_kw(
            'project.task', 'write',
            [[task_id], values]
        )
        
        if result:
            logger.info(f"Updated task {task_id}")
        
        return result
    
    def assign_users_to_task(self, task_id: int, user_ids: List[int], 
                            replace: bool = True) -> bool:
        """
        Atribuir usuários a uma tarefa
        
        Args:
            task_id: ID da tarefa
            user_ids: Lista de IDs de usuários
            replace: Se True, substitui todos. Se False, adiciona aos existentes
        """
        if replace:
            # Substituir todos os assignees
            return self.update_task(task_id, user_ids=user_ids)
        else:
            # Adicionar aos existentes
            values = {'user_ids': []}
            for user_id in user_ids:
                values['user_ids'].append((4, user_id, 0))
            
            return self.execute_kw(
                'project.task', 'write',
                [[task_id], values]
            )
    
    def remove_user_from_task(self, task_id: int, user_id: int) -> bool:
        """Remover usuário de uma tarefa"""
        return self.execute_kw(
            'project.task', 'write',
            [[task_id], {'user_ids': [(3, user_id, 0)]}]
        )
    
    def move_task_to_stage(self, task_id: int, stage_id: int) -> bool:
        """Mover tarefa para outro estágio"""
        return self.update_task(task_id, stage_id=stage_id)
    
    def archive_task(self, task_id: int) -> bool:
        """Arquivar tarefa (soft delete)"""
        result = self.update_task(task_id, active=False)
        if result:
            logger.info(f"Archived task {task_id}")
        return result
    
    def delete_task(self, task_id: int, hard_delete: bool = False) -> bool:
        """
        Deletar tarefa
        
        Args:
            task_id: ID da tarefa
            hard_delete: Se True, deleta permanentemente. Se False, apenas arquiva
        """
        if hard_delete:
            result = self.execute_kw('project.task', 'unlink', [[task_id]])
            if result:
                logger.warning(f"Hard deleted task {task_id}")
            return result
        else:
            return self.archive_task(task_id)
    
    # ========================================================================
    # USER METHODS
    # ========================================================================
    
    def get_users(self, filters: list = None) -> List[Dict]:
        """Buscar usuários"""
        filters = filters or [['active', '=', True]]
        
        return self.execute_kw(
            'res.users', 'search_read',
            [filters],
            {'fields': ['id', 'name', 'login', 'email', 'active']}
        )
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Buscar usuário por email"""
        users = self.get_users([['email', '=', email]])
        return users[0] if users else None
    
    def get_user_by_login(self, login: str) -> Optional[Dict]:
        """Buscar usuário por login"""
        users = self.get_users([['login', '=', login]])
        return users[0] if users else None
    
    # ========================================================================
    # STAGE METHODS
    # ========================================================================
    
    def get_task_stages(self, project_id: int = None) -> List[Dict]:
        """
        Buscar estágios de tarefas
        
        Args:
            project_id: Se fornecido, busca estágios do projeto específico
        """
        filters = []
        
        if project_id:
            filters.append(['project_ids', 'in', [project_id]])
        
        return self.execute_kw(
            'project.task.type', 'search_read',
            [filters],
            {'fields': ['id', 'name', 'sequence', 'fold'], 'order': 'sequence asc'}
        )
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_changes_since(self, model: str, since_date: str, 
                         fields: list = None) -> List[Dict]:
        """
        Buscar registros modificados desde uma data
        
        Args:
            model: Nome do modelo ('project.task', 'project.project', etc.)
            since_date: Data no formato 'YYYY-MM-DD HH:MM:SS'
            fields: Campos para retornar
        
        Returns:
            Lista de registros modificados
        """
        filters = [
            '|',
            ['write_date', '>', since_date],
            ['create_date', '>', since_date]
        ]
        
        fields = fields or ['id', 'write_date', 'create_date']
        
        return self.execute_kw(
            model, 'search_read',
            [filters],
            {'fields': fields}
        )
    
    def search_ids(self, model: str, filters: list) -> List[int]:
        """
        Buscar apenas IDs (mais rápido que search_read)
        
        Args:
            model: Nome do modelo
            filters: Filtros Odoo domain
        
        Returns:
            Lista de IDs
        """
        return self.execute_kw(model, 'search', [filters])


# ============================================================================
# CLIENTE JSON-RPC
# ============================================================================

class OdooJSONRPCClient:
    """
    Cliente JSON-RPC completo para Odoo 18
    
    Mais leve e rápido que XML-RPC, mesma funcionalidade.
    
    Uso:
        client = OdooJSONRPCClient(url, db, username, password)
        tasks = client.get_tasks()
    """
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.uid = None
        
        # Autenticar
        self.authenticate()
        logger.info(f"Authenticated via JSON-RPC as UID {self.uid}")
    
    def authenticate(self) -> bool:
        """Autenticar via JSON-RPC"""
        response = self.call(
            '/web/session/authenticate',
            params={
                'db': self.db,
                'login': self.username,
                'password': self.password
            }
        )
        
        if response and 'uid' in response:
            self.uid = response['uid']
            return True
        
        raise Exception("Authentication failed")
    
    def call(self, endpoint: str, method: str = 'call', params: dict = None) -> Any:
        """
        Chamada JSON-RPC genérica
        
        Args:
            endpoint: Endpoint da API ('/jsonrpc', '/web/session/authenticate', etc.)
            method: Método JSON-RPC (geralmente 'call')
            params: Parâmetros da chamada
        
        Returns:
            Resultado da chamada
        """
        url = f"{self.url}{endpoint}"
        
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params or {},
            'id': 1
        }
        
        headers = {'Content-Type': 'application/json'}
        response = self.session.post(url, json=payload, headers=headers)
        
        result = response.json()
        
        if 'error' in result:
            error_msg = result['error'].get('message', str(result['error']))
            raise Exception(f"JSON-RPC Error: {error_msg}")
        
        return result.get('result')
    
    def execute_kw(self, model: str, method: str, args: list = None, 
                   kwargs: dict = None) -> Any:
        """Executar método em modelo"""
        return self.call(
            '/jsonrpc',
            params={
                'service': 'object',
                'method': 'execute_kw',
                'args': [
                    self.db, self.uid, self.password,
                    model, method,
                    args or [], kwargs or {}
                ]
            }
        )
    
    # ========================================================================
    # TASK METHODS (mesma interface do XML-RPC)
    # ========================================================================
    
    def get_tasks(self, filters: list = None, fields: list = None) -> List[Dict]:
        """Buscar tarefas"""
        filters = filters or [['active', '=', True]]
        fields = fields or [
            'id', 'name', 'project_id', 'user_ids',
            'parent_id', 'child_ids', 'stage_id'
        ]
        
        return self.execute_kw(
            'project.task',
            'search_read',
            args=[filters],
            kwargs={'fields': fields}
        )
    
    def create_task(self, name: str, project_id: int, **kwargs) -> int:
        """Criar tarefa"""
        values = {
            'name': name,
            'project_id': project_id,
        }
        
        # Processar user_ids
        if 'user_ids' in kwargs:
            user_ids = kwargs.pop('user_ids')
            values['user_ids'] = [(6, 0, user_ids)]
        
        values.update(kwargs)
        
        task_id = self.execute_kw('project.task', 'create', args=[values])
        logger.info(f"Created task {task_id} via JSON-RPC")
        return task_id
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """Atualizar tarefa"""
        values = {}
        
        if 'user_ids' in kwargs:
            user_ids = kwargs.pop('user_ids')
            values['user_ids'] = [(6, 0, user_ids)]
        
        values.update(kwargs)
        
        return self.execute_kw(
            'project.task', 'write',
            args=[[task_id], values]
        )
    
    def delete_task(self, task_id: int) -> bool:
        """Arquivar tarefa"""
        return self.update_task(task_id, active=False)


# ============================================================================
# GERENCIADOR DE SINCRONIZAÇÃO BIDIRECIONAL
# ============================================================================

class OdooBidirectionalSync:
    """
    Gerenciador de sincronização bidirecional
    Odoo <-> Sistema Externo
    
    Uso:
        sync = OdooBidirectionalSync(odoo_client)
        
        # Sync do Odoo para sistema externo
        changes = sync.sync_from_odoo(last_sync_date)
        
        # Sync do sistema externo para Odoo
        sync.sync_to_odoo(external_changes)
    """
    
    def __init__(self, odoo_client: OdooXMLRPCClient):
        self.odoo = odoo_client
        self.mapping = {}  # {odoo_id: external_id}
        self.reverse_mapping = {}  # {external_id: odoo_id}
    
    def load_mapping(self, mapping_dict: Dict[int, str]):
        """
        Carregar mapeamento ID Odoo <-> ID Externo
        
        Args:
            mapping_dict: {odoo_id: external_id}
        """
        self.mapping = mapping_dict
        self.reverse_mapping = {v: k for k, v in mapping_dict.items()}
        logger.info(f"Loaded {len(self.mapping)} ID mappings")
    
    def save_mapping(self) -> Dict[int, str]:
        """Salvar mapeamento para persistência"""
        return self.mapping.copy()
    
    def sync_from_odoo(self, last_sync: str, 
                      project_ids: List[int] = None) -> List[Dict]:
        """
        Sincronizar mudanças do Odoo para sistema externo
        
        Args:
            last_sync: Data da última sincronização ('YYYY-MM-DD HH:MM:SS')
            project_ids: Se fornecido, sincroniza apenas projetos específicos
        
        Returns:
            Lista de tarefas modificadas
        """
        logger.info(f"Syncing from Odoo since {last_sync}")
        
        # Buscar tarefas modificadas
        filters = [
            '|',
            ['write_date', '>', last_sync],
            ['create_date', '>', last_sync]
        ]
        
        if project_ids:
            filters.append(['project_id', 'in', project_ids])
        
        changed_tasks = self.odoo.get_tasks(filters)
        
        logger.info(f"Found {len(changed_tasks)} changed tasks")
        
        # Processar cada tarefa
        for task in changed_tasks:
            external_id = self.mapping.get(task['id'])
            
            if external_id:
                logger.info(f"Task {task['id']} -> Update external {external_id}")
                # Aqui você chamaria: external_system.update_task(external_id, task)
            else:
                logger.info(f"Task {task['id']} -> Create new in external system")
                # Aqui você chamaria: external_id = external_system.create_task(task)
                # self.mapping[task['id']] = external_id
        
        return changed_tasks
    
    def sync_to_odoo(self, external_tasks: List[Dict]) -> Dict[str, int]:
        """
        Sincronizar mudanças do sistema externo para Odoo
        
        Args:
            external_tasks: Lista de tarefas do sistema externo
                Cada tarefa deve ter:
                - id: ID externo
                - name: Nome
                - modified_at: Data de modificação
                - project_id: ID do projeto no Odoo
                - outros campos opcionais
        
        Returns:
            Estatísticas: {'created': int, 'updated': int, 'skipped': int}
        """
        stats = {'created': 0, 'updated': 0, 'skipped': 0}
        
        logger.info(f"Syncing {len(external_tasks)} tasks to Odoo")
        
        for ext_task in external_tasks:
            external_id = ext_task['id']
            odoo_id = self.reverse_mapping.get(external_id)
            
            # Preparar dados
            task_data = {
                'name': ext_task['name'],
                'project_id': ext_task['project_id'],
            }
            
            # Campos opcionais
            if 'description' in ext_task:
                task_data['description'] = ext_task['description']
            
            if 'user_ids' in ext_task:
                task_data['user_ids'] = ext_task['user_ids']
            
            if 'parent_id' in ext_task and ext_task['parent_id']:
                # Mapear parent_id externo para Odoo
                parent_odoo_id = self.reverse_mapping.get(ext_task['parent_id'])
                if parent_odoo_id:
                    task_data['parent_id'] = parent_odoo_id
            
            if odoo_id:
                # Tarefa já existe no Odoo - verificar qual é mais recente
                odoo_task = self.odoo.get_task_by_id(
                    odoo_id,
                    fields=['write_date']
                )
                
                if not odoo_task:
                    logger.warning(f"Odoo task {odoo_id} not found, creating new")
                    odoo_id = None
                else:
                    odoo_write_date = odoo_task['write_date']
                    external_write_date = ext_task['modified_at']
                    
                    if external_write_date > odoo_write_date:
                        # Sistema externo é mais recente - atualizar Odoo
                        self.odoo.update_task(odoo_id, **task_data)
                        stats['updated'] += 1
                        logger.info(f"Updated Odoo task {odoo_id} from external {external_id}")
                    else:
                        # Odoo é mais recente - skip
                        stats['skipped'] += 1
                        logger.info(f"Skipped task {odoo_id} (Odoo is newer)")
                        continue
            
            if not odoo_id:
                # Criar nova tarefa no Odoo
                odoo_id = self.odoo.create_task(**task_data)
                self.mapping[odoo_id] = external_id
                self.reverse_mapping[external_id] = odoo_id
                stats['created'] += 1
                logger.info(f"Created Odoo task {odoo_id} from external {external_id}")
        
        logger.info(f"Sync complete: {stats}")
        return stats
    
    def resolve_conflicts(self, odoo_task: Dict, external_task: Dict) -> str:
        """
        Resolver conflitos quando mesma tarefa foi modificada nos dois lados
        
        Args:
            odoo_task: Tarefa do Odoo
            external_task: Tarefa do sistema externo
        
        Returns:
            'odoo' ou 'external' (qual versão manter)
        """
        # Estratégia: last-write-wins
        odoo_date = odoo_task.get('write_date', odoo_task.get('create_date'))
        external_date = external_task.get('modified_at')
        
        if external_date > odoo_date:
            return 'external'
        else:
            return 'odoo'


# ============================================================================
# EXEMPLOS DE USO
# ============================================================================

def example_xmlrpc_basic():
    """Exemplo básico de uso do cliente XML-RPC"""
    print("\n" + "="*80)
    print("EXEMPLO 1: XML-RPC Básico")
    print("="*80)
    
    # Criar cliente
    client = OdooXMLRPCClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    
    # Buscar projetos
    print("\n--- Projetos ---")
    projects = client.get_projects()
    for project in projects[:3]:
        print(f"  {project['id']}: {project['name']}")
    
    if not projects:
        print("  Nenhum projeto encontrado")
        return
    
    project_id = projects[0]['id']
    
    # Buscar tarefas do primeiro projeto
    print(f"\n--- Tarefas do Projeto {project_id} ---")
    tasks = client.get_tasks_by_project(project_id)
    for task in tasks[:5]:
        print(f"  {task['id']}: {task['name']}")
        if task.get('user_ids'):
            print(f"    Assignees: {task['user_ids']}")


def example_create_task_hierarchy():
    """Exemplo: Criar hierarquia de tarefas"""
    print("\n" + "="*80)
    print("EXEMPLO 2: Criar Tarefa com Subtarefas")
    print("="*80)
    
    client = OdooXMLRPCClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    
    # Buscar primeiro projeto
    projects = client.get_projects()
    if not projects:
        print("Nenhum projeto encontrado")
        return
    
    project_id = projects[0]['id']
    
    # Criar tarefa com subtarefas
    result = client.create_task_with_subtasks(
        parent_name='Implementar API de Autenticação',
        project_id=project_id,
        subtask_names=[
            'Design da API',
            'Implementação do backend',
            'Testes unitários',
            'Documentação'
        ],
        description='<p>Implementar sistema completo de autenticação</p>',
        priority='1'
    )
    
    print(f"\nCriada tarefa pai: {result['parent_id']}")
    print(f"Criadas {len(result['subtask_ids'])} subtarefas:")
    for subtask_id in result['subtask_ids']:
        subtask = client.get_task_by_id(subtask_id)
        print(f"  - {subtask_id}: {subtask['name']}")
    
    # Buscar hierarquia completa
    print("\n--- Hierarquia Completa ---")
    hierarchy = client.get_task_hierarchy(result['parent_id'])
    print_task_tree(hierarchy)
    
    # Limpar (arquivar tarefa pai e todas as subtarefas)
    print("\n--- Arquivando tarefas criadas ---")
    client.archive_task(result['parent_id'])
    for subtask_id in result['subtask_ids']:
        client.archive_task(subtask_id)
    print("Tarefas arquivadas")


def print_task_tree(task: Dict, level: int = 0):
    """Imprimir árvore de tarefas recursivamente"""
    indent = "  " * level
    print(f"{indent}- {task['name']} (ID: {task['id']})")
    
    for child in task.get('children', []):
        print_task_tree(child, level + 1)


def example_filter_by_user():
    """Exemplo: Filtrar tarefas por usuário"""
    print("\n" + "="*80)
    print("EXEMPLO 3: Filtrar Tarefas por Usuário")
    print("="*80)
    
    client = OdooXMLRPCClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    
    # Buscar usuário atual
    current_user = client.get_user_by_login(ODOO_USERNAME)
    if not current_user:
        print("Usuário não encontrado")
        return
    
    print(f"\nUsuário: {current_user['name']} (ID: {current_user['id']})")
    
    # Buscar tarefas do usuário
    my_tasks = client.get_tasks_by_user(current_user['id'])
    
    print(f"\nTarefas atribuídas: {len(my_tasks)}")
    for task in my_tasks[:10]:
        project_name = task['project_id'][1] if task.get('project_id') else 'N/A'
        stage_name = task['stage_id'][1] if task.get('stage_id') else 'N/A'
        
        print(f"\n  {task['id']}: {task['name']}")
        print(f"    Projeto: {project_name}")
        print(f"    Estágio: {stage_name}")
        print(f"    Prioridade: {'Alta' if task.get('priority') == '1' else 'Normal'}")
        if task.get('date_deadline'):
            print(f"    Deadline: {task['date_deadline']}")


def example_sync_bidirectional():
    """Exemplo: Sincronização bidirecional"""
    print("\n" + "="*80)
    print("EXEMPLO 4: Sincronização Bidirecional")
    print("="*80)
    
    client = OdooXMLRPCClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    sync = OdooBidirectionalSync(client)
    
    # Simular última sincronização (1 hora atrás)
    last_sync = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\nBuscando mudanças desde: {last_sync}")
    
    # Sincronizar do Odoo
    changed_tasks = sync.sync_from_odoo(last_sync)
    
    print(f"\nEncontradas {len(changed_tasks)} tarefas modificadas:")
    for task in changed_tasks[:5]:
        action = 'Criada' if task['create_date'] > last_sync else 'Modificada'
        print(f"  {task['id']}: {task['name']} ({action})")
    
    # Simular tarefas do sistema externo
    print("\n--- Simulando sincronização reversa ---")
    
    projects = client.get_projects()
    if projects:
        external_tasks = [
            {
                'id': 'ext-001',
                'name': 'Tarefa do Sistema Externo 1',
                'project_id': projects[0]['id'],
                'modified_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'description': '<p>Criada no sistema externo</p>'
            }
        ]
        
        stats = sync.sync_to_odoo(external_tasks)
        print(f"\nEstatísticas da sincronização:")
        print(f"  Criadas: {stats['created']}")
        print(f"  Atualizadas: {stats['updated']}")
        print(f"  Ignoradas: {stats['skipped']}")


def example_jsonrpc():
    """Exemplo: Usar JSON-RPC"""
    print("\n" + "="*80)
    print("EXEMPLO 5: JSON-RPC")
    print("="*80)
    
    client = OdooJSONRPCClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    
    # Buscar tarefas
    tasks = client.get_tasks(limit=5)
    
    print(f"\nTarefas via JSON-RPC: {len(tasks)}")
    for task in tasks:
        print(f"  {task['id']}: {task['name']}")
    
    # Criar tarefa
    projects = client.execute_kw(
        'project.project', 'search_read',
        args=[[['active', '=', True]]],
        kwargs={'fields': ['id', 'name'], 'limit': 1}
    )
    
    if projects:
        task_id = client.create_task(
            'Tarefa JSON-RPC Test',
            project_id=projects[0]['id'],
            description='<p>Criada via JSON-RPC</p>'
        )
        print(f"\nTarefa criada: {task_id}")
        
        # Arquivar
        client.delete_task(task_id)
        print(f"Tarefa {task_id} arquivada")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    """
    Execute os exemplos
    
    Nota: Certifique-se de configurar as variáveis no topo do arquivo:
    - ODOO_URL
    - ODOO_DB
    - ODOO_USERNAME
    - ODOO_PASSWORD
    """
    
    try:
        # Executar exemplos
        example_xmlrpc_basic()
        example_create_task_hierarchy()
        example_filter_by_user()
        example_sync_bidirectional()
        example_jsonrpc()
        
        print("\n" + "="*80)
        print("Todos os exemplos executados com sucesso!")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Erro ao executar exemplos: {e}", exc_info=True)
        print(f"\nERRO: {e}")
        print("\nVerifique as configurações no topo do arquivo.")
