# 📚 Documentação de Integração com API Odoo 18

## 📖 Índice de Documentação

Esta pasta contém documentação completa e detalhada sobre integração com a API do Odoo 18, com foco em **gerenciamento de projetos e tarefas**.

---

## 📁 Arquivos Disponíveis

### 1. 🎯 **API_INTEGRATION_SUMMARY.md** (COMECE AQUI!)
**Tamanho:** 17 KB | **Linhas:** 631

**Conteúdo:**
- ✅ Resumo executivo
- ✅ Tabela comparativa das APIs
- ✅ Recomendação: JSON-RPC
- ✅ Código mínimo funcional
- ✅ Quick start em 5 minutos
- ✅ Checklist de implementação

**Para quem:**
- Tomadores de decisão
- Desenvolvedores que querem visão geral rápida
- Quick reference

**Tempo de leitura:** 10-15 minutos

---

### 2. 📘 **odoo_api_integration_guide.md** (GUIA COMPLETO)
**Tamanho:** 73 KB | **Linhas:** 2.733

**Conteúdo:**
- 📋 Odoo XML-RPC API (completo)
- 📋 Odoo JSON-RPC API (completo)
- 📋 Odoo REST API (módulos OCA)
- 📋 GraphQL para Odoo (módulos OCA)
- 🔐 Autenticação detalhada
- 📖 CRUD completo (Create, Read, Update, Delete)
- 🔍 Filtros avançados
- 👥 Gerenciamento de usuários/assignees
- 🌳 Hierarquia de tarefas (parent_id/subtasks)
- 🔄 Sincronização bidirecional
- 📊 Comparação detalhada
- ⚖️ Prós e contras
- 🎯 Recomendações finais

**Para quem:**
- Desenvolvedores implementando integração
- Arquitetos de software
- Tech leads
- Documentação de referência

**Tempo de leitura:** 1-2 horas (consulta contínua)

---

### 3. 💻 **odoo_api_python_examples.py** (CÓDIGO EXECUTÁVEL)
**Tamanho:** 37 KB | **Linhas:** 1.134

**Conteúdo:**
- ✅ Classe `OdooXMLRPCClient` completa
- ✅ Classe `OdooJSONRPCClient` completa
- ✅ Classe `OdooBidirectionalSync` completa
- ✅ 50+ métodos prontos para uso
- ✅ Exemplos executáveis
- ✅ Código comentado linha por linha
- ✅ Tratamento de erros
- ✅ Logging configurado

**Funcionalidades implementadas:**
- Autenticação
- Buscar projetos
- Buscar tarefas
- Criar tarefas
- Criar subtarefas
- Atualizar tarefas
- Deletar/arquivar tarefas
- Filtrar por usuário
- Filtrar por projeto
- Gerenciar assignees (Many2many)
- Hierarquia de tarefas completa
- Sincronização bidirecional
- Resolução de conflitos

**Como usar:**
```bash
# Editar configurações no topo do arquivo
ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'odoo'
ODOO_USERNAME = 'admin@example.com'
ODOO_PASSWORD = 'admin'

# Executar exemplos
python docs/odoo_api_python_examples.py
```

**Para quem:**
- Desenvolvedores Python
- Copy-paste de código funcional
- Base para customização

---

## 🚀 Por Onde Começar?

### Se você quer...

#### ⚡ **Decisão rápida (5 min)**
→ Leia: `API_INTEGRATION_SUMMARY.md`
- Veja a tabela comparativa
- Leia a seção "Recomendação"
- Copie o código "Quick Start"

#### 🎓 **Entender todas as opções (1h)**
→ Leia: `odoo_api_integration_guide.md`
- Seções: 1-4 (XML-RPC, JSON-RPC, REST, GraphQL)
- Seção 5 (Comparação)
- Seção 6 (Recomendações)

#### 💻 **Implementar agora (30 min)**
→ Use: `odoo_api_python_examples.py`
- Configure as variáveis
- Execute os exemplos
- Customize para seu caso

#### 🔄 **Sincronização bidirecional completa (2-4h)**
→ Leia: `odoo_api_integration_guide.md` (seção completa)
→ Use: `odoo_api_python_examples.py` (classe `OdooBidirectionalSync`)
→ Referência: `API_INTEGRATION_SUMMARY.md` (checklist)

---

## 🎯 Recomendação Rápida

### Para Sincronização Bidirecional de Projetos e Tarefas:

**Use: JSON-RPC**

**Por quê:**
- ✅ Nativo no Odoo (zero setup)
- ✅ Performance superior ao XML-RPC
- ✅ Payloads JSON pequenos
- ✅ Fácil de debugar
- ✅ Bem documentado
- ✅ Excelente para sync bidirecional

**Código mínimo:**
```python
import requests

session = requests.Session()
auth = session.post('http://localhost:8069/web/session/authenticate', 
    json={'jsonrpc': '2.0', 'method': 'call',
          'params': {'db': 'odoo', 'login': 'admin', 'password': 'admin'},
          'id': 1}).json()

uid = auth['result']['uid']

# Buscar tarefas
def call(model, method, args=[], kwargs={}):
    return session.post('http://localhost:8069/jsonrpc', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'service': 'object', 'method': 'execute_kw',
                  'args': ['odoo', uid, 'admin', model, method, args, kwargs]},
        'id': 1}).json()['result']

tasks = call('project.task', 'search_read', 
            [[['project_id', '=', 1]]], 
            {'fields': ['id', 'name', 'user_ids']})
```

---

## 📋 Tópicos Principais Cobertos

### Autenticação
- ✅ XML-RPC
- ✅ JSON-RPC
- ✅ Tokens REST
- ✅ Sessões

### Modelos Odoo
- ✅ `project.project` (Projetos)
- ✅ `project.task` (Tarefas)
- ✅ `res.users` (Usuários)
- ✅ `project.task.type` (Estágios)

### Operações CRUD
- ✅ Create (criar tarefas/projetos)
- ✅ Read (buscar com filtros)
- ✅ Update (atualizar campos)
- ✅ Delete (soft/hard delete)

### Funcionalidades Avançadas
- ✅ Hierarquia de tarefas (parent_id)
- ✅ Subtarefas recursivas
- ✅ Many2many (user_ids, tag_ids)
- ✅ Many2one (project_id, stage_id)
- ✅ Filtros complexos (domain)
- ✅ Ordenação e limite
- ✅ Campos relacionados

### Sincronização
- ✅ Incremental (write_date, create_date)
- ✅ Bidirecional (Odoo ↔ Externo)
- ✅ Mapeamento de IDs
- ✅ Resolução de conflitos
- ✅ Retry logic
- ✅ Logging

---

## 🔧 Instalação e Setup

### Dependências Python

```bash
# Apenas requests (para JSON-RPC)
pip install requests

# Opcional: retry logic
pip install tenacity

# Opcional: ORM-like wrapper
pip install odoorpc
```

### Configuração Odoo

1. **Criar usuário técnico:**
   - Settings > Users > Create
   - Nome: `API Integration User`
   - Access Rights: Project Manager

2. **Anotar credenciais:**
   - URL: `http://localhost:8069`
   - Database: `odoo`
   - Username: `api@yourdomain.com`
   - Password: `sua_senha_segura`

3. **Testar conexão:**
   ```bash
   python docs/odoo_api_python_examples.py
   ```

---

## 📊 Estrutura dos Dados

### Projeto (project.project)
```python
{
    'id': 1,
    'name': 'Meu Projeto',
    'user_id': [2, 'Admin'],        # Gerente
    'task_ids': [10, 11, 12],       # Lista de IDs de tarefas
    'active': True,
    'write_date': '2026-02-28 15:30:00'
}
```

### Tarefa (project.task)
```python
{
    'id': 10,
    'name': 'Implementar API',
    'project_id': [1, 'Meu Projeto'],
    'parent_id': False,              # ou [8, 'Tarefa Pai']
    'child_ids': [11, 12],           # IDs das subtarefas
    'user_ids': [2, 3],              # IDs dos assignees
    'stage_id': [1, 'Em Progresso'],
    'priority': '1',                 # '0' ou '1'
    'date_deadline': '2026-03-15',
    'write_date': '2026-02-28 14:20:00'
}
```

---

## 🎓 Exemplos de Uso

### Exemplo 1: Buscar tarefas de um projeto

```python
from odoo_api_python_examples import OdooJSONRPCClient

client = OdooJSONRPCClient(
    url='http://localhost:8069',
    db='odoo',
    username='admin',
    password='admin'
)

tasks = client.get_tasks([['project_id', '=', 1]])
for task in tasks:
    print(f"{task['id']}: {task['name']}")
```

### Exemplo 2: Criar tarefa com subtarefas

```python
from odoo_api_python_examples import OdooXMLRPCClient

client = OdooXMLRPCClient(
    url='http://localhost:8069',
    db='odoo',
    username='admin',
    password='admin'
)

result = client.create_task_with_subtasks(
    parent_name='Desenvolver API',
    project_id=1,
    subtask_names=['Backend', 'Frontend', 'Testes', 'Deploy']
)

print(f"Criada tarefa {result['parent_id']} com {len(result['subtask_ids'])} subtarefas")
```

### Exemplo 3: Filtrar tarefas por usuário

```python
user = client.get_user_by_email('john@example.com')
my_tasks = client.get_tasks_by_user(user['id'])

print(f"Tarefas de {user['name']}: {len(my_tasks)}")
```

### Exemplo 4: Sincronização bidirecional

```python
from odoo_api_python_examples import OdooBidirectionalSync
from datetime import datetime, timedelta

client = OdooXMLRPCClient(...)
sync = OdooBidirectionalSync(client)

# Sync desde 1 hora atrás
last_sync = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

# Buscar mudanças do Odoo
changes = sync.sync_from_odoo(last_sync)
print(f"Mudanças do Odoo: {len(changes)}")

# Aplicar mudanças no Odoo
external_tasks = [...]  # Lista de tarefas do sistema externo
stats = sync.sync_to_odoo(external_tasks)
print(f"Criadas: {stats['created']}, Atualizadas: {stats['updated']}")
```

---

## 🔍 Troubleshooting

### Erro: Authentication failed
```python
# Verificar credenciais
# Verificar se banco de dados existe
# Verificar se usuário tem permissões
```

### Erro: Model not found
```python
# Verificar nome do modelo: 'project.task' (não 'task')
# Verificar se módulo está instalado (Project)
```

### Erro: Access Denied
```python
# Verificar access rights do usuário
# Verificar record rules
# Usuário precisa ser Project Manager ou superior
```

### Tarefa não aparece após criar
```python
# Verificar se active=True
# Verificar filtros na busca
# Verificar project_id correto
```

---

## 📞 Suporte e Recursos

### Documentação Oficial
- [Odoo External API](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)
- [Odoo ORM API](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)
- [Odoo Web Services](https://www.odoo.com/documentation/18.0/developer/howtos/web_services.html)

### Comunidade
- [Odoo Community Forum](https://www.odoo.com/forum)
- [OCA GitHub](https://github.com/OCA)
- [Stack Overflow - Odoo Tag](https://stackoverflow.com/questions/tagged/odoo)

### Ferramentas
- [Postman](https://www.postman.com/) - Testar APIs
- [Insomnia](https://insomnia.rest/) - Cliente REST/GraphQL
- [curl](https://curl.se/) - Testes via terminal

---

## ✅ Checklist Rápido

### Antes de Começar
- [ ] Odoo 18 instalado e rodando
- [ ] Banco de dados criado
- [ ] Módulo Project instalado
- [ ] Credenciais de administrador

### Implementação
- [ ] Ler `API_INTEGRATION_SUMMARY.md`
- [ ] Escolher abordagem (JSON-RPC recomendado)
- [ ] Configurar variáveis em `odoo_api_python_examples.py`
- [ ] Executar exemplos básicos
- [ ] Customizar para seu caso
- [ ] Implementar sync bidirecional
- [ ] Configurar logging
- [ ] Testar resolução de conflitos

### Produção
- [ ] Criar usuário técnico dedicado
- [ ] Armazenar credenciais em variáveis de ambiente
- [ ] Configurar cron job / serviço
- [ ] Implementar retry logic
- [ ] Configurar alertas de erro
- [ ] Documentar processo interno
- [ ] Fazer backup do mapeamento de IDs

---

## 📈 Próximos Passos

1. **Leia o resumo executivo**
   ```bash
   less docs/API_INTEGRATION_SUMMARY.md
   ```

2. **Execute os exemplos**
   ```bash
   python docs/odoo_api_python_examples.py
   ```

3. **Customize para seu caso**
   - Copie as classes necessárias
   - Adapte para seu sistema externo
   - Implemente lógica de negócio

4. **Implemente em produção**
   - Configure serviço/cron
   - Monitore logs
   - Ajuste conforme necessário

---

**Última atualização:** Fev 28, 2026  
**Versão Odoo:** 18.0  
**Autor:** Documentação Técnica API Odoo

---

## 📄 Licença

Esta documentação está disponível sob os mesmos termos do Odoo:
- Odoo 18 - LGPL-3.0
- Módulos OCA - AGPL-3.0

---

**Boa sorte com sua integração! 🚀**
