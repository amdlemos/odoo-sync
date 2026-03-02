# 🔄 Odoo Task Sync - CLI Stateless para Agentes IA

Ferramenta CLI para gerenciar tarefas do **Odoo 18** diretamente via RPC, permitindo que agentes de IA trabalhem de forma autônoma com timesheets, movimentação de tarefas e criação/atualização de conteúdo.

## 📋 Visão Geral

Sistema **stateless** (sem persistência local) que conecta diretamente ao Odoo para:
- ✅ Consultar tarefas ao vivo (sem cache local JSON)
- ✅ Gerenciar timesheets automáticos para múltiplos agentes de IA
- ✅ Mover tarefas entre estágios
- ✅ Criar/atualizar/deletar tarefas via CLI
- ✅ Suporte a hierarquia de tarefas (parent/children)
- ✅ Cache em memória (5min TTL) para performance
- ✅ Idioma: **Português (pt-BR)** obrigatório

## 🏗️ Arquitetura

```
┌─────────────┐
│             │
│  ODOO 18    │◄────── Único Source of Truth
│  (VPS)      │
│             │
└──────┬──────┘
       │ OdooRPC API (stateless)
       │
┌──────▼────────────────────┐
│                            │
│   odoo-sync CLI            │
│   • Cache em memória 5min  │
│   • Timers multi-agente    │
│   • CRUD de tarefas        │
│                            │
└───────────────┬────────────┘
                │
┌───────────────▼───────────────┐
│                                │
│      AI AGENTS                │
│  • Claude, GPT-4, etc.        │
│  • Leem tarefas via CLI       │
│  • Gerenciam timers           │
│  • Movem estágios             │
│                                │
└────────────────────────────────┘
```

## 🚀 Instalação

### Via pip (Recomendado)

```bash
pip install odoo-task-sync
```

### Via pipx (Isolado)

```bash
pipx install odoo-task-sync
```

### Desenvolvimento

```bash
# Clone o projeto
cd odoo-sync

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows

# Instale em modo de desenvolvimento
pip install -e .
```

## ⚙️ Configuração

### 1. Configuração Global (~/.config/odoo-sync/.env)

Crie o diretório e arquivo:

```bash
mkdir -p ~/.config/odoo-sync
cat > ~/.config/odoo-sync/.env << 'EOF'
# Credenciais Odoo (global)
ODOO_HOST=seu-odoo.com
ODOO_PORT=443
ODOO_PROTOCOL=jsonrpc+ssl
ODOO_DB=odoo
ODOO_USER=seu.email@exemplo.com
ODOO_PASSWORD=sua_senha

# Pool de Agentes de IA (IDs de hr.employee)
AI_AGENT_IDS=2,3,4
EOF
```

### 2. Configuração por Projeto (Opcional)

Em qualquer projeto que use `odoo-sync`:

```bash
# Inicializar projeto local
odoo-sync init
```

Isso cria:
- `.odoo-sync.env` — config local (sobrescreve global)
- `.odoo-agent-rules/main.md` — regras do agente (copiado de AI_SYSTEM_PROMPT.md)
- `.odoo-agent-rules/specs.md` — especificação HTML para descrições
- `data/tasks/` — diretório vazio (não mais usado, pode ser ignorado)

Edite `.odoo-sync.env` para definir projeto padrão:

```env
# ID do projeto padrão deste repositório
DEFAULT_PROJECT_ID=5

# (Opcional) Sobrescrever credenciais globais
# ODOO_HOST=outro-odoo.com
# AI_AGENT_IDS=5,6
```

## 📖 Comandos Principais

### Consulta de Tarefas (Stateless)

```bash
# Ver detalhes completos de uma tarefa
odoo-sync task show --task 123
odoo-sync task show --task 123 --json  # Saída em JSON

# Listar tarefas de um projeto
odoo-sync task list --project 5

# Listar com filtros
odoo-sync task list --project 5 --stage 10 --limit 20
odoo-sync task list --user 2  # Tarefas atribuídas ao usuário ID 2

# Ver subtarefas
odoo-sync task children --task 100

# Listar estágios disponíveis
odoo-sync task stages
odoo-sync task stages --project 5
```

### Timers (Timesheets)

```bash
# Iniciar cronômetro (automático: busca tarefa + move para "Desenvolvimento" + cria timesheet)
odoo-sync timer start --task 123 --desc "Implementar endpoint de autenticação" --model "claude-sonnet"
# Saída:
# ✓ Cronômetro iniciado!
# Timer ID: 456
# Agente alocado: AI Agent 1

# Parar cronômetro
odoo-sync timer stop --id 456
```

**O que acontece ao iniciar timer:**
1. Busca a tarefa no Odoo (valida que existe)
2. Tenta mover para estágio "Desenvolvimento" (busca por keywords: desenvolv, development, dev)
3. Aloca um agente disponível do pool `AI_AGENT_IDS`
4. Cria timesheet (`account.analytic.line`) com `unit_amount=0` (timer aberto)
5. Retorna `timer_id` para você parar depois

### Gerenciamento de Tarefas

```bash
# Criar tarefa
odoo-sync task create --name "Implementar login OAuth" --desc "Descrição em Português" -p 5 -a 2

# Atualizar tarefa
odoo-sync task update --task 123 --name "Novo nome"
odoo-sync task update --task 123 --stage 15
odoo-sync task update --task 123 --desc "$(cat docs/task-123.html)"  # Enviar HTML de arquivo

# Mover tarefa de estágio
odoo-sync task move --task 123 --stage 20

# Deletar tarefa
odoo-sync task delete --task 123
odoo-sync task delete --task 123 --yes  # Sem confirmação
```

**Criar múltiplas tarefas:** Para criar um lote de tarefas, chame `task create` múltiplas vezes:

```bash
# Exemplo: criar 3 tarefas
odoo-sync task create --name "Tarefa 1" -p 5
odoo-sync task create --name "Tarefa 2" -p 5
odoo-sync task create --name "Tarefa 3" -p 5
```

### Utilitários

```bash
# Atualizar regras do agente (.odoo-agent-rules/) a partir do pacote
odoo-sync update --rules
odoo-sync update --rules --yes  # Sobrescrever sem perguntar

# Ver documentação de regras HTML
odoo-sync doc rules
```

## 🤖 Workflow para Agentes de IA

### 1. Contexto vem da tarefa

Quando um agente recebe um `task_id`, ele deve primeiro buscar o contexto:

```bash
odoo-sync task show --task 123
```

Isso retorna:
- Nome e descrição completa (HTML com contexto do que fazer)
- Estágio atual
- Projeto
- Prazo, horas, atribuições, parent/children

### 2. Iniciar Timer

Antes de qualquer trabalho:

```bash
odoo-sync timer start --task 123 --desc "Implementar endpoint de login" --model "claude"
# Guarde o Timer ID retornado!
```

### 3. Executar Trabalho

Fazer edições de código, testes, commits, etc.

### 4. Parar Timer

Ao terminar:

```bash
odoo-sync timer stop --id <TIMER_ID>
```

### 5. Mover Estágio (se concluído)

Se a tarefa está 100% pronta:

```bash
odoo-sync task stages  # Ver estágios
odoo-sync task move --task 123 --stage 20  # Mover para "Concluído"
```

## 📝 Formato de Descrições (HTML)

Ao criar/atualizar descrições, use o template canônico:

```html
<h3>Contexto</h3>
<p>Breve descrição do que a feature faz.</p>

<h3>Regras de Negócio</h3>
<ul>
  <li>Regra 1: apenas administradores podem...</li>
  <li>Regra 2: campo X é obrigatório</li>
</ul>

<h3>Critérios de Aceitação</h3>
<ul class="o_checklist">
  <li><label><input type="checkbox" disabled> Model criado com migration</label></li>
  <li><label><input type="checkbox" disabled> Testes implementados</label></li>
</ul>

<h3>Request/Response Exemplo</h3>
<pre><code>{
  "method": "POST",
  "path": "/api/login"
}
</code></pre>
```

**Tags permitidas:** `h1, h2, h3, p, ul, ol, li, pre, code, strong, em, a, blockquote`

**Tags proibidas:** `script, style, iframe, form` (checkboxes apenas visuais em checklists)

**Limite:** < 64 KB

**Enviando descrições longas:**
```bash
# Criar HTML local primeiro
odoo-sync task update --task 123 --desc "$(cat docs/task-123.html)"
```

Ver especificação completa:
```bash
odoo-sync doc rules
```

## 🔧 Configuração Avançada

### Pool de Agentes de IA

Configure IDs de funcionários (`hr.employee`) que representam agentes:

```env
# Global: ~/.config/odoo-sync/.env
AI_AGENT_IDS=2,3,4

# Ou sobrescrever por projeto: .odoo-sync.env
AI_AGENT_IDS=5,6,7
```

Quando `timer start` é executado, o sistema:
1. Busca agentes livres (sem timers abertos `unit_amount=0`)
2. Aloca o primeiro disponível
3. Retorna erro se todos estiverem ocupados

### Precedência de Configuração

```
1. Projeto local (.odoo-sync.env)
2. Global (~/.config/odoo-sync/.env)
3. Fallback (source .env no repo, apenas dev)
```

### Cache em Memória

O `OdooClient` mantém cache de 5 minutos para:
- Tarefas consultadas via `get_task_by_id()`
- Cache é invalidado automaticamente após `update_task()` ou `delete_task()`
- Cache é descartado quando o comando CLI termina

Desabilitar cache em uma chamada específica:
```python
client.get_task_by_id(123, use_cache=False)
```

## 🛠️ Desenvolvimento

### Estrutura do Projeto

```
odoo-sync/
├── src/
│   ├── cli/
│   │   ├── main.py         # CLI principal (comandos)
│   │   └── importer.py     # Importador JSON
│   └── sync/
│       └── odoo_client.py  # Cliente RPC + cache
├── docs/
│   └── task-html-spec.md   # Spec de HTML
├── AI_SYSTEM_PROMPT.md     # Regras do agente (source)
├── pyproject.toml          # Packaging
└── README.md               # Este arquivo
```

### Rodar Testes

```bash
pytest tests/
```

### Contribuindo

1. Fork o projeto
2. Crie branch para feature (`git checkout -b feature/nova-feature`)
3. Commit mudanças (`git commit -m 'feat: adiciona nova feature'`)
4. Push para branch (`git push origin feature/nova-feature`)
5. Abra Pull Request

## 📚 Documentação Adicional

- **AI_SYSTEM_PROMPT.md** — Regras completas para agentes de IA
- **docs/task-html-spec.md** — Especificação canônica de HTML para descrições
- **.odoo-agent-rules/** — Gerado por `odoo-sync init`, regras locais do projeto

## ❓ FAQ

### Por que stateless? E os arquivos JSON?

Anteriormente, `odoo-sync` baixava tarefas para `data/tasks/*.json` localmente. Essa abordagem foi **removida** porque:
- Agentes precisam conectar ao Odoo de qualquer forma (timers, stage moves)
- Odoo RPC é rápido o suficiente para queries individuais
- Elimina problemas de sincronização e conflitos
- Reduz ~70% do código

Agora: **Odoo é a única fonte de verdade**. Queries vão direto ao servidor.

### Como funciona o cache?

Cache em memória (Python dict) com TTL de 5 minutos, apenas durante execução do comando:
- 1ª chamada `get_task_by_id(123)` → busca do Odoo, cacheia
- 2ª chamada `get_task_by_id(123)` → retorna do cache (se < 5min)
- Comando termina → cache descartado

Invalidação automática após `update_task()` ou `delete_task()`.

### Múltiplos agentes podem rodar simultaneamente?

Sim! Cada agente:
1. Conecta ao Odoo independentemente
2. Usa `timer start` para alocar um employee do pool
3. Se todos agentes estão ocupados, retorna erro

### Como adicionar novos agentes?

No Odoo:
1. Criar funcionário (`hr.employee`) com nome "AI Agent X"
2. Anotar o ID do funcionário
3. Adicionar ID em `AI_AGENT_IDS=2,3,4,5`

### Posso usar em projetos não-Odoo?

Não. `odoo-sync` é específico para Odoo 18+ via OdooRPC. Para outros sistemas, adapte o `odoo_client.py`.

## 📄 Licença

MIT

## 👤 Autor

**Alan Lemos**  
Email: amdlemos@gmail.com

---

**Versão:** 0.1.0 (Stateless)  
**Última atualização:** 2026-03-01
