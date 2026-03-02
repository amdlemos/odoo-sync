# Spec: HTML para descrições de tarefas do Odoo

Objetivo
- Garantir que descrições criadas/atualizadas via `odoo-sync` renderizem previsivelmente no Odoo: headings, listas, checklist visual e blocos de código legíveis.
- Fornecer um template canônico e regras mínimas para evitar resultados inconsistentes quando o HTML for sanitizado pelo Odoo.

Local recomendado
- `docs/odoo/task-html-spec.md`

Tags permitidas (recomendado)
- Estrutura: `h1, h2, h3, p, ul, ol, li, pre, code, strong, em, a, blockquote`
- Evitar / bloqueadas: `script, style, iframe, form, button, input` (o Odoo pode sanitizar ou remover; usamos checkboxes visuais apenas como elementos estáticos no template).

Template canônico (usar sempre que possível)
- Este é o template padrão para tarefas de especificação que serão enviadas em `--desc` pelo `odoo-sync`.

HTML exato de exemplo

<h3>Contexto</h3>
<p>Breve descrição do que o endpoint/feature faz — objetivo sucinto e por que existe.</p>

<h3>Regras de Negócio</h3>
<ul>
  <li>Regra 1: (ex.: apenas administradores podem...)</li>
  <li>Regra 2: (ex.: campo X é obrigatório)</li>
</ul>

<h3>Critérios de Aceitação</h3>
<ul class="o_checklist">
  <li><label><input type="checkbox" disabled> Model criado com migration</label></li>
  <li><label><input type="checkbox" disabled> Data class (spatie/laravel-data) com rules</label></li>
  <li><label><input type="checkbox" disabled> Controller/rota implementada</label></li>
  <li><label><input type="checkbox" disabled> Tests de integração/feature</label></li>
</ul>

<h3>Request/Response Exemplo</h3>
<pre><code>{
  "method": "POST",
  "path": "/api/example",
  "body": {
    "field": "value"
  }
}

→ 201 Created
{
  "id": 1,
  "field": "value"
}
</code></pre>

Boas práticas para enviar via `odoo-sync`
- Gere o HTML localmente num arquivo (por exemplo `docs/odoo/task-<id>.html`) e envie com:

```
odoo-sync task update -t <ID> --desc "$(cat docs/odoo/task-<id>.html)"
```

- Isso evita problemas com escape de aspas no shell e faz com que o conteúdo seja exatamente o que o Odoo receberá.
- Use UTF-8 e evite caracteres de controle; mantenha o tamanho da descrição razoável (ex.: < 64 KB).
- Sempre rode `odoo-sync pull --project 2` após mudanças para atualizar `data/tasks/project_2_tasks.json`.

Recomendações para `.odoo-agent-rules.md` (opcionais, mas úteis)
1. Exigir template: alterações de `description` devem seguir o template canônico; se diferente, adicionar justificativa curta no corpo da tarefa ou comentário.
2. Sanitização: validar localmente (script simples) que o HTML usa apenas tags permitidas antes de enviar.
3. Checklists: documentar que os `input type="checkbox" disabled` são apenas visuais — para checklists rastreáveis, criar subtasks.
4. Limite de tamanho: impedir descrições excessivamente grandes; recommendar 64 KB.
5. Processo de promoção: antes de mover para `Especificações` (stage 10) verificar:
   - `description` atualizada com o template
   - pelo menos 1 critério de aceitação verificável
   - branch/issue associada (opcional)

Verificações pós-envio
- Abrir a tarefa no Odoo UI e confirmar:
  - headings aparecem (h3/h2 conforme o template)
  - a lista com `class="o_checklist"` exibe os itens com checkboxes desabilitados
  - blocos `pre/code` mantém a formatação
- Se algum item quebrar, não remover o arquivo HTML local; ajuste o template e reenvie usando o mesmo arquivo para facilitar troubleshooting.

Notas finais
- Este arquivo é a fonte de verdade para criar/atualizar descrições no Odoo via `odoo-sync`.
- Se quiser, posso também adicionar um pequeno script de validação (PHP/Node/Python) que checa tags permitidas e tamanho antes de enviar.
