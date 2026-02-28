# Guia de Integração: Multi-Agentes Inteligentes no Odoo

Este documento descreve o fluxo de arquitetura e uso para a funcionalidade de "Controle de Tempos (Timesheets) para Múltiplos Agentes" no repositório `odoo-task-sync`.

## O Problema Original
O Odoo por padrão assume que uma conta de usuário/funcionário está trabalhando em apenas uma tarefa por vez. Tentar abrir um segundo cronômetro usando os wizards de interface resultará em erros (`UserError: Cannot know which one to stop`). 

Ao acionar múltiplos modelos de IA simultaneamente (Ex: rodando um script com GPT-4o e outro com Claude 3.5 Sonnet para automatizar tarefas da mesma conta), o sistema entraria em colapso. Além disso, se os agentes logassem o tempo na conta do humano principal, as horas totais do projeto seriam irreais, causando problemas de faturamento e gestão (um humano com "30 horas trabalhadas" no mesmo dia).

## A Solução: Pool de Trabalhadores (Agents Pool)
Criamos um sistema onde os Agentes de IA são cadastrados como `Employees` (Empregados) genéricos dentro do Odoo, e o humano responsável figura como `Manager` (Gerente) deles na hierarquia.

### Configuração
1. **No Odoo**: 
   - Criar funcionários: `Agente 1`, `Agente 2`, `Agente 3`.
   - No campo "Gerente" (`parent_id`) da ficha deles, selecione o seu usuário real (ex: `Alan Lemos`).
2. **No .env (`odoo-task-sync`)**:
   - Mapear os IDs numéricos destes agentes:
   ```env
   AI_AGENT_IDS=2,3,4
   ```

### Fluxo de Execução da API (`odoo_client.py`)
Quando o método `start_ai_task_timer` é chamado:
1. Ele acessa a tabela `account.analytic.line` para ver quais funcionários do Pool não possuem nenhum registro com `unit_amount = 0` (cronômetros abertos).
2. Ele aloca o primeiro agente livre.
3. Cria um log direto no banco, saltando a camada limitadora de UI (wizard) com a assinatura `[Agente 2 | GPT-4o]`.
4. Ao final da execução, chama a função `stop_ai_task_timer` que procura aquela linha específica e aciona o fechamento para salvar a duração real da execução do LLM em horas (`unit_amount`).

### Benefícios nos Relatórios (Dashboard)
Com a subordinação hierárquica ativada:
- A aba "Minhas Horas" do usuário Alan Lemos não sofrerá inflação e terá apenas o esforço mecânico humano puro.
- A aba "Horas da Minha Equipe" agrupará tudo que a IA produziu debaixo da liderança de Alan Lemos.
- Permite faturamento e separação de métricas exatas entre "Homem x Máquina".
