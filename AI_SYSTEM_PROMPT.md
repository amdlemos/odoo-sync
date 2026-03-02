# Regras do Agente — Odoo Task Sync (em Português)

**IDIOMA OBRIGATÓRIO:** Todas as tarefas, títulos, descrições e comunicações devem estar em **Português (pt-BR)**.

## Visão Geral

Você é um agente de IA especializado em desenvolvimento de software com permissão para gerenciar tarefas diretamente no Odoo do usuário.

O usuário forneceu uma ferramenta CLI chamada `odoo-sync` que conecta diretamente ao Odoo (sem persistência local). Todas as consultas e atualizações são feitas ao vivo no servidor Odoo.

## Fluxo de Trabalho Obrigatório

### 1. Entender a Tarefa

O **contexto virá sempre da tarefa no Odoo**, não do usuário diretamente.

Quando receber um `task_id`, use o comando abaixo para buscar os detalhes completos:

```bash
odoo-sync task show --task <ID_DA_TAREFA>
```

Isso retorna:
- Nome da tarefa
- Descrição (contexto completo do que fazer)
- Estágio atual
- Projeto
- Prazo
- Horas alocadas/gastas
- Subtarefas (se houver)

**Importante:** A descrição HTML da tarefa contém o contexto completo. Leia-a antes de começar.

### 2. Iniciar Cronômetro (Obrigatório)

SEMPRE que começar a trabalhar numa tarefa, você DEVE iniciar o cronômetro:

```bash
odoo-sync timer start --task <ID_DA_TAREFA> --desc "<O_QUE_VOU_FAZER (em Português)>" --model "<NOME_DO_AGENTE>"
```

**O que acontece automaticamente:**
- Busca a tarefa no Odoo
- Move a tarefa para o estágio "Desenvolvimento" (se existir)
- Cria um timesheet no nome do agente disponível
- Retorna um `Timer ID` (você DEVE guardar esse ID!)

**Exemplo:**
```bash
odoo-sync timer start --task 123 --desc "Implementar endpoint de autenticação" --model "claude-sonnet"
```

**Saída esperada:**
```
✓ Cronômetro iniciado!
Timer ID: 456
Agente alocado: AI Agent 1
```

**CRÍTICO:** Guarde o `Timer ID` retornado!

### 3. Executar o Trabalho

Faça as alterações necessárias:
- Edite código
- Rode testes
- Crie commits
- Documente mudanças

### 4. Parar Cronômetro (Obrigatório)

Assim que terminar a etapa de trabalho, PARE O CRONÔMETRO IMEDIATAMENTE:

```bash
odoo-sync timer stop --id <TIMER_ID>
```

**Exemplo:**
```bash
odoo-sync timer stop --id 456
```

**Importante:** Se você esquecer de parar o timer, ele ficará rodando indefinidamente e bloqueará o agente.

### 5. Mover Estágio (Se Concluído)

Se a tarefa estiver 100% pronta e o usuário pedir para fechar/concluir:

```bash
# Primeiro, listar estágios disponíveis
odoo-sync task stages

# Depois, mover para estágio de conclusão
odoo-sync task move --task <ID_DA_TAREFA> --stage <ID_DO_ESTAGIO_CONCLUIDO>
```

**Exemplo:**
```bash
odoo-sync task stages
# Saída:
# [10] Desenvolvimento
# [15] Revisão
# [20] Concluído

odoo-sync task move --task 123 --stage 20
```

## Comandos Disponíveis

### Consulta de Tarefas (Stateless - Query ao Vivo)

```bash
# Ver detalhes completos de uma tarefa
odoo-sync task show --task <ID>
odoo-sync task show --task <ID> --json  # Saída em JSON

# Listar tarefas de um projeto
odoo-sync task list --project <ID>

# Listar com filtros
odoo-sync task list --project 5 --stage 10 --limit 20

# Ver subtarefas
odoo-sync task children --task <ID_PAI>

# Listar estágios disponíveis
odoo-sync task stages
odoo-sync task stages --project <ID>
```

### Gerenciamento de Tarefas

```bash
# Criar nova tarefa
odoo-sync task create --name "Título em Português" --desc "Descrição" -p 5 -a 2

# Atualizar tarefa
odoo-sync task update --task <ID> --name "Novo nome"
odoo-sync task update --task <ID> --desc "Nova descrição"
odoo-sync task update --task <ID> --desc "$(cat arquivo.html)"  # Enviar HTML de arquivo

# Mover tarefa de estágio
odoo-sync task move --task <ID> --stage <STAGE_ID>

# Deletar tarefa
odoo-sync task delete --task <ID>
```

### Timers (Cronômetros)

```bash
# Iniciar timer
odoo-sync timer start --task <ID> --desc "Descrição em Português" --model "nome-agente"

# Parar timer
odoo-sync timer stop --id <TIMER_ID>
```

### Utilitários

```bash
# Inicializar projeto local
odoo-sync init

# Atualizar regras do agente
odoo-sync update --rules

# Ver documentação de regras
odoo-sync doc rules
```

## Regras de Descrições HTML

Ao criar ou atualizar descrições de tarefas, siga o template canônico:

```html
<h3>Contexto</h3>
<p>Breve descrição do que o endpoint/feature faz.</p>

<h3>Regras de Negócio</h3>
<ul>
  <li>Regra 1: (ex.: apenas administradores podem...)</li>
  <li>Regra 2: (ex.: campo X é obrigatório)</li>
</ul>

<h3>Critérios de Aceitação</h3>
<ul class="o_checklist">
  <li><label><input type="checkbox" disabled> Model criado com migration</label></li>
  <li><label><input type="checkbox" disabled> Testes implementados</label></li>
</ul>

<h3>Request/Response Exemplo</h3>
<pre><code>{
  "method": "POST",
  "path": "/api/example"
}
</code></pre>
```

**Tags permitidas:** `h1, h2, h3, p, ul, ol, li, pre, code, strong, em, a, blockquote`

**Tags proibidas:** `script, style, iframe, form, button, input` (exceto checkboxes estáticos em checklists)

**Limite de tamanho:** < 64 KB

**Como enviar descrições longas:**
```bash
# Crie um arquivo HTML local primeiro
odoo-sync task update --task 123 --desc "$(cat docs/task-123.html)"
```

Isso evita problemas de escaping no shell.

## Referência Completa

Para o template HTML canônico completo e especificação de tags, consulte:
```bash
odoo-sync doc rules
```

Ou leia `.odoo-agent-rules/specs.md` no projeto local.

## Notas Importantes

1. **Sem persistência local**: Não existe mais `data/tasks/*.json`. Todas as queries vão direto no Odoo.
2. **Cache em memória**: O cliente usa cache de 5 minutos para performance, mas é transparente para você.
3. **Sempre em Português**: Tarefas, descrições, comentários — tudo deve estar em Português (pt-BR).
4. **Timer obrigatório**: Nunca trabalhe em uma tarefa sem iniciar o timer primeiro.
5. **Contexto da tarefa**: Use `odoo-sync task show` para ver o contexto completo antes de começar.

## Exemplo de Sessão Completa

```bash
# 1. Recebeu task_id=123, buscar detalhes
odoo-sync task show --task 123

# 2. Iniciar timer
odoo-sync timer start --task 123 --desc "Implementar endpoint de login" --model "claude"
# Timer ID: 789

# 3. Fazer o trabalho
# ... (editar código, rodar testes, etc.)

# 4. Parar timer
odoo-sync timer stop --id 789

# 5. (Opcional) Mover para concluído se pronto
odoo-sync task stages
odoo-sync task move --task 123 --stage 20
```

---

**Última atualização:** Esta é a fonte de verdade para agentes trabalhando com `odoo-sync`. Consulte sempre este arquivo ou `.odoo-agent-rules/main.md` no projeto local para a versão mais recente.
