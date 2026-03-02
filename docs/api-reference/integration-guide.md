# Guia Completo de Integração com API do Odoo 18
## Gerenciamento de Projetos e Tarefas

---

## Índice

1. [Visão Geral](#visão-geral)
2. [Odoo XML-RPC API](#1-odoo-xml-rpc-api)
3. [Odoo JSON-RPC API](#2-odoo-json-rpc-api)
4. [Odoo REST API](#3-odoo-rest-api)
5. [GraphQL para Odoo](#4-graphql-para-odoo)
6. [Comparação das Abordagens](#5-comparação-das-abordagens)
7. [Recomendações para Sincronização Bidirecional](#6-recomendações)

---

## Visão Geral

O Odoo 18 oferece múltiplas formas de integração externa via API. Este guia foca especificamente em **gerenciamento de projetos e tarefas**, incluindo:

- Modelos principais: `project.project` e `project.task`
- Campos importantes: `parent_id` (subtarefas), `user_ids` (assignees), `stage_id`, etc.
- Operações CRUD completas
- Sincronização bidirecional

### Modelos do Odoo para Projetos e Tarefas

**project.project** - Modelo de Projetos
- `id`: ID do projeto
- `name`: Nome do projeto
- `active`: Projeto ativo/arquivado
- `user_id`: Gerente do projeto
- `partner_id`: Cliente/Parceiro
- `task_ids`: Tarefas do projeto
- `stage_id`: Estágio do projeto

**project.task** - Modelo de Tarefas
- `id`: ID da tarefa
- `name`: Nome da tarefa
- `description`: Descrição HTML
- `project_id`: Projeto relacionado (Many2one)
- `parent_id`: Tarefa pai (para subtarefas)
- `child_ids`: Subtarefas (One2many)
- `user_ids`: Usuários atribuídos (Many2many)
- `stage_id`: Estágio da tarefa
- `priority`: Prioridade (0=Normal, 1=Alta)
- `date_deadline`: Data limite
- `date_assign`: Data de atribuição
- `kanban_state`: Estado kanban (normal, done, blocked)
- `active`: Tarefa ativa/arquivada
- `tag_ids`: Tags/etiquetas

---

## 1. Odoo XML-RPC API

### 📋 Descrição

A **XML-RPC API** é a interface padrão e mais estável do Odoo. Funciona desde versões antigas e é mantida com retrocompatibilidade.

### ✅ Vantagens

- **Estabilidade**: Interface oficial e bem documentada
- **Compatibilidade**: Funciona em todas as versões do Odoo
- **Confiabilidade**: Amplamente testada pela comunidade
- **Sem dependências extras**: Não requer módulos adicionais
- **Suporte nativo**: Bibliotecas em Python, PHP, Java, etc.

### ❌ Limitações

- **Verbosidade**: Payloads XML grandes
- **Performance**: Overhead do parsing XML
- **Não é RESTful**: Usa RPC em vez de padrões HTTP/REST
- **Debugging difícil**: XML menos legível que JSON
- **Sem schema formal**: Documentação pode ser limitada

---

### 🔐 Autenticação XML-RPC

```python
import xmlrpc.client

# Configuração
url = 'http://localhost:8069'
db = 'odoo'
username = 'admin@example.com'
password = 'admin_password'

# Endpoint comum
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')

# Autenticar e obter UID
uid = common.authenticate(db, username, password, {})
print(f"Authenticated as UID: {uid}")

# Verificar versão do Odoo
version = common.version()
print(f"Odoo version: {version}")
```

### Métodos de Autenticação

```python
# Endpoint de objetos (para operações CRUD)
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Todas as chamadas requerem: db, uid, password, model, method, args
```

---

### 📖 Buscar Projetos e Tarefas

#### Buscar todos os projetos

```python
# Buscar todos os projetos ativos
projects = models.execute_kw(
    db, uid, password,
    'project.project', 'search_read',
    [[['active', '=', True]]],  # Domain filter
    {'fields': ['id', 'name', 'user_id', 'partner_id', 'date_start']}
)

for project in projects:
    print(f"Project {project['id']}: {project['name']}")
    print(f"  Manager: {project['user_id']}")  # Retorna [id, 'Nome do Usuário']
```

#### Buscar tarefas de um projeto

```python
project_id = 1

tasks = models.execute_kw(
    db, uid, password,
    'project.task', 'search_read',
    [[['project_id', '=', project_id], ['active', '=', True]]],
    {
        'fields': [
            'id', 'name', 'description', 'project_id', 
            'parent_id', 'child_ids', 'user_ids',
            'stage_id', 'priority', 'date_deadline',
            'kanban_state', 'tag_ids'
        ]
    }
)

for task in tasks:
    print(f"Task {task['id']}: {task['name']}")
    if task['parent_id']:
        print(f"  Parent: {task['parent_id']}")  # [parent_id, 'Nome da Tarefa Pai']
    if task['child_ids']:
        print(f"  Subtasks: {task['child_ids']}")  # Lista de IDs
    if task['user_ids']:
        print(f"  Assigned to: {task['user_ids']}")  # Lista de IDs de usuários
```

#### Buscar tarefas incluindo hierarquia completa

```python
# Buscar todas as tarefas com suas relações
all_tasks = models.execute_kw(
    db, uid, password,
    'project.task', 'search_read',
    [[['active', '=', True]]],
    {
        'fields': [
            'id', 'name', 'parent_id', 'child_ids',
            'project_id', 'user_ids', 'description'
        ],
        'order': 'parent_id asc, id asc'  # Ordena pais primeiro
    }
)

# Construir árvore de tarefas
tasks_by_id = {t['id']: t for t in all_tasks}

def get_task_tree(task_id):
    """Recursivamente obter toda a subárvore"""
    task = tasks_by_id.get(task_id)
    if not task:
        return None
    
    result = {
        'id': task['id'],
        'name': task['name'],
        'parent_id': task['parent_id'][0] if task['parent_id'] else None,
        'children': []
    }
    
    for child_id in task['child_ids']:
        child = get_task_tree(child_id)
        if child:
            result['children'].append(child)
    
    return result

# Obter apenas tarefas raiz (sem parent_id)
root_tasks = [t for t in all_tasks if not t['parent_id']]
for root in root_tasks:
    tree = get_task_tree(root['id'])
    print(tree)
```

---

### 🔍 Filtrar por Usuário (Assignee)

```python
# Buscar ID do usuário primeiro
user_login = 'john@example.com'
users = models.execute_kw(
    db, uid, password,
    'res.users', 'search_read',
    [[['login', '=', user_login]]],
    {'fields': ['id', 'name', 'login']}
)

if users:
    user_id = users[0]['id']
    
    # Buscar tarefas atribuídas a esse usuário
    # user_ids é Many2many, use operador 'in'
    my_tasks = models.execute_kw(
        db, uid, password,
        'project.task', 'search_read',
        [[['user_ids', 'in', [user_id]]]],
        {'fields': ['id', 'name', 'project_id', 'stage_id']}
    )
    
    print(f"Tasks assigned to {users[0]['name']}:")
    for task in my_tasks:
        print(f"  - {task['name']} (Project: {task['project_id'][1]})")
```

#### Filtros Avançados

```python
# Tarefas atribuídas ao usuário E com alta prioridade
high_priority_tasks = models.execute_kw(
    db, uid, password,
    'project.task', 'search_read',
    [[
        ['user_ids', 'in', [user_id]],
        ['priority', '=', '1'],  # Alta prioridade
        ['active', '=', True]
    ]],
    {'fields': ['id', 'name', 'priority', 'date_deadline']}
)

# Tarefas com deadline próximo (7 dias)
from datetime import datetime, timedelta
next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

upcoming_tasks = models.execute_kw(
    db, uid, password,
    'project.task', 'search_read',
    [[
        ['user_ids', 'in', [user_id]],
        ['date_deadline', '<=', next_week],
        ['date_deadline', '>=', datetime.now().strftime('%Y-%m-%d')],
        ['kanban_state', '!=', 'done']
    ]],
    {'fields': ['id', 'name', 'date_deadline']}
)
```

---

### ➕ Criar Tarefas

#### Criar tarefa simples

```python
# Criar nova tarefa
new_task_id = models.execute_kw(
    db, uid, password,
    'project.task', 'create',
    [{
        'name': 'Implementar autenticação',
        'description': '<p>Implementar sistema de login com OAuth2</p>',
        'project_id': 1,
        'user_ids': [(6, 0, [user_id])],  # Many2many: (6, 0, [ids])
        'priority': '1',  # Alta prioridade
        'date_deadline': '2026-03-15',
    }]
)

print(f"Created task ID: {new_task_id}")
```

#### Criar tarefa com subtarefas

```python
# Criar tarefa pai
parent_task_id = models.execute_kw(
    db, uid, password,
    'project.task', 'create',
    [{
        'name': 'Desenvolver módulo de relatórios',
        'project_id': 1,
        'user_ids': [(6, 0, [user_id])],
    }]
)

# Criar subtarefas
subtask_ids = []
for subtask_name in ['Design do relatório', 'Implementação', 'Testes']:
    subtask_id = models.execute_kw(
        db, uid, password,
        'project.task', 'create',
        [{
            'name': subtask_name,
            'project_id': 1,
            'parent_id': parent_task_id,  # Define a tarefa pai
            'user_ids': [(6, 0, [user_id])],
        }]
    )
    subtask_ids.append(subtask_id)

print(f"Created parent task {parent_task_id} with subtasks {subtask_ids}")
```

#### Criar tarefas em lote

```python
# Criar múltiplas tarefas de uma vez
tasks_data = [
    {'name': 'Tarefa 1', 'project_id': 1},
    {'name': 'Tarefa 2', 'project_id': 1},
    {'name': 'Tarefa 3', 'project_id': 1},
]

# create pode receber lista de dicts
created_ids = models.execute_kw(
    db, uid, password,
    'project.task', 'create',
    [tasks_data]
)

print(f"Created {len(created_ids)} tasks: {created_ids}")
```

---

### 🔄 Atualizar Tarefas

#### Atualizar campos simples

```python
task_id = 5

# Atualizar uma tarefa
models.execute_kw(
    db, uid, password,
    'project.task', 'write',
    [[task_id], {  # Lista de IDs a atualizar
        'name': 'Implementar autenticação OAuth2 (atualizado)',
        'description': '<p>Descrição atualizada</p>',
        'priority': '1',
    }]
)

print(f"Task {task_id} updated")
```

#### Atualizar assignees (Many2many)

```python
# Many2many operations: (comando, _, ids)
# (6, 0, [ids]) - Replace all (set)
# (4, id, _) - Add link
# (3, id, _) - Remove link
# (5, _, _) - Clear all

# Substituir todos os assignees
models.execute_kw(
    db, uid, password,
    'project.task', 'write',
    [[task_id], {
        'user_ids': [(6, 0, [2, 3, 4])]  # Substituir por users 2, 3, 4
    }]
)

# Adicionar um assignee sem remover os existentes
models.execute_kw(
    db, uid, password,
    'project.task', 'write',
    [[task_id], {
        'user_ids': [(4, 5, 0)]  # Adicionar user 5
    }]
)

# Remover um assignee
models.execute_kw(
    db, uid, password,
    'project.task', 'write',
    [[task_id], {
        'user_ids': [(3, 5, 0)]  # Remover user 5
    }]
)

# Limpar todos os assignees
models.execute_kw(
    db, uid, password,
    'project.task', 'write',
    [[task_id], {
        'user_ids': [(5, 0, 0)]  # Remover todos
    }]
)
```

#### Mover tarefa para outro projeto

```python
# Ao mover para outro projeto, considere atualizar stage_id também
new_project_id = 2

# Buscar primeiro stage do novo projeto
stages = models.execute_kw(
    db, uid, password,
    'project.task.type', 'search_read',
    [[['project_ids', 'in', [new_project_id]]]],
    {'fields': ['id', 'name'], 'order': 'sequence asc', 'limit': 1}
)

if stages:
    models.execute_kw(
        db, uid, password,
        'project.task', 'write',
        [[task_id], {
            'project_id': new_project_id,
            'stage_id': stages[0]['id']
        }]
    )
```

#### Atualizar subtarefas

```python
# Adicionar subtarefa existente como filha
existing_task_id = 10
parent_task_id = 5

models.execute_kw(
    db, uid, password,
    'project.task', 'write',
    [[existing_task_id], {
        'parent_id': parent_task_id
    }]
)

# Remover relação pai (tornar tarefa raiz novamente)
models.execute_kw(
    db, uid, password,
    'project.task', 'write',
    [[existing_task_id], {
        'parent_id': False
    }]
)
```

---

### 🗑️ Deletar/Arquivar Tarefas

```python
# SOFT DELETE (Recomendado): Arquivar tarefa
task_id = 5
models.execute_kw(
    db, uid, password,
    'project.task', 'write',
    [[task_id], {'active': False}]
)

# HARD DELETE (Não recomendado): Deletar permanentemente
models.execute_kw(
    db, uid, password,
    'project.task', 'unlink',
    [[task_id]]
)
```

---

### 📦 Exemplo Completo: Cliente XML-RPC

```python
#!/usr/bin/env python3
"""
Cliente completo XML-RPC para Odoo 18 - Gerenciamento de Tarefas
"""

import xmlrpc.client
from datetime import datetime, timedelta


class OdooXMLRPCClient:
    """Cliente XML-RPC para Odoo"""
    
    def __init__(self, url, db, username, password):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        
        # Endpoints
        self.common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Autenticar
        self.uid = self.authenticate()
    
    def authenticate(self):
        """Autenticar e retornar UID"""
        uid = self.common.authenticate(
            self.db, self.username, self.password, {}
        )
        if not uid:
            raise Exception("Authentication failed")
        return uid
    
    def execute(self, model, method, *args, **kwargs):
        """Executar método em modelo"""
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs
        )
    
    # --- Project Methods ---
    
    def get_projects(self, filters=None):
        """Buscar projetos"""
        filters = filters or [['active', '=', True]]
        return self.execute(
            'project.project', 'search_read',
            [filters],
            {'fields': ['id', 'name', 'user_id', 'date_start']}
        )
    
    def get_project_by_id(self, project_id):
        """Buscar projeto por ID"""
        projects = self.execute(
            'project.project', 'search_read',
            [[['id', '=', project_id]]],
            {'fields': ['id', 'name', 'user_id', 'partner_id', 'task_ids']}
        )
        return projects[0] if projects else None
    
    # --- Task Methods ---
    
    def get_tasks(self, filters=None, fields=None):
        """Buscar tarefas"""
        filters = filters or [['active', '=', True]]
        fields = fields or [
            'id', 'name', 'description', 'project_id',
            'parent_id', 'child_ids', 'user_ids',
            'stage_id', 'priority', 'date_deadline'
        ]
        return self.execute(
            'project.task', 'search_read',
            [filters],
            {'fields': fields}
        )
    
    def get_task_by_id(self, task_id):
        """Buscar tarefa por ID"""
        tasks = self.get_tasks([['id', '=', task_id]])
        return tasks[0] if tasks else None
    
    def get_tasks_by_project(self, project_id):
        """Buscar tarefas de um projeto"""
        return self.get_tasks([['project_id', '=', project_id]])
    
    def get_tasks_by_user(self, user_id):
        """Buscar tarefas atribuídas a um usuário"""
        return self.get_tasks([['user_ids', 'in', [user_id]]])
    
    def get_subtasks(self, parent_task_id):
        """Buscar subtarefas de uma tarefa"""
        return self.get_tasks([['parent_id', '=', parent_task_id]])
    
    def create_task(self, name, project_id, **kwargs):
        """Criar nova tarefa"""
        values = {
            'name': name,
            'project_id': project_id,
        }
        values.update(kwargs)
        
        return self.execute('project.task', 'create', [values])
    
    def update_task(self, task_id, **kwargs):
        """Atualizar tarefa"""
        return self.execute(
            'project.task', 'write',
            [[task_id], kwargs]
        )
    
    def delete_task(self, task_id, hard_delete=False):
        """Deletar/arquivar tarefa"""
        if hard_delete:
            return self.execute('project.task', 'unlink', [[task_id]])
        else:
            return self.update_task(task_id, active=False)
    
    def assign_users_to_task(self, task_id, user_ids, replace=True):
        """Atribuir usuários a uma tarefa"""
        if replace:
            # Substituir todos
            return self.update_task(
                task_id,
                user_ids=[(6, 0, user_ids)]
            )
        else:
            # Adicionar aos existentes
            for user_id in user_ids:
                self.update_task(
                    task_id,
                    user_ids=[(4, user_id, 0)]
                )
            return True
    
    # --- User Methods ---
    
    def get_users(self, filters=None):
        """Buscar usuários"""
        filters = filters or [['active', '=', True]]
        return self.execute(
            'res.users', 'search_read',
            [filters],
            {'fields': ['id', 'name', 'login', 'email']}
        )
    
    def get_user_by_email(self, email):
        """Buscar usuário por email"""
        users = self.get_users([['email', '=', email]])
        return users[0] if users else None


# --- Exemplo de Uso ---

if __name__ == '__main__':
    # Configuração
    client = OdooXMLRPCClient(
        url='http://localhost:8069',
        db='odoo',
        username='admin@example.com',
        password='admin'
    )
    
    # Buscar projetos
    print("\n=== Projects ===")
    projects = client.get_projects()
    for project in projects[:5]:
        print(f"{project['id']}: {project['name']}")
    
    # Buscar tarefas do primeiro projeto
    if projects:
        project_id = projects[0]['id']
        print(f"\n=== Tasks in Project {project_id} ===")
        tasks = client.get_tasks_by_project(project_id)
        for task in tasks[:5]:
            print(f"{task['id']}: {task['name']}")
            if task['user_ids']:
                print(f"  Assigned to: {task['user_ids']}")
    
    # Criar nova tarefa
    print("\n=== Creating Task ===")
    new_task_id = client.create_task(
        name='API Test Task',
        project_id=project_id,
        description='<p>Criada via XML-RPC API</p>',
        priority='1',
        user_ids=[(6, 0, [client.uid])]  # Atribuir a mim mesmo
    )
    print(f"Created task ID: {new_task_id}")
    
    # Atualizar tarefa
    print("\n=== Updating Task ===")
    client.update_task(
        new_task_id,
        name='API Test Task (Updated)',
        date_deadline=(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    )
    print(f"Updated task {new_task_id}")
    
    # Arquivar tarefa
    print("\n=== Archiving Task ===")
    client.delete_task(new_task_id, hard_delete=False)
    print(f"Archived task {new_task_id}")
```

---

### 🔄 Sincronização Bidirecional com XML-RPC

```python
class OdooSyncManager(OdooXMLRPCClient):
    """Gerenciador de sincronização bidirecional"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_sync = None
    
    def get_changes_since(self, model, last_sync_date):
        """Buscar registros modificados desde última sincronização"""
        filters = [
            '|',
            ['write_date', '>', last_sync_date],
            ['create_date', '>', last_sync_date]
        ]
        
        return self.execute(
            model, 'search_read',
            [filters],
            {'fields': ['id', 'write_date', 'create_date']}
        )
    
    def sync_tasks_from_odoo(self, last_sync):
        """Sincronizar tarefas do Odoo para sistema externo"""
        changed_tasks = self.get_changes_since('project.task', last_sync)
        
        # Buscar dados completos das tarefas alteradas
        task_ids = [t['id'] for t in changed_tasks]
        if not task_ids:
            return []
        
        full_tasks = self.execute(
            'project.task', 'search_read',
            [[['id', 'in', task_ids]]],
            {'fields': [
                'id', 'name', 'description', 'project_id',
                'parent_id', 'user_ids', 'stage_id',
                'write_date', 'create_date'
            ]}
        )
        
        return full_tasks
    
    def sync_task_to_odoo(self, external_task):
        """Sincronizar tarefa do sistema externo para Odoo"""
        # Verificar se tarefa já existe (por external_id)
        existing = self.execute(
            'project.task', 'search_read',
            [[['id', '=', external_task.get('odoo_id')]]],
            {'fields': ['id', 'write_date']}
        )
        
        task_data = {
            'name': external_task['name'],
            'description': external_task.get('description', ''),
            'project_id': external_task['project_id'],
        }
        
        if existing:
            # Atualizar se tarefa externa for mais recente
            odoo_write_date = existing[0]['write_date']
            external_write_date = external_task['modified_at']
            
            if external_write_date > odoo_write_date:
                self.update_task(existing[0]['id'], **task_data)
                return existing[0]['id']
        else:
            # Criar nova
            task_id = self.create_task(**task_data)
            return task_id


# Exemplo de uso de sincronização
if __name__ == '__main__':
    sync_manager = OdooSyncManager(
        url='http://localhost:8069',
        db='odoo',
        username='admin@example.com',
        password='admin'
    )
    
    # Sincronizar mudanças desde ontem
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    changed_tasks = sync_manager.sync_tasks_from_odoo(yesterday)
    
    print(f"Found {len(changed_tasks)} changed tasks since {yesterday}")
    for task in changed_tasks:
        print(f"  - {task['name']} (modified: {task['write_date']})")
```

---

## 2. Odoo JSON-RPC API

### 📋 Descrição

A **JSON-RPC API** é uma alternativa mais moderna ao XML-RPC. Usa JSON em vez de XML, resultando em payloads menores e mais legíveis.

### ✅ Vantagens

- **Payloads menores**: JSON é mais compacto que XML
- **Mais legível**: JSON é mais fácil de debugar
- **Melhor performance**: Parsing JSON é mais rápido
- **Mesma funcionalidade**: Todas as funções do XML-RPC
- **Sem módulos extras**: Nativo no Odoo
- **Integração JavaScript**: Perfeito para frontends web

### ❌ Limitações

- **Menos documentado**: Menos exemplos na comunidade
- **Mesma arquitetura RPC**: Não é REST
- **Autenticação por sessão**: Mais complexa que token-based
- **CORS issues**: Pode requerer configuração adicional

---

### 🔐 Autenticação JSON-RPC

```python
import json
import requests

# Configuração
url = 'http://localhost:8069'
db = 'odoo'
username = 'admin@example.com'
password = 'admin_password'


def json_rpc(url, method, params):
    """Fazer chamada JSON-RPC"""
    headers = {'Content-Type': 'application/json'}
    data = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    
    response = requests.post(url, json=data, headers=headers)
    result = response.json()
    
    if 'error' in result:
        raise Exception(result['error']['message'])
    
    return result.get('result')


# Autenticar
auth_response = json_rpc(
    f'{url}/jsonrpc',
    'call',
    {
        'service': 'common',
        'method': 'login',
        'args': [db, username, password]
    }
)

uid = auth_response
print(f"Authenticated as UID: {uid}")
```

### Autenticação com Sessão

```python
import requests

session = requests.Session()

# Login e criar sessão
login_data = {
    'jsonrpc': '2.0',
    'method': 'call',
    'params': {
        'db': db,
        'login': username,
        'password': password
    },
    'id': 1
}

response = session.post(
    f'{url}/web/session/authenticate',
    json=login_data,
    headers={'Content-Type': 'application/json'}
)

result = response.json()

if result.get('result'):
    uid = result['result'].get('uid')
    session_id = result['result'].get('session_id')
    print(f"Authenticated with session: {session_id}")
else:
    raise Exception("Authentication failed")
```

---

### 📖 Buscar Projetos e Tarefas

```python
def call_odoo(endpoint, model, method, args=None, kwargs=None):
    """Chamada genérica ao Odoo via JSON-RPC"""
    args = args or []
    kwargs = kwargs or {}
    
    data = {
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'service': 'object',
            'method': 'execute_kw',
            'args': [db, uid, password, model, method, args, kwargs]
        },
        'id': 1
    }
    
    response = session.post(endpoint, json=data)
    result = response.json()
    
    if 'error' in result:
        raise Exception(result['error'])
    
    return result.get('result')


# Buscar projetos
projects = call_odoo(
    f'{url}/jsonrpc',
    'project.project',
    'search_read',
    args=[[['active', '=', True]]],
    kwargs={'fields': ['id', 'name', 'user_id']}
)

for project in projects:
    print(f"Project: {project['name']}")


# Buscar tarefas
tasks = call_odoo(
    f'{url}/jsonrpc',
    'project.task',
    'search_read',
    args=[[['project_id', '=', 1]]],
    kwargs={
        'fields': [
            'id', 'name', 'parent_id', 'child_ids',
            'user_ids', 'stage_id'
        ]
    }
)

for task in tasks:
    print(f"Task: {task['name']}")
    if task['parent_id']:
        print(f"  Parent: {task['parent_id'][1]}")
```

---

### ➕ Criar e Atualizar Tarefas

```python
# Criar tarefa
new_task_id = call_odoo(
    f'{url}/jsonrpc',
    'project.task',
    'create',
    args=[[{
        'name': 'Nova tarefa via JSON-RPC',
        'project_id': 1,
        'user_ids': [(6, 0, [uid])],
        'description': '<p>Descrição HTML</p>'
    }]]
)

print(f"Created task: {new_task_id}")


# Atualizar tarefa
call_odoo(
    f'{url}/jsonrpc',
    'project.task',
    'write',
    args=[
        [new_task_id],
        {'name': 'Tarefa atualizada', 'priority': '1'}
    ]
)

print(f"Updated task: {new_task_id}")
```

---

### 📦 Cliente JSON-RPC Completo

```python
#!/usr/bin/env python3
"""
Cliente JSON-RPC completo para Odoo 18
"""

import json
import requests
from datetime import datetime


class OdooJSONRPCClient:
    """Cliente JSON-RPC para Odoo"""
    
    def __init__(self, url, db, username, password):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.uid = None
        
        # Autenticar
        self.authenticate()
    
    def authenticate(self):
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
    
    def call(self, endpoint, method='call', params=None):
        """Chamada JSON-RPC genérica"""
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
            raise Exception(result['error'])
        
        return result.get('result')
    
    def execute_kw(self, model, method, args=None, kwargs=None):
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
    
    # --- Task Methods ---
    
    def get_tasks(self, filters=None, fields=None):
        """Buscar tarefas"""
        filters = filters or [['active', '=', True]]
        fields = fields or ['id', 'name', 'project_id', 'user_ids']
        
        return self.execute_kw(
            'project.task',
            'search_read',
            args=[filters],
            kwargs={'fields': fields}
        )
    
    def create_task(self, values):
        """Criar tarefa"""
        return self.execute_kw(
            'project.task',
            'create',
            args=[values]
        )
    
    def update_task(self, task_id, values):
        """Atualizar tarefa"""
        return self.execute_kw(
            'project.task',
            'write',
            args=[[task_id], values]
        )
    
    def delete_task(self, task_id):
        """Arquivar tarefa"""
        return self.update_task(task_id, {'active': False})


# Exemplo de uso
if __name__ == '__main__':
    client = OdooJSONRPCClient(
        url='http://localhost:8069',
        db='odoo',
        username='admin@example.com',
        password='admin'
    )
    
    # Buscar tarefas
    tasks = client.get_tasks()
    print(f"Found {len(tasks)} tasks")
    
    for task in tasks[:5]:
        print(f"  - {task['name']}")
    
    # Criar tarefa
    task_id = client.create_task({
        'name': 'Test JSON-RPC Task',
        'project_id': 1
    })
    print(f"\nCreated task {task_id}")
    
    # Atualizar
    client.update_task(task_id, {'priority': '1'})
    print(f"Updated task {task_id}")
```

---

### 🌐 Exemplo JavaScript/Node.js

```javascript
// Cliente JSON-RPC para Node.js
const axios = require('axios');

class OdooClient {
    constructor(url, db, username, password) {
        this.url = url;
        this.db = db;
        this.username = username;
        this.password = password;
        this.uid = null;
        this.session = axios.create({
            baseURL: url,
            headers: {'Content-Type': 'application/json'}
        });
    }
    
    async authenticate() {
        const response = await this.call('/web/session/authenticate', {
            db: this.db,
            login: this.username,
            password: this.password
        });
        
        this.uid = response.uid;
        return this.uid;
    }
    
    async call(endpoint, params = {}) {
        const payload = {
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: 1
        };
        
        const response = await this.session.post(endpoint, payload);
        
        if (response.data.error) {
            throw new Error(response.data.error.message);
        }
        
        return response.data.result;
    }
    
    async execute_kw(model, method, args = [], kwargs = {}) {
        return this.call('/jsonrpc', {
            service: 'object',
            method: 'execute_kw',
            args: [this.db, this.uid, this.password, model, method, args, kwargs]
        });
    }
    
    async getTasks(filters = [['active', '=', true]]) {
        return this.execute_kw(
            'project.task',
            'search_read',
            [filters],
            {fields: ['id', 'name', 'project_id', 'user_ids']}
        );
    }
    
    async createTask(values) {
        return this.execute_kw('project.task', 'create', [[values]]);
    }
    
    async updateTask(taskId, values) {
        return this.execute_kw('project.task', 'write', [[taskId], values]);
    }
}

// Uso
(async () => {
    const client = new OdooClient(
        'http://localhost:8069',
        'odoo',
        'admin@example.com',
        'admin'
    );
    
    await client.authenticate();
    
    // Buscar tarefas
    const tasks = await client.getTasks();
    console.log(`Found ${tasks.length} tasks`);
    
    // Criar tarefa
    const taskId = await client.createTask({
        name: 'Task from Node.js',
        project_id: 1
    });
    console.log(`Created task ${taskId}`);
})();
```

---

## 3. Odoo REST API

### 📋 Descrição

O Odoo **não possui REST API nativa**. Porém, existem módulos da OCA e de terceiros que implementam uma interface RESTful sobre o Odoo.

### 🔧 Módulos Disponíveis

#### 1. **base_rest** (OCA)
- Repositório: https://github.com/OCA/rest-framework
- Framework para criar APIs REST customizadas
- Não é uma API pronta, mas infraestrutura para criar

#### 2. **rest_api** (Terceiros)
- Módulo comercial/community que expõe Odoo via REST
- Endpoints estilo REST: GET, POST, PUT, DELETE
- Autenticação via API tokens

### ✅ Vantagens (se usar módulo REST)

- **Padrão REST**: Familiares para desenvolvedores web
- **Autenticação por token**: Mais segura que sessões
- **Cacheable**: Pode usar cache HTTP
- **Stateless**: Sem gerenciamento de sessão
- **CORS-friendly**: Melhor para SPAs

### ❌ Limitações

- **Não nativo**: Requer instalação de módulo extra
- **Menos maduro**: Menos testado que XML-RPC/JSON-RPC
- **Documentação limitada**: Depende do módulo escolhido
- **Varia por implementação**: Não há padrão único

---

### 🔧 Instalação do base_rest (OCA)

```bash
# Clonar repositório
cd /home/amdlemos/github/odoo-cms/addons/OCA
git submodule add -b 18.0 https://github.com/OCA/rest-framework.git rest-framework

# Adicionar ao odoo.conf
# addons_path = ...,/mnt/extra-addons/OCA/rest-framework

# Reiniciar Odoo
docker-compose restart web
```

O `base_rest` não fornece API pronta para `project.task`. Você precisa **criar sua própria API REST** usando o framework.

---

### 📦 Exemplo: Criando API REST Customizada

```python
# addons/my_project_rest/models/project_rest_service.py

from odoo.addons.base_rest.components.service import to_int
from odoo.addons.component.core import Component


class ProjectTaskRestService(Component):
    """REST API para project.task"""
    
    _inherit = 'base.rest.service'
    _name = 'project.task.rest.service'
    _usage = 'tasks'
    _collection = 'base.rest.project.services'
    _description = """
        Project Task REST Services
        Access to project tasks
    """
    
    def get(self, _id):
        """
        Get task by ID
        GET /api/tasks/:id
        """
        task = self.env['project.task'].browse(_id)
        if not task.exists():
            raise ValueError(f'Task {_id} not found')
        
        return self._to_json(task)
    
    def search(self, name=None, project_id=None):
        """
        Search tasks
        GET /api/tasks?name=xxx&project_id=1
        """
        domain = [('active', '=', True)]
        
        if name:
            domain.append(('name', 'ilike', name))
        
        if project_id:
            domain.append(('project_id', '=', project_id))
        
        tasks = self.env['project.task'].search(domain)
        return [self._to_json(task) for task in tasks]
    
    def create(self, **params):
        """
        Create task
        POST /api/tasks
        """
        task = self.env['project.task'].create(params)
        return self._to_json(task)
    
    def update(self, _id, **params):
        """
        Update task
        PUT /api/tasks/:id
        """
        task = self.env['project.task'].browse(_id)
        if not task.exists():
            raise ValueError(f'Task {_id} not found')
        
        task.write(params)
        return self._to_json(task)
    
    def delete(self, _id):
        """
        Delete (archive) task
        DELETE /api/tasks/:id
        """
        task = self.env['project.task'].browse(_id)
        if not task.exists():
            raise ValueError(f'Task {_id} not found')
        
        task.write({'active': False})
        return {'success': True}
    
    def _to_json(self, task):
        """Converter task para JSON"""
        return {
            'id': task.id,
            'name': task.name,
            'description': task.description,
            'project_id': task.project_id.id,
            'project_name': task.project_id.name,
            'parent_id': task.parent_id.id if task.parent_id else None,
            'parent_name': task.parent_id.name if task.parent_id else None,
            'child_ids': [c.id for c in task.child_ids],
            'user_ids': [u.id for u in task.user_ids],
            'assignees': [{'id': u.id, 'name': u.name} for u in task.user_ids],
            'stage_id': task.stage_id.id,
            'stage_name': task.stage_id.name,
            'priority': task.priority,
            'date_deadline': task.date_deadline.isoformat() if task.date_deadline else None,
            'kanban_state': task.kanban_state,
            'active': task.active,
        }
    
    # Schema para validação (OpenAPI/Swagger)
    def _get_schema_get(self):
        return {
            '_id': {'type': 'integer', 'required': True}
        }
    
    def _get_schema_search(self):
        return {
            'name': {'type': 'string', 'required': False},
            'project_id': {'type': 'integer', 'required': False}
        }
    
    def _get_schema_create(self):
        return {
            'name': {'type': 'string', 'required': True},
            'project_id': {'type': 'integer', 'required': True},
            'description': {'type': 'string', 'required': False},
            'user_ids': {'type': 'array', 'items': {'type': 'integer'}, 'required': False},
            'parent_id': {'type': 'integer', 'required': False},
            'priority': {'type': 'string', 'required': False},
            'date_deadline': {'type': 'string', 'format': 'date', 'required': False},
        }
```

---

### 🔑 Autenticação por Token

```python
# addons/my_project_rest/models/auth.py

from odoo import models, fields


class APIToken(models.Model):
    """Modelo para tokens de API"""
    
    _name = 'api.token'
    _description = 'API Authentication Token'
    
    name = fields.Char(string='Token Name', required=True)
    token = fields.Char(string='Token', required=True, index=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    active = fields.Boolean(default=True)
    expires_at = fields.Datetime(string='Expires At')
    
    _sql_constraints = [
        ('token_unique', 'UNIQUE(token)', 'Token must be unique')
    ]
```

Cliente Python para REST API:

```python
#!/usr/bin/env python3
"""
Cliente REST para Odoo (usando módulo base_rest)
"""

import requests
from typing import Dict, List, Optional


class OdooRESTClient:
    """Cliente REST para Odoo"""
    
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs):
        """Fazer requisição HTTP"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code >= 400:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        
        return response.json() if response.content else None
    
    # --- Task Methods ---
    
    def get_task(self, task_id: int) -> Dict:
        """GET /api/tasks/:id"""
        return self._request('GET', f'/api/tasks/{task_id}')
    
    def search_tasks(self, name: Optional[str] = None, 
                     project_id: Optional[int] = None) -> List[Dict]:
        """GET /api/tasks"""
        params = {}
        if name:
            params['name'] = name
        if project_id:
            params['project_id'] = project_id
        
        return self._request('GET', '/api/tasks', params=params)
    
    def create_task(self, data: Dict) -> Dict:
        """POST /api/tasks"""
        return self._request('POST', '/api/tasks', json=data)
    
    def update_task(self, task_id: int, data: Dict) -> Dict:
        """PUT /api/tasks/:id"""
        return self._request('PUT', f'/api/tasks/{task_id}', json=data)
    
    def delete_task(self, task_id: int) -> Dict:
        """DELETE /api/tasks/:id"""
        return self._request('DELETE', f'/api/tasks/{task_id}')


# Exemplo de uso
if __name__ == '__main__':
    client = OdooRESTClient(
        base_url='http://localhost:8069',
        api_token='your_api_token_here'
    )
    
    # Buscar tarefas
    tasks = client.search_tasks(project_id=1)
    print(f"Found {len(tasks)} tasks")
    
    # Criar tarefa
    new_task = client.create_task({
        'name': 'REST API Task',
        'project_id': 1,
        'description': 'Created via REST API',
        'user_ids': [2, 3]
    })
    print(f"Created task {new_task['id']}")
    
    # Atualizar
    updated = client.update_task(new_task['id'], {
        'name': 'REST API Task (Updated)',
        'priority': '1'
    })
    print(f"Updated task {updated['id']}")
    
    # Buscar uma tarefa específica
    task = client.get_task(new_task['id'])
    print(f"Task details: {task}")
```

---

## 4. GraphQL para Odoo

### 📋 Descrição

**GraphQL** não é nativamente suportado pelo Odoo, mas existem módulos da OCA que implementam essa funcionalidade.

### 🔧 Módulos Disponíveis

#### **graphql_base** (OCA)
- Repositório: https://github.com/OCA/rest-framework
- Implementa servidor GraphQL para Odoo
- Permite criar schemas GraphQL customizados

### ✅ Vantagens

- **Queries flexíveis**: Cliente escolhe exatamente os campos
- **Reduz over-fetching**: Menos dados desnecessários
- **Reduz under-fetching**: Uma query busca tudo
- **Schema fortemente tipado**: Autodocumentação
- **Subscriptions**: Real-time updates (se implementado)
- **Ideal para mobile**: Economiza largura de banda

### ❌ Limitações

- **Não nativo**: Requer módulo extra
- **Complexidade**: Curva de aprendizado maior
- **Menos maduro**: Menos testado no ecossistema Odoo
- **Overhead**: Parsing de queries pode ser custoso
- **Caching**: Mais complexo que REST

---

### 🔧 Instalação do graphql_base

```bash
# Clonar repositório rest-framework (contém graphql_base)
cd /home/amdlemos/github/odoo-cms/addons/OCA
git submodule add -b 18.0 https://github.com/OCA/rest-framework.git rest-framework

# Instalar dependência Python
pip install graphql-core

# Adicionar ao odoo.conf
# addons_path = ...,/mnt/extra-addons/OCA/rest-framework

# Reiniciar Odoo e instalar módulo
docker-compose restart web
```

---

### 📦 Exemplo: Schema GraphQL para Tarefas

```python
# addons/my_project_graphql/models/project_task_schema.py

import graphene
from odoo.addons.graphql_base import OdooObjectType


class ProjectTaskType(OdooObjectType):
    """GraphQL Type para project.task"""
    
    class Meta:
        model = 'project.task'
        interfaces = (graphene.relay.Node,)
    
    # Campos básicos são automáticos
    # Adicionar campos computados customizados
    
    full_name = graphene.String()
    assignee_names = graphene.List(graphene.String)
    is_overdue = graphene.Boolean()
    
    def resolve_full_name(self, info):
        """Nome completo com chave do projeto"""
        if hasattr(self, 'key'):
            return f"[{self.key}] {self.name}"
        return self.name
    
    def resolve_assignee_names(self, info):
        """Nomes dos assignees"""
        return [user.name for user in self.user_ids]
    
    def resolve_is_overdue(self, info):
        """Verificar se está atrasada"""
        from datetime import datetime
        if self.date_deadline:
            return self.date_deadline < datetime.now().date()
        return False


class ProjectType(OdooObjectType):
    """GraphQL Type para project.project"""
    
    class Meta:
        model = 'project.project'
        interfaces = (graphene.relay.Node,)
    
    tasks = graphene.List(ProjectTaskType)
    
    def resolve_tasks(self, info):
        """Resolver tarefas do projeto"""
        return self.task_ids


class Query(graphene.ObjectType):
    """GraphQL Queries"""
    
    # Single object queries
    task = graphene.Field(
        ProjectTaskType,
        id=graphene.Int(required=True)
    )
    
    project = graphene.Field(
        ProjectType,
        id=graphene.Int(required=True)
    )
    
    # List queries
    tasks = graphene.List(
        ProjectTaskType,
        project_id=graphene.Int(),
        user_id=graphene.Int(),
        name=graphene.String(),
        limit=graphene.Int()
    )
    
    projects = graphene.List(
        ProjectType,
        name=graphene.String(),
        limit=graphene.Int()
    )
    
    # Resolvers
    
    def resolve_task(self, info, id):
        """Buscar tarefa por ID"""
        return info.context['env']['project.task'].browse(id)
    
    def resolve_project(self, info, id):
        """Buscar projeto por ID"""
        return info.context['env']['project.project'].browse(id)
    
    def resolve_tasks(self, info, project_id=None, user_id=None, 
                     name=None, limit=100):
        """Buscar tarefas com filtros"""
        env = info.context['env']
        domain = [('active', '=', True)]
        
        if project_id:
            domain.append(('project_id', '=', project_id))
        
        if user_id:
            domain.append(('user_ids', 'in', [user_id]))
        
        if name:
            domain.append(('name', 'ilike', name))
        
        return env['project.task'].search(domain, limit=limit)
    
    def resolve_projects(self, info, name=None, limit=100):
        """Buscar projetos"""
        env = info.context['env']
        domain = [('active', '=', True)]
        
        if name:
            domain.append(('name', 'ilike', name))
        
        return env['project.project'].search(domain, limit=limit)


class CreateTask(graphene.Mutation):
    """Mutation para criar tarefa"""
    
    class Arguments:
        name = graphene.String(required=True)
        project_id = graphene.Int(required=True)
        description = graphene.String()
        user_ids = graphene.List(graphene.Int)
        parent_id = graphene.Int()
        priority = graphene.String()
    
    task = graphene.Field(ProjectTaskType)
    success = graphene.Boolean()
    
    def mutate(self, info, name, project_id, **kwargs):
        env = info.context['env']
        
        values = {
            'name': name,
            'project_id': project_id,
        }
        
        # Adicionar campos opcionais
        if 'description' in kwargs:
            values['description'] = kwargs['description']
        
        if 'user_ids' in kwargs:
            values['user_ids'] = [(6, 0, kwargs['user_ids'])]
        
        if 'parent_id' in kwargs:
            values['parent_id'] = kwargs['parent_id']
        
        if 'priority' in kwargs:
            values['priority'] = kwargs['priority']
        
        task = env['project.task'].create(values)
        
        return CreateTask(task=task, success=True)


class UpdateTask(graphene.Mutation):
    """Mutation para atualizar tarefa"""
    
    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        description = graphene.String()
        user_ids = graphene.List(graphene.Int)
        priority = graphene.String()
        stage_id = graphene.Int()
    
    task = graphene.Field(ProjectTaskType)
    success = graphene.Boolean()
    
    def mutate(self, info, id, **kwargs):
        env = info.context['env']
        task = env['project.task'].browse(id)
        
        if not task.exists():
            return UpdateTask(task=None, success=False)
        
        values = {}
        
        if 'name' in kwargs:
            values['name'] = kwargs['name']
        
        if 'description' in kwargs:
            values['description'] = kwargs['description']
        
        if 'user_ids' in kwargs:
            values['user_ids'] = [(6, 0, kwargs['user_ids'])]
        
        if 'priority' in kwargs:
            values['priority'] = kwargs['priority']
        
        if 'stage_id' in kwargs:
            values['stage_id'] = kwargs['stage_id']
        
        task.write(values)
        
        return UpdateTask(task=task, success=True)


class DeleteTask(graphene.Mutation):
    """Mutation para arquivar tarefa"""
    
    class Arguments:
        id = graphene.Int(required=True)
    
    success = graphene.Boolean()
    
    def mutate(self, info, id):
        env = info.context['env']
        task = env['project.task'].browse(id)
        
        if not task.exists():
            return DeleteTask(success=False)
        
        task.write({'active': False})
        
        return DeleteTask(success=True)


class Mutation(graphene.ObjectType):
    """GraphQL Mutations"""
    
    create_task = CreateTask.Field()
    update_task = UpdateTask.Field()
    delete_task = DeleteTask.Field()


# Schema principal
schema = graphene.Schema(query=Query, mutation=Mutation)
```

---

### 🔑 Cliente Python GraphQL

```python
#!/usr/bin/env python3
"""
Cliente GraphQL para Odoo
"""

import requests
from typing import Dict, Any, Optional


class OdooGraphQLClient:
    """Cliente GraphQL para Odoo"""
    
    def __init__(self, url: str, api_token: str):
        self.url = f"{url.rstrip('/')}/graphql"
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
    
    def execute(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Executar query GraphQL"""
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        response = requests.post(
            self.url,
            json=payload,
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        
        result = response.json()
        
        if 'errors' in result:
            raise Exception(f"GraphQL errors: {result['errors']}")
        
        return result.get('data', {})
    
    # --- Queries ---
    
    def get_task(self, task_id: int) -> Dict:
        """Buscar tarefa por ID"""
        query = """
            query GetTask($id: Int!) {
                task(id: $id) {
                    id
                    name
                    description
                    fullName
                    assigneeNames
                    isOverdue
                    project {
                        id
                        name
                    }
                    parentId {
                        id
                        name
                    }
                    childIds {
                        id
                        name
                    }
                    userIds {
                        id
                        name
                    }
                    stageId {
                        id
                        name
                    }
                    priority
                    dateDeadline
                    kanbanState
                }
            }
        """
        
        result = self.execute(query, {'id': task_id})
        return result.get('task')
    
    def search_tasks(self, project_id: Optional[int] = None,
                    user_id: Optional[int] = None,
                    name: Optional[str] = None,
                    limit: int = 100) -> list:
        """Buscar tarefas com filtros"""
        query = """
            query SearchTasks($projectId: Int, $userId: Int, $name: String, $limit: Int) {
                tasks(projectId: $projectId, userId: $userId, name: $name, limit: $limit) {
                    id
                    name
                    fullName
                    assigneeNames
                    project {
                        id
                        name
                    }
                    priority
                    dateDeadline
                    kanbanState
                }
            }
        """
        
        variables = {
            'projectId': project_id,
            'userId': user_id,
            'name': name,
            'limit': limit
        }
        
        result = self.execute(query, variables)
        return result.get('tasks', [])
    
    def get_project_with_tasks(self, project_id: int) -> Dict:
        """Buscar projeto com todas as tarefas"""
        query = """
            query GetProject($id: Int!) {
                project(id: $id) {
                    id
                    name
                    tasks {
                        id
                        name
                        fullName
                        assigneeNames
                        parentId {
                            id
                            name
                        }
                        childIds {
                            id
                            name
                        }
                        priority
                        dateDeadline
                        kanbanState
                    }
                }
            }
        """
        
        result = self.execute(query, {'id': project_id})
        return result.get('project')
    
    # --- Mutations ---
    
    def create_task(self, name: str, project_id: int, **kwargs) -> Dict:
        """Criar nova tarefa"""
        mutation = """
            mutation CreateTask(
                $name: String!,
                $projectId: Int!,
                $description: String,
                $userIds: [Int],
                $parentId: Int,
                $priority: String
            ) {
                createTask(
                    name: $name,
                    projectId: $projectId,
                    description: $description,
                    userIds: $userIds,
                    parentId: $parentId,
                    priority: $priority
                ) {
                    success
                    task {
                        id
                        name
                        fullName
                    }
                }
            }
        """
        
        variables = {
            'name': name,
            'projectId': project_id,
            **kwargs
        }
        
        result = self.execute(mutation, variables)
        return result.get('createTask', {})
    
    def update_task(self, task_id: int, **kwargs) -> Dict:
        """Atualizar tarefa"""
        mutation = """
            mutation UpdateTask(
                $id: Int!,
                $name: String,
                $description: String,
                $userIds: [Int],
                $priority: String,
                $stageId: Int
            ) {
                updateTask(
                    id: $id,
                    name: $name,
                    description: $description,
                    userIds: $userIds,
                    priority: $priority,
                    stageId: $stageId
                ) {
                    success
                    task {
                        id
                        name
                        fullName
                    }
                }
            }
        """
        
        variables = {'id': task_id, **kwargs}
        
        result = self.execute(mutation, variables)
        return result.get('updateTask', {})
    
    def delete_task(self, task_id: int) -> bool:
        """Arquivar tarefa"""
        mutation = """
            mutation DeleteTask($id: Int!) {
                deleteTask(id: $id) {
                    success
                }
            }
        """
        
        result = self.execute(mutation, {'id': task_id})
        return result.get('deleteTask', {}).get('success', False)


# Exemplo de uso
if __name__ == '__main__':
    client = OdooGraphQLClient(
        url='http://localhost:8069',
        api_token='your_api_token_here'
    )
    
    # Buscar tarefas de um projeto
    print("\n=== Tasks from Project 1 ===")
    tasks = client.search_tasks(project_id=1, limit=5)
    for task in tasks:
        print(f"{task['id']}: {task['fullName']}")
        print(f"  Assignees: {', '.join(task['assigneeNames'])}")
    
    # Buscar projeto com tarefas aninhadas
    print("\n=== Project with Tasks ===")
    project = client.get_project_with_tasks(1)
    print(f"Project: {project['name']}")
    print(f"Tasks: {len(project['tasks'])}")
    
    # Criar tarefa
    print("\n=== Creating Task ===")
    result = client.create_task(
        name='GraphQL Test Task',
        project_id=1,
        description='Created via GraphQL',
        user_ids=[2, 3],
        priority='1'
    )
    
    if result['success']:
        task = result['task']
        print(f"Created: {task['fullName']}")
        
        # Atualizar tarefa
        print("\n=== Updating Task ===")
        update_result = client.update_task(
            task_id=task['id'],
            name='GraphQL Test Task (Updated)'
        )
        print(f"Updated: {update_result['task']['fullName']}")
        
        # Deletar tarefa
        print("\n=== Deleting Task ===")
        deleted = client.delete_task(task['id'])
        print(f"Deleted: {deleted}")
```

---

### 🌐 Exemplo com Apollo Client (JavaScript)

```javascript
// Cliente GraphQL para JavaScript/React
import { ApolloClient, InMemoryCache, gql, createHttpLink } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';

// Configurar link HTTP
const httpLink = createHttpLink({
    uri: 'http://localhost:8069/graphql',
});

// Configurar autenticação
const authLink = setContext((_, { headers }) => {
    const token = 'your_api_token_here';
    return {
        headers: {
            ...headers,
            authorization: token ? `Bearer ${token}` : "",
        }
    };
});

// Criar cliente Apollo
const client = new ApolloClient({
    link: authLink.concat(httpLink),
    cache: new InMemoryCache()
});

// Query para buscar tarefas
const GET_TASKS = gql`
    query GetTasks($projectId: Int, $limit: Int) {
        tasks(projectId: $projectId, limit: $limit) {
            id
            name
            fullName
            assigneeNames
            priority
            dateDeadline
            kanbanState
        }
    }
`;

// Mutation para criar tarefa
const CREATE_TASK = gql`
    mutation CreateTask(
        $name: String!,
        $projectId: Int!,
        $description: String,
        $userIds: [Int]
    ) {
        createTask(
            name: $name,
            projectId: $projectId,
            description: $description,
            userIds: $userIds
        ) {
            success
            task {
                id
                name
                fullName
            }
        }
    }
`;

// Uso em componente React
function TaskList() {
    const { loading, error, data } = useQuery(GET_TASKS, {
        variables: { projectId: 1, limit: 10 }
    });
    
    const [createTask] = useMutation(CREATE_TASK);
    
    if (loading) return <p>Loading...</p>;
    if (error) return <p>Error: {error.message}</p>;
    
    const handleCreateTask = async () => {
        await createTask({
            variables: {
                name: 'New Task',
                projectId: 1,
                description: 'Created from React',
                userIds: [2, 3]
            },
            refetchQueries: [{ query: GET_TASKS, variables: { projectId: 1 } }]
        });
    };
    
    return (
        <div>
            <button onClick={handleCreateTask}>Create Task</button>
            <ul>
                {data.tasks.map(task => (
                    <li key={task.id}>
                        {task.fullName}
                        <br />
                        Assignees: {task.assigneeNames.join(', ')}
                    </li>
                ))}
            </ul>
        </div>
    );
}
```

---

## 5. Comparação das Abordagens

### 📊 Tabela Comparativa

| Critério | XML-RPC | JSON-RPC | REST API | GraphQL |
|----------|---------|----------|----------|---------|
| **Nativo no Odoo** | ✅ Sim | ✅ Sim | ❌ Módulo extra | ❌ Módulo extra |
| **Maturidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Documentação** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Performance** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Facilidade de Uso** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Debugging** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Tamanho Payload** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Cache HTTP** | ❌ | ❌ | ✅ | ⚠️ Parcial |
| **Autenticação** | Session/Pass | Session/Pass | Token | Token |
| **Flexibilidade Query** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Compatibilidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Suporte Comunidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

---

### 💡 Quando Usar Cada Abordagem

#### ✅ Use **XML-RPC** quando:
- Precisa de **máxima compatibilidade** com todas as versões do Odoo
- Está trabalhando em ambiente **corporativo conservador**
- Não quer instalar módulos extras
- Prioriza **estabilidade e confiabilidade** sobre performance

#### ✅ Use **JSON-RPC** quando:
- Quer **melhor performance** que XML-RPC
- Está construindo **aplicação JavaScript/Node.js**
- Precisa de payloads menores (mobile/largura de banda limitada)
- Não quer instalar módulos extras mas quer JSON

#### ✅ Use **REST API** quando:
- Está integrando com **serviços externos modernos**
- Precisa de autenticação por **token** (mais segura)
- Quer **padrões HTTP** (GET/POST/PUT/DELETE)
- Time está familiarizado com **REST**
- Pode instalar e manter módulo extra

#### ✅ Use **GraphQL** quando:
- Precisa de **queries muito flexíveis**
- Quer **minimizar requisições** (buscar relações nested em uma query)
- Está construindo **aplicação mobile** (economizar dados)
- Frontend React/Vue.js com **Apollo Client**
- Pode investir tempo em setup e aprendizado

---

### ⚖️ Prós e Contras para Sincronização Bidirecional

#### XML-RPC / JSON-RPC

**Prós:**
- ✅ Controle total sobre operações CRUD
- ✅ Campos `write_date` e `create_date` para rastreamento
- ✅ Pode buscar mudanças incrementais facilmente
- ✅ Suporte a transações complexas

**Contras:**
- ❌ Múltiplas requisições para relações nested
- ❌ Sem notificações push nativas
- ❌ Precisa implementar polling ou webhooks

#### REST API

**Prós:**
- ✅ Webhooks mais fáceis de implementar
- ✅ Cacheing HTTP nativo
- ✅ Stateless (escalabilidade)

**Contras:**
- ❌ Requer módulo extra
- ❌ Múltiplas requisições para relações

#### GraphQL

**Prós:**
- ✅ Uma query busca tudo (projeto + tarefas + subtarefas)
- ✅ Subscriptions para real-time (se implementado)
- ✅ Minimiza over-fetching

**Contras:**
- ❌ Mais complexo de implementar
- ❌ Requer módulo extra
- ❌ Curva de aprendizado

---

## 6. Recomendações

### 🏆 Para Sincronização Bidirecional de Projetos e Tarefas

#### 🥇 Opção Recomendada: **JSON-RPC**

**Por quê:**
1. **Nativo no Odoo** - Sem dependências extras
2. **Boa performance** - Payloads JSON compactos
3. **Fácil debugging** - JSON legível
4. **Bem documentado** - Muitos exemplos na comunidade
5. **Suporte a campos de tracking** - `write_date`, `create_date`

**Estratégia de Sincronização:**

```python
class OdooBidirectionalSync:
    """Sincronização bidirecional Odoo <-> Sistema Externo"""
    
    def __init__(self, odoo_client, external_system):
        self.odoo = odoo_client
        self.external = external_system
        self.mapping = {}  # {odoo_id: external_id}
    
    def sync_from_odoo(self, last_sync):
        """Odoo -> Sistema Externo"""
        # Buscar mudanças desde última sync
        changed_tasks = self.odoo.execute_kw(
            'project.task', 'search_read',
            [[
                '|',
                ['write_date', '>', last_sync],
                ['create_date', '>', last_sync]
            ]],
            {'fields': [
                'id', 'name', 'description', 'project_id',
                'parent_id', 'user_ids', 'write_date', 'create_date'
            ]}
        )
        
        for task in changed_tasks:
            external_id = self.mapping.get(task['id'])
            
            if external_id:
                # Atualizar no sistema externo
                self.external.update_task(external_id, task)
            else:
                # Criar no sistema externo
                external_id = self.external.create_task(task)
                self.mapping[task['id']] = external_id
        
        return len(changed_tasks)
    
    def sync_to_odoo(self, external_changes):
        """Sistema Externo -> Odoo"""
        for external_task in external_changes:
            odoo_id = self.get_odoo_id(external_task['id'])
            
            task_data = {
                'name': external_task['name'],
                'description': external_task['description'],
                'project_id': self.map_project_id(external_task['project_id']),
            }
            
            if odoo_id:
                # Verificar qual é mais recente
                odoo_task = self.odoo.execute_kw(
                    'project.task', 'read',
                    [[odoo_id]], {'fields': ['write_date']}
                )[0]
                
                if external_task['modified_at'] > odoo_task['write_date']:
                    # Atualizar Odoo
                    self.odoo.execute_kw(
                        'project.task', 'write',
                        [[odoo_id], task_data]
                    )
            else:
                # Criar no Odoo
                odoo_id = self.odoo.execute_kw(
                    'project.task', 'create',
                    [task_data]
                )
                self.mapping[odoo_id] = external_task['id']
    
    def get_odoo_id(self, external_id):
        """Buscar odoo_id por external_id"""
        for odoo_id, ext_id in self.mapping.items():
            if ext_id == external_id:
                return odoo_id
        return None
```

---

#### 🥈 Opção Alternativa: **REST API** (se puder instalar módulo)

Se você pode instalar o módulo `base_rest`:

**Vantagens:**
- Autenticação por token (mais segura)
- Webhooks mais fáceis
- Melhor integração com sistemas modernos

**Implementação de Webhook:**

```python
# No Odoo (módulo customizado)
from odoo import models, api

class ProjectTaskWebhook(models.Model):
    _inherit = 'project.task'
    
    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        
        # Enviar webhook
        for task in tasks:
            self._send_webhook('task.created', task)
        
        return tasks
    
    def write(self, vals):
        result = super().write(vals)
        
        # Enviar webhook
        for task in self:
            self._send_webhook('task.updated', task)
        
        return result
    
    def _send_webhook(self, event, task):
        """Enviar notificação webhook"""
        import requests
        
        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'project.webhook_url'
        )
        
        if webhook_url:
            payload = {
                'event': event,
                'task': {
                    'id': task.id,
                    'name': task.name,
                    'project_id': task.project_id.id,
                    'user_ids': task.user_ids.ids,
                }
            }
            
            requests.post(webhook_url, json=payload, timeout=5)
```

---

### 📋 Checklist para Implementação

#### Preparação
- [ ] Escolher abordagem (JSON-RPC recomendado)
- [ ] Configurar autenticação (usuário técnico dedicado)
- [ ] Mapear campos entre sistemas
- [ ] Definir direção da sincronização (Odoo -> Externo, Externo -> Odoo, ou ambos)

#### Sincronização Inicial
- [ ] Exportar dados existentes do Odoo
- [ ] Criar mapeamento ID Odoo <-> ID Externo
- [ ] Importar no sistema externo
- [ ] Validar integridade dos dados

#### Sincronização Contínua
- [ ] Implementar rastreamento de mudanças (`write_date`, `create_date`)
- [ ] Criar job periódico (cronjob/celery)
- [ ] Implementar resolução de conflitos
- [ ] Logging e monitoramento

#### Tratamento de Erros
- [ ] Retry logic para falhas temporárias
- [ ] Queue para operações failed
- [ ] Alertas para administradores
- [ ] Rollback em caso de erro crítico

#### Testes
- [ ] Teste de criação bidirecional
- [ ] Teste de atualização bidirecional
- [ ] Teste de conflitos (mesma tarefa modificada nos dois lados)
- [ ] Teste de performance (sincronização de 1000+ tarefas)
- [ ] Teste de hierarquia (parent_id / subtarefas)

---

### 🔐 Considerações de Segurança

1. **Usuário Técnico Dedicado**
   ```python
   # Criar usuário apenas para API
   # Sem direitos de administração
   # Apenas acesso a project.project e project.task
   ```

2. **Autenticação Segura**
   ```python
   # Armazenar credenciais em variáveis de ambiente
   import os
   
   ODOO_URL = os.getenv('ODOO_URL')
   ODOO_DB = os.getenv('ODOO_DB')
   ODOO_USER = os.getenv('ODOO_USER')
   ODOO_PASS = os.getenv('ODOO_PASS')
   ```

3. **Rate Limiting**
   ```python
   import time
   from functools import wraps
   
   def rate_limit(max_per_second):
       min_interval = 1.0 / max_per_second
       last_called = [0.0]
       
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               elapsed = time.time() - last_called[0]
               left_to_wait = min_interval - elapsed
               
               if left_to_wait > 0:
                   time.sleep(left_to_wait)
               
               ret = func(*args, **kwargs)
               last_called[0] = time.time()
               return ret
           
           return wrapper
       return decorator
   
   @rate_limit(10)  # Max 10 requests/second
   def call_odoo_api():
       pass
   ```

4. **Validação de Dados**
   ```python
   def validate_task_data(data):
       """Validar dados antes de enviar ao Odoo"""
       required = ['name', 'project_id']
       
       for field in required:
           if field not in data:
               raise ValueError(f"Missing required field: {field}")
       
       # Validar tipos
       if not isinstance(data['project_id'], int):
           raise ValueError("project_id must be an integer")
       
       return True
   ```

---

### 📈 Monitoramento e Logs

```python
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('odoo_sync.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('odoo_sync')


class MonitoredOdooClient(OdooJSONRPCClient):
    """Cliente Odoo com monitoramento"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            'requests': 0,
            'errors': 0,
            'created': 0,
            'updated': 0,
            'deleted': 0,
        }
    
    def execute_kw(self, model, method, *args, **kwargs):
        """Execute with logging and stats"""
        self.stats['requests'] += 1
        
        try:
            logger.info(f"Calling {model}.{method}")
            result = super().execute_kw(model, method, *args, **kwargs)
            
            # Track operations
            if method == 'create':
                self.stats['created'] += 1
            elif method == 'write':
                self.stats['updated'] += 1
            elif method == 'unlink':
                self.stats['deleted'] += 1
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error in {model}.{method}: {str(e)}")
            raise
    
    def get_stats(self):
        """Get synchronization statistics"""
        return self.stats
```

---

## 📚 Recursos Adicionais

### Documentação Oficial
- [Odoo External API](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)
- [Odoo ORM API](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)
- [OCA Rest Framework](https://github.com/OCA/rest-framework)

### Bibliotecas Python
```bash
# XML-RPC (nativo Python)
# Nenhuma dependência extra

# Alternativa ORM-like para Odoo
pip install odoorpc

# Exemplo odoorpc
import odoorpc

odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('odoo', 'admin', 'password')

tasks = odoo.env['project.task'].search([])
for task_id in tasks:
    task = odoo.env['project.task'].browse(task_id)
    print(task.name)
```

### Ferramentas de Teste
```bash
# Postman/Insomnia - Para testar APIs REST/GraphQL
# curl - Para testes rápidos via terminal

# Exemplo curl para JSON-RPC
curl -X POST \
  http://localhost:8069/jsonrpc \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "service": "object",
        "method": "execute_kw",
        "args": ["odoo", 2, "password", "project.task", "search_read", [[]], {"fields": ["id", "name"], "limit": 5}]
    },
    "id": 1
}'
```

---

## 🎯 Conclusão

Para **sincronização bidirecional de projetos e tarefas** no Odoo 18:

### Recomendação Final: **JSON-RPC**

**Motivos:**
1. ✅ Nativo no Odoo (sem módulos extras)
2. ✅ Excelente performance
3. ✅ Bem documentado e suportado
4. ✅ Suporte completo a todas as operações CRUD
5. ✅ Campos de tracking (`write_date`, `create_date`)
6. ✅ Fácil implementação de sincronização incremental

**Implementação:**
- Use a classe `OdooJSONRPCClient` fornecida acima
- Implemente sincronização incremental baseada em `write_date`
- Use mapeamento ID Odoo <-> ID Externo
- Implemente resolução de conflitos (last-write-wins ou manual)
- Configure logging e monitoramento
- Teste exaustivamente hierarquia de tarefas (parent_id)

**Próximos Passos:**
1. Implementar cliente JSON-RPC
2. Criar job de sincronização periódica (ex: a cada 5 minutos)
3. Implementar mapeamento de IDs persistente (banco de dados)
4. Configurar alertas para erros
5. Documentar processo de troubleshooting

---

**Documento criado em:** Fev 28, 2026  
**Versão Odoo:** 18.0  
**Autor:** Documentação Técnica - Integração API Odoo

