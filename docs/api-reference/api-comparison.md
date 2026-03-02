# Resumo Executivo: Integração com API Odoo 18

## 🎯 Objetivo

Escolher a melhor abordagem para sincronização bidirecional de **projetos e tarefas** entre Odoo 18 e sistema externo.

---

## 📊 Comparação Rápida

| Característica | XML-RPC | JSON-RPC | REST API | GraphQL |
|---------------|---------|----------|----------|---------|
| **Nativo no Odoo** | ✅ Sim | ✅ Sim | ❌ Módulo | ❌ Módulo |
| **Setup** | ⚡ Imediato | ⚡ Imediato | 🔧 Configuração | 🔧 Complexo |
| **Performance** | 🐌 Lenta | 🚀 Rápida | 🚀 Rápida | ⚡ Muito Rápida |
| **Tamanho Payload** | 📦 Grande (XML) | 📄 Pequeno (JSON) | 📄 Pequeno | 📄 Mínimo |
| **Debugging** | 😕 Difícil | 😊 Fácil | 😊 Fácil | 😐 Médio |
| **Documentação** | 📚 Excelente | 📖 Boa | 📝 Limitada | 📝 Limitada |
| **Comunidade** | 👥 Muito Grande | 👥 Grande | 👤 Pequena | 👤 Pequena |
| **Curva Aprendizado** | ⭐ Fácil | ⭐ Fácil | ⭐⭐ Médio | ⭐⭐⭐ Difícil |
| **Sync Bidirecional** | ✅ Excelente | ✅ Excelente | ✅ Bom | ⚠️ Complexo |

---

## 🏆 Recomendação: **JSON-RPC**

### Por quê JSON-RPC?

#### ✅ Vantagens Decisivas

1. **Zero Setup** 
   - Nativo no Odoo 18
   - Sem módulos extras
   - Funciona imediatamente

2. **Performance Superior**
   - Payloads 60-70% menores que XML-RPC
   - Parsing JSON muito mais rápido que XML
   - Ideal para sincronização frequente

3. **Developer-Friendly**
   - JSON é legível e fácil de debugar
   - Suporte nativo em todas as linguagens modernas
   - Console browser para testes rápidos

4. **Sincronização Bidirecional**
   - Campos `write_date` e `create_date` nativos
   - Fácil implementação de sync incremental
   - Controle total sobre conflitos

5. **Estabilidade**
   - Mesma estabilidade do XML-RPC
   - Mantido pela Odoo SA
   - Retrocompatível

#### ❌ Quando NÃO usar JSON-RPC

- Sistema legado que só fala XML
- Compliance requer apenas protocolos XML
- Já tem infraestrutura XML-RPC funcionando

---

## 📋 Modelos Principais

### `project.project` - Projetos

```python
{
    'id': 1,
    'name': 'Projeto API',
    'user_id': [2, 'Admin'],           # Gerente (Many2one)
    'partner_id': [5, 'Cliente XYZ'],  # Cliente (Many2one)
    'task_ids': [10, 11, 12],          # Tarefas (One2many)
    'active': True,
    'date_start': '2026-01-01',
    'date': '2026-12-31',
    'create_date': '2026-01-01 10:00:00',
    'write_date': '2026-02-28 15:30:00'
}
```

### `project.task` - Tarefas

```python
{
    'id': 10,
    'name': 'Implementar API',
    'description': '<p>Descrição HTML</p>',
    'project_id': [1, 'Projeto API'],     # Projeto (Many2one)
    'parent_id': [8, 'Tarefa Pai'],       # Tarefa pai (Many2one) - Para SUBTAREFAS
    'child_ids': [11, 12],                # Subtarefas (One2many)
    'user_ids': [2, 3],                   # Assignees (Many2many) ⭐ IMPORTANTE
    'stage_id': [1, 'Em Progresso'],      # Estágio
    'tag_ids': [5, 6],                    # Tags
    'priority': '1',                      # '0'=Normal, '1'=Alta
    'date_deadline': '2026-03-15',
    'kanban_state': 'normal',             # 'normal', 'done', 'blocked'
    'active': True,
    'create_date': '2026-02-01 09:00:00',
    'write_date': '2026-02-28 14:20:00'
}
```

---

## 🔑 Operações Críticas

### 1. Autenticação

```python
import requests

url = 'http://localhost:8069'
db = 'odoo'
username = 'admin@example.com'
password = 'admin'

session = requests.Session()

# Autenticar
response = session.post(
    f'{url}/web/session/authenticate',
    json={
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'db': db,
            'login': username,
            'password': password
        },
        'id': 1
    }
)

result = response.json()
uid = result['result']['uid']
```

### 2. Buscar Tarefas

```python
# Buscar todas as tarefas de um projeto
def get_tasks(session, url, db, uid, password, project_id):
    response = session.post(
        f'{url}/jsonrpc',
        json={
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'service': 'object',
                'method': 'execute_kw',
                'args': [
                    db, uid, password,
                    'project.task',
                    'search_read',
                    [[['project_id', '=', project_id]]],
                    {
                        'fields': [
                            'id', 'name', 'parent_id', 'child_ids',
                            'user_ids', 'stage_id', 'write_date'
                        ]
                    }
                ]
            },
            'id': 1
        }
    )
    
    return response.json()['result']
```

### 3. Filtrar por Usuário

```python
# Buscar tarefas de um usuário específico
def get_user_tasks(session, url, db, uid, password, user_id):
    response = session.post(
        f'{url}/jsonrpc',
        json={
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'service': 'object',
                'method': 'execute_kw',
                'args': [
                    db, uid, password,
                    'project.task',
                    'search_read',
                    [[
                        ['user_ids', 'in', [user_id]],  # ⭐ Many2many
                        ['active', '=', True]
                    ]],
                    {'fields': ['id', 'name', 'project_id']}
                ]
            },
            'id': 1
        }
    )
    
    return response.json()['result']
```

### 4. Criar Tarefa com Subtarefas

```python
def create_task(session, url, db, uid, password, name, project_id, parent_id=None):
    values = {
        'name': name,
        'project_id': project_id
    }
    
    if parent_id:
        values['parent_id'] = parent_id  # Define como subtarefa
    
    response = session.post(
        f'{url}/jsonrpc',
        json={
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'service': 'object',
                'method': 'execute_kw',
                'args': [
                    db, uid, password,
                    'project.task',
                    'create',
                    [values]
                ]
            },
            'id': 1
        }
    )
    
    return response.json()['result']  # Retorna ID da nova tarefa

# Criar tarefa pai
parent_id = create_task(session, url, db, uid, password, 
                       'Tarefa Pai', project_id=1)

# Criar subtarefas
for i in range(3):
    create_task(session, url, db, uid, password,
               f'Subtarefa {i+1}', project_id=1, parent_id=parent_id)
```

### 5. Atualizar Assignees (Many2many)

```python
def assign_users(session, url, db, uid, password, task_id, user_ids):
    """
    Many2many operations:
    (6, 0, [ids]) - Replace all (recomendado)
    (4, id, 0)    - Add link
    (3, id, 0)    - Remove link
    (5, 0, 0)     - Clear all
    """
    
    response = session.post(
        f'{url}/jsonrpc',
        json={
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'service': 'object',
                'method': 'execute_kw',
                'args': [
                    db, uid, password,
                    'project.task',
                    'write',
                    [[task_id], {
                        'user_ids': [(6, 0, user_ids)]  # Substituir todos
                    }]
                ]
            },
            'id': 1
        }
    )
    
    return response.json()['result']

# Atribuir usuários 2, 3 e 4 à tarefa 10
assign_users(session, url, db, uid, password, task_id=10, user_ids=[2, 3, 4])
```

---

## 🔄 Estratégia de Sincronização Bidirecional

### Arquitetura Recomendada

```
┌─────────────────┐         ┌─────────────────┐
│                 │         │                 │
│  Sistema        │◄────────┤  Odoo 18        │
│  Externo        │────────►│  JSON-RPC       │
│                 │         │                 │
└─────────────────┘         └─────────────────┘
       ▲                             ▲
       │                             │
       └─────────┬───────────────────┘
                 │
         ┌───────┴────────┐
         │  Sync Manager  │
         │  - Mapping     │
         │  - Conflicts   │
         │  - Logging     │
         └────────────────┘
```

### Fluxo de Sincronização

#### 1. Odoo → Sistema Externo

```python
def sync_from_odoo(last_sync_date):
    # Buscar mudanças desde última sync
    changed_tasks = get_changes_since(last_sync_date)
    
    for task in changed_tasks:
        external_id = get_external_id(task['id'])
        
        if external_id:
            # Atualizar no sistema externo
            external_system.update_task(external_id, task)
        else:
            # Criar no sistema externo
            external_id = external_system.create_task(task)
            save_mapping(task['id'], external_id)
```

#### 2. Sistema Externo → Odoo

```python
def sync_to_odoo(external_changes):
    for ext_task in external_changes:
        odoo_id = get_odoo_id(ext_task['id'])
        
        if odoo_id:
            # Verificar qual é mais recente
            odoo_task = get_task(odoo_id)
            
            if ext_task['modified_at'] > odoo_task['write_date']:
                # Atualizar Odoo
                update_task(odoo_id, ext_task)
        else:
            # Criar no Odoo
            odoo_id = create_task(ext_task)
            save_mapping(odoo_id, ext_task['id'])
```

### Mapeamento de IDs

```python
# Persistir em banco de dados ou arquivo
id_mapping = {
    # odoo_id: external_id
    10: 'ext-uuid-001',
    11: 'ext-uuid-002',
    12: 'ext-uuid-003'
}

# Reverse mapping
reverse_mapping = {v: k for k, v in id_mapping.items()}
```

### Resolução de Conflitos

**Estratégia Recomendada: Last-Write-Wins**

```python
def resolve_conflict(odoo_task, external_task):
    if external_task['modified_at'] > odoo_task['write_date']:
        return 'external'  # Usar versão do sistema externo
    else:
        return 'odoo'  # Usar versão do Odoo
```

**Estratégias Alternativas:**
- **Manual Review**: Marcar para revisão humana
- **Merge**: Combinar mudanças (complexo)
- **Odoo Always Wins**: Sistema master
- **External Always Wins**: Sistema externo master

---

## ⚙️ Configuração Recomendada

### 1. Usuário Técnico

Criar usuário dedicado apenas para API:

```sql
-- No Odoo
Settings > Users & Companies > Users > Create

Nome: API Integration User
Email: api@yourdomain.com
Access Rights:
  - Project: Manager
  - Contacts: User
  - Technical: NO
```

### 2. Frequência de Sincronização

```python
# Cron job a cada 5 minutos
*/5 * * * * /usr/bin/python3 /path/to/sync_script.py

# Ou serviço contínuo com sleep
while True:
    sync_bidirectional()
    time.sleep(300)  # 5 minutos
```

### 3. Logging e Monitoramento

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('odoo_sync.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('odoo_sync')

# Em cada operação
logger.info(f"Synced {count} tasks from Odoo")
logger.error(f"Failed to sync task {task_id}: {error}")
```

### 4. Tratamento de Erros

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def sync_with_retry():
    try:
        sync_bidirectional()
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise
```

---

## 🚀 Quick Start

### Instalação

```bash
# Apenas requests é necessário para JSON-RPC
pip install requests

# Opcional: para retry logic
pip install tenacity
```

### Código Mínimo Funcional

```python
#!/usr/bin/env python3
import requests

# Config
URL = 'http://localhost:8069'
DB = 'odoo'
USER = 'admin@example.com'
PASS = 'admin'

# Autenticar
session = requests.Session()
auth = session.post(f'{URL}/web/session/authenticate', json={
    'jsonrpc': '2.0',
    'method': 'call',
    'params': {'db': DB, 'login': USER, 'password': PASS},
    'id': 1
}).json()

uid = auth['result']['uid']

# Buscar tarefas
def call(model, method, args=[], kwargs={}):
    return session.post(f'{URL}/jsonrpc', json={
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'service': 'object',
            'method': 'execute_kw',
            'args': [DB, uid, PASS, model, method, args, kwargs]
        },
        'id': 1
    }).json()['result']

# Buscar projetos
projects = call('project.project', 'search_read', 
                [[]], {'fields': ['id', 'name'], 'limit': 5})

for p in projects:
    print(f"{p['id']}: {p['name']}")
    
    # Buscar tarefas do projeto
    tasks = call('project.task', 'search_read',
                [[['project_id', '=', p['id']]]],
                {'fields': ['id', 'name', 'user_ids']})
    
    for t in tasks:
        print(f"  - {t['name']}")
```

---

## 📚 Recursos Adicionais

### Arquivos do Projeto

1. **`docs/api-reference/integration-guide.md`**
   - Guia completo com todos os detalhes
   - Exemplos de XML-RPC, JSON-RPC, REST, GraphQL
   - 2700+ linhas de documentação técnica

2. **`docs/api-reference/api-comparison.md`** (este arquivo)
   - Resumo executivo
   - Decisões rápidas
   - Quick start

3. **`docs/architecture/multi-agent-timesheets.md`**
   - Arquitetura de timesheets para múltiplos agentes IA
   - Pool de agentes e alocação automática

### Documentação Oficial

- [Odoo External API](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)
- [Odoo ORM API](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)

### Bibliotecas Python

```bash
# OdooRPC - Wrapper ORM-like
pip install odoorpc

# Uso
import odoorpc
odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('odoo', 'admin', 'password')

tasks = odoo.env['project.task'].search([])
for task_id in tasks:
    task = odoo.env['project.task'].browse(task_id)
    print(task.name)
```

---

## ✅ Checklist de Implementação

### Fase 1: Setup Inicial
- [ ] Instalar dependências (`requests`)
- [ ] Criar usuário técnico no Odoo
- [ ] Testar autenticação JSON-RPC
- [ ] Mapear campos necessários

### Fase 2: Sincronização Unidirecional
- [ ] Implementar sync Odoo → Externo
- [ ] Criar mapeamento de IDs
- [ ] Testar com dados reais
- [ ] Implementar logging

### Fase 3: Sincronização Bidirecional
- [ ] Implementar sync Externo → Odoo
- [ ] Implementar resolução de conflitos
- [ ] Testar modificações simultâneas
- [ ] Validar hierarquia de tarefas (parent_id)

### Fase 4: Produção
- [ ] Configurar cron job / serviço
- [ ] Implementar retry logic
- [ ] Configurar alertas de erro
- [ ] Documentar processo de troubleshooting
- [ ] Backup do mapeamento de IDs

---

## 🎯 Decisão Final

### Use **JSON-RPC** se:
- ✅ Quer começar AGORA (zero setup)
- ✅ Prioriza estabilidade e confiabilidade
- ✅ Precisa de sincronização bidirecional robusta
- ✅ Time confortável com Python/JavaScript

### Considere **REST API** se:
- ⚠️ Pode instalar módulos extras
- ⚠️ Precisa de autenticação por token
- ⚠️ Integrará com muitos sistemas externos
- ⚠️ Quer webhooks nativos

### Evite **GraphQL** para este caso:
- ❌ Muito complexo para o caso de uso
- ❌ Overhead não justificado
- ❌ Módulo extra necessário
- ❌ Menos maduro no ecossistema Odoo

---

## 📞 Suporte

Para dúvidas sobre a implementação:

1. Consulte o guia completo: `docs/api-reference/integration-guide.md`
2. Veja a arquitetura de multi-agentes: `docs/architecture/multi-agent-timesheets.md`
3. Documentação oficial Odoo: https://www.odoo.com/documentation/18.0/

---

**Última atualização:** Fev 28, 2026  
**Versão Odoo:** 18.0  
**Recomendação:** JSON-RPC para sincronização bidirecional

