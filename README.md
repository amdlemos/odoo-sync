# 🔄 Odoo Task Sync - Sincronização Bidirecional com Agentes IA

Sistema de sincronização entre **Odoo 18** e arquivos **JSON locais**, permitindo que agentes de IA processem, analisem e sugiram melhorias em tarefas de projetos.

## 📋 Visão Geral

Este projeto resolve o desafio de:
- ✅ Baixar tarefas e subtarefas do Odoo para análise offline
- ✅ Permitir que múltiplos agentes de IA processem as tarefas
- ✅ Gerar sugestões automatizadas (priorização, subtarefas, descrições, etc.)
- ✅ Sincronizar mudanças aprovadas de volta para o Odoo
- ✅ Manter gerentes de projeto sempre atualizados

## 🏗️ Arquitetura

```
┌─────────────┐    sync     ┌──────────────┐
│             │◄───────────►│              │
│  ODOO 18    │             │  JSON Files  │
│  (VPS)      │             │  (Local)     │
│             │             │              │
└──────┬──────┘             └──────┬───────┘
       │ OdooRPC API                │ File I/O
       │                            │
┌──────▼────────────────────────────▼───────┐
│                                            │
│        SYNC ENGINE (Python)                │
│  • Download/Upload de tarefas             │
│  • Detecção de conflitos                  │
│  • Versionamento                           │
│                                            │
└───────────────────┬────────────────────────┘
                    │
┌───────────────────▼───────────────────────┐
│                                            │
│        AI AGENT INTERFACE                 │
│  • Claude, GPT-4, ou agentes customizados │
│  • Análise e sugestões                    │
│  • Aprovação interativa                   │
│                                            │
└────────────────────────────────────────────┘
```

## 🚀 Início Rápido

### 1. Instalação

```bash
# Clone ou copie o projeto
cd odoo-task-sync

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt
```

### 2. Configuração

Copie o arquivo de exemplo e configure:

```bash
cp .env.example .env
```

Edite `.env` com suas credenciais:

```env
# Odoo Configuration
ODOO_HOST=seu-odoo.com
ODOO_PORT=443
ODOO_PROTOCOL=jsonrpc+ssl
ODOO_DB=odoo
ODOO_USER=seu.email@exemplo.com
ODOO_PASSWORD=sua_senha

# AI API Keys (opcional)
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
```

### 3. Teste de Conexão

```bash
# Baixar suas tarefas
python scripts/sync_pull.py

# Visualizar resultado
cat data/tasks/user_*_all_tasks.json | jq .
```

## 📖 Uso Detalhado

### Baixar Tarefas (Pull)

```bash
# Todas as suas tarefas
python scripts/sync_pull.py

# Tarefas de um projeto específico
python scripts/sync_pull.py --project 1

# Tarefas de outro usuário (requer permissões)
python scripts/sync_pull.py --project 1 --user 2

# Incluir tarefas completadas
python scripts/sync_pull.py --include-completed
```

**Resultado**: Arquivo JSON em `data/tasks/`

### Processar com IA

#### Opção 1: Usando a Interface Python

```python
from pathlib import Path
from src.ai.agent_interface import AIAgentInterface

# Carregar tarefas
interface = AIAgentInterface(Path('data/tasks/project_1_tasks.json'))

# Obter resumo para IA
summary = interface.get_tasks_summary(format='markdown')
print(summary)

# Obter estatísticas
stats = interface.get_statistics()
print(f"Tarefas atrasadas: {stats['tasks_overdue']}")
print(f"Sem descrição: {stats['tasks_empty_description']}")

# Exportar para prompt de IA
prompt_data = interface.export_for_ai_prompt()
# Envie prompt_data para Claude, GPT-4, etc.
```

#### Opção 2: Usando Claude/GPT Diretamente

```python
import anthropic
from pathlib import Path
from src.ai.agent_interface import AIAgentInterface

# Preparar dados
interface = AIAgentInterface(Path('data/tasks/project_1_tasks.json'))
tasks_data = interface.export_for_ai_prompt()

# Enviar para Claude
client = anthropic.Anthropic(api_key="your-key")

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": f"""
        Analise estas tarefas e forneça sugestões para:
        1. Reorganizar prioridades
        2. Criar subtarefas necessárias
        3. Melhorar descrições vazias
        4. Identificar riscos de atraso
        
        {tasks_data}
        
        Retorne em formato JSON com estrutura:
        {{
          "suggestions": [
            {{
              "task_id": 42,
              "type": "update_priority",
              "changes": {{"priority": "2"}},
              "reasoning": "..."
            }}
          ]
        }}
        """
    }]
)

# Processar resposta
suggestions = extract_suggestions_from_ai(message.content)

# Salvar sugestões
interface.save_suggestions(suggestions, agent_name="claude-sonnet-4")
```

### Revisar e Aprovar Sugestões

```python
import json
from pathlib import Path

# Carregar sugestões
with open('data/ai_workspace/suggestions_20260228_120000.json') as f:
    data = json.load(f)

# Revisar e aprovar interativamente
approved_changes = []

for suggestion in data['suggestions']:
    print(f"\n{'='*60}")
    print(f"Tarefa: [{suggestion['task_id']}] {suggestion['task_name']}")
    print(f"Tipo: {suggestion['type']}")
    print(f"Sugestão: {suggestion['suggestion']}")
    print(f"Justificativa: {suggestion['reasoning']}")
    print(f"Confiança: {suggestion['confidence']*100:.0f}%")
    
    choice = input("\n[A]provar / [R]ejeitar / [E]ditar / [P]ular? ").lower()
    
    if choice == 'a':
        suggestion['approved'] = True
        suggestion['reviewed_by'] = 'Você'
        suggestion['reviewed_at'] = datetime.now().isoformat()
        approved_changes.append(suggestion)

# Salvar mudanças aprovadas
with open('data/ai_workspace/approved_changes.json', 'w') as f:
    json.dump({
        'metadata': {'total': len(approved_changes)},
        'changes': approved_changes
    }, f, indent=2)
```

### Enviar Mudanças para Odoo (Push)

```bash
# Aplicar mudanças aprovadas
python scripts/sync_push.py data/ai_workspace/approved_changes.json

# Apenas validar (dry-run)
python scripts/sync_push.py data/ai_workspace/approved_changes.json --dry-run
```

## 📁 Estrutura de Arquivos

```
odoo-task-sync/
├── config/                      # Configurações
├── data/
│   ├── tasks/                   # Tarefas sincronizadas
│   │   ├── project_1_tasks.json
│   │   └── user_2_all_tasks.json
│   ├── metadata/                # Metadados de sync
│   │   ├── sync_state.json
│   │   └── conflicts.json
│   └── ai_workspace/            # Área de trabalho IA
│       ├── suggestions.json
│       └── approved_changes.json
├── src/
│   ├── sync/
│   │   ├── odoo_client.py       # Cliente Odoo (OdooRPC)
│   │   └── sync_manager.py      # Gerenciador de sync
│   ├── ai/
│   │   └── agent_interface.py   # Interface para IAs
│   └── models/
│       └── task.py              # Modelos de dados
├── scripts/
│   ├── sync_pull.py             # Script: baixar tarefas
│   └── sync_push.py             # Script: enviar mudanças
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 Formato JSON das Tarefas

### Arquivo de Tarefas (`data/tasks/project_X_tasks.json`)

```json
{
  "metadata": {
    "project_id": 1,
    "project_name": "Projeto CMS - Odoo",
    "last_sync": "2026-02-28T15:30:00Z",
    "total_tasks": 15
  },
  "tasks": [
    {
      "id": 42,
      "name": "Implementar autenticação OAuth",
      "description": "<p>Implementar OAuth2...</p>",
      "description_plain": "Implementar OAuth2...",
      
      "project": {
        "id": 1,
        "name": "Projeto CMS - Odoo"
      },
      
      "hierarchy": {
        "parent_id": null,
        "child_ids": [43, 44],
        "child_count": 2,
        "is_subtask": false
      },
      
      "assignment": {
        "user_ids": [2, 3],
        "user_names": ["João Silva", "Maria Santos"]
      },
      
      "status": {
        "stage_id": 3,
        "stage_name": "Em Progresso",
        "priority": "1",
        "priority_label": "Alta"
      },
      
      "dates": {
        "date_deadline": "2026-03-15",
        "create_date": "2026-02-27T16:45:00Z",
        "write_date": "2026-02-28T14:00:00Z"
      },
      
      "time_tracking": {
        "planned_hours": 40.0,
        "effective_hours": 15.5,
        "remaining_hours": 24.5,
        "progress_percent": 38.75
      },
      
      "sync_metadata": {
        "last_sync_from_odoo": "2026-02-28T15:30:00Z",
        "odoo_write_date": "2026-02-28T14:00:00Z",
        "checksum": "abc123"
      }
    }
  ]
}
```

## 🤖 Exemplos de Sugestões de IA

### 1. Criar Subtarefa

```json
{
  "suggestion_id": "S001",
  "task_id": 42,
  "type": "create_subtask",
  "confidence": 0.95,
  "suggestion": {
    "action": "create",
    "parent_id": 42,
    "values": {
      "name": "Implementar testes unitários OAuth",
      "description": "Criar testes para cobrir fluxos OAuth2",
      "user_ids": [2],
      "planned_hours": 4.0
    }
  },
  "reasoning": "A tarefa principal não possui subtarefa para testes..."
}
```

### 2. Atualizar Prioridade

```json
{
  "suggestion_id": "S002",
  "task_id": 42,
  "type": "update_priority",
  "confidence": 0.87,
  "suggestion": {
    "action": "update",
    "task_id": 42,
    "changes": {"priority": "2"},
    "previous_values": {"priority": "1"}
  },
  "reasoning": "Tarefa atrasada (38% progresso, 60% do prazo expirado)"
}
```

### 3. Melhorar Descrição

```json
{
  "suggestion_id": "S003",
  "task_id": 43,
  "type": "update_description",
  "confidence": 0.72,
  "suggestion": {
    "action": "update",
    "task_id": 43,
    "changes": {
      "description": "<p><strong>Objetivos:</strong>...</p>"
    }
  },
  "reasoning": "Descrição vazia. Adicionando estrutura detalhada..."
}
```

## ⚙️ Configuração Avançada

### Filtros Personalizados

```python
from src.sync.odoo_client import OdooClient

client = OdooClient(...)

# Tarefas urgentes e atrasadas
urgent_overdue = client.get_tasks(
    domain=[
        '&',
        ('priority', '=', '2'),
        ('date_deadline', '<', '2026-02-28')
    ]
)

# Tarefas sem responsável em projetos ativos
unassigned = client.get_tasks(
    domain=[
        '&',
        ('user_ids', '=', False),
        ('project_id.active', '=', True)
    ]
)

# Busca por texto
api_tasks = client.search_tasks('API', project_id=1)
```

### Detecção de Conflitos

O sistema detecta automaticamente quando:
- Uma tarefa foi modificada no Odoo após o último sync
- Mudanças locais conflitam com mudanças no servidor

```json
{
  "conflicts": [
    {
      "task_id": 42,
      "local_version": {
        "write_date": "2026-02-28T16:00:00Z",
        "changes": {"priority": "2"}
      },
      "odoo_version": {
        "write_date": "2026-02-28T16:15:00Z",
        "changes": {"stage_id": 4}
      },
      "resolution_options": [
        "keep_odoo",
        "keep_local",
        "merge"
      ]
    }
  ]
}
```

## 🛠️ Desenvolvimento

### Executar Testes

```bash
pytest tests/
```

### Logging

Logs são salvos em `logs/`:
- `sync_pull.log` - Logs de download
- `sync_push.log` - Logs de upload
- `odoo_sync.log` - Logs gerais

### Contribuir

1. Fork o projeto
2. Crie uma branch para sua feature
3. Faça commit das mudanças
4. Push para a branch
5. Abra um Pull Request

## 📚 Recursos Adicionais

### Documentação Odoo
- [Odoo 18 External API](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)
- [OdooRPC Documentation](https://github.com/OCA/odoorpc)

### IAs Suportadas
- **Claude (Anthropic)**: Melhor para análise contextual e raciocínio
- **GPT-4 (OpenAI)**: Excelente para geração de conteúdo
- **Agentes customizados**: Use a AIAgentInterface para integrar qualquer IA

## ❓ FAQ

**P: Preciso instalar algo no Odoo?**  
R: Não! O sistema usa apenas a API externa do Odoo.

**P: Os dados ficam seguros?**  
R: Sim! Os arquivos JSON ficam apenas na sua máquina local. Use `.gitignore` para não commitar dados sensíveis.

**P: Posso usar sem IA?**  
R: Sim! Use apenas os scripts de sync para ter backup local das tarefas em JSON.

**P: Funciona com Odoo Community Edition?**  
R: Sim! Funciona com Community e Enterprise.

**P: Como atualizar para nova versão do Odoo?**  
R: Atualize o `odoorpc` e teste a compatibilidade.

## 📄 Licença

MIT License - Sinta-se livre para usar e modificar.

## 🙏 Créditos

- **OdooRPC**: https://github.com/OCA/odoorpc
- **Odoo Community Association (OCA)**: https://odoo-community.org/

---

**Desenvolvido com ❤️ para integração Odoo + IA**

Para dúvidas ou sugestões, abra uma issue!
### Gestão de Timesheet com Agentes (Multi-Agent)

O sistema suporta múltiplos agentes trabalhando simultaneamente nas tarefas sem haver colapso ou sobreposição de horas. Para utilizar:

1. Crie os agentes no Odoo como Empregados (Employees).
2. Configure o seu usuário como Gerente (`Manager`) de cada agente para que as horas caiam nos seus relatórios.
3. Obtenha os IDs numéricos dos Agentes no Odoo (ex: 2, 3, 4).
4. Configure no seu arquivo `.env`:

```env
# AI Agent Configuration
AI_AGENT_IDS=2,3,4
```

Quando um agente precisar iniciar um trabalho, o sistema procurará automaticamente qual agente está livre e atrelará a linha de Timesheet (Timer) a esse agente livre.

```python
# Iniciar trabalho
res = client.start_ai_task_timer(
    task_id=5, 
    description="Implementando testes de API", 
    llm_model="claude-3.5-sonnet"
)
print(f"Agente alocado: {res['agent_name']} | Timer ID: {res['timer_id']}")

# O agente faz o seu processamento...

# Parar o tempo
client.stop_ai_task_timer(res['timer_id'])
```
