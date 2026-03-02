# Como Instalar e Usar a CLI odoo-sync Globalmente

O `odoo-task-sync` foi transformado em um pacote Python. Isso significa que você pode instalá-lo no seu sistema e usar o comando `odoo-sync` em **qualquer diretório** (projetos Laravel, React, etc).

## 1. Instalação Global

A melhor forma de instalar ferramentas CLI em Python é usando o `pipx` (para isolamento) ou o `pip` de usuário:

```bash
cd odoo-task-sync

# Usando pipx (Recomendado)
pipx install -e .

# OU usando pip tradicional
pip install --user -e .
```
*(Nota: O parâmetro `-e` significa "editable". Se você alterar o código da ferramenta, não precisa reinstalar!)*

## 2. Configuração (Credenciais)

Para não precisar digitar a senha do seu Odoo em todo projeto novo que você for, configure as credenciais globalmente:

```bash
mkdir -p ~/.config/odoo-sync
cp .env ~/.config/odoo-sync/.env
```
*(Lembre-se de preencher corretamente com `admin@amdlemos.com` e o ID dos agentes nesse `.env` global)*.

## 3. Uso no Dia a Dia (Em um novo Projeto)

Vá para a pasta de um projeto qualquer (ex: um frontend em React) no qual você vai trabalhar hoje:

```bash
cd ~/meus-projetos/app-react
```

### Inicialize a pasta:
```bash
odoo-sync init
```
*Isso criará a pasta local `data/tasks/` e o arquivo `.odoo-sync.env`*

### Configure o Projeto Específico
Abra o `.odoo-sync.env` recém-criado na pasta atual e coloque o ID do projeto no Odoo referente a esse App:
```env
DEFAULT_PROJECT_ID=5
```

### Comandos Diários
- **Baixar tarefas:** `odoo-sync pull`
- **Ver estágios:** `odoo-sync task stages`
- **Mover tarefa:** `odoo-sync task move --task 42 --stage 24`

### Criar / Atualizar Tarefas

- **Criar tarefa (dry-run):**
  `odoo-sync task create --name "Corrigir bug X" --desc "Reproduzir e corrigir" --project 5 --stage 12 -a 2 -a 3 --dry-run`
- **Criar tarefa (real):**
  `odoo-sync task create --name "Implementar feature Y" -p 5 -a 2 -a 3`

- **Atualizar tarefa (ex.: mudar nome/estágio):**
  `odoo-sync task update --task 42 --name "Novo nome" --stage 5`

- **Desvincular parent_id (remover parent):**
  `odoo-sync task update --task 42 --clear-parent`
  ou
  `odoo-sync task update --task 42 --parent none`

- **Substituir atribuídos (user_ids):**
  `odoo-sync task update --task 42 -a 2 -a 3`

- **Remover todos os atribuídos:**
  `odoo-sync task update --task 42 --clear-assign`

### Interação para IAs (Opencode, Claude, etc)
- **Ligar timer:** `odoo-sync timer start --task 42 --desc "Criando botão" --model "opencode"`
- **Desligar timer:** `odoo-sync timer stop --id 15`
