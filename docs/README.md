# 📚 Documentação Técnica - odoo-sync

Índice completo da documentação técnica do projeto.

---

## 📖 Documentação Principal

Para informações de uso geral, consulte o **[README.md](../README.md)** na raiz do projeto.

---

## 📁 Estrutura da Documentação

### 🎯 Especificações
- **[task-html-spec.md](task-html-spec.md)** - Especificação canônica de HTML para descrições de tarefas

### 🏗️ Arquitetura
- **[architecture/multi-agent-timesheets.md](architecture/multi-agent-timesheets.md)** - Arquitetura de timesheets para múltiplos agentes IA
  - Pool de agentes
  - Alocação automática
  - Controle de concorrência

### 🔌 API Reference
- **[api-reference/README.md](api-reference/README.md)** - Índice de documentação de API
- **[api-reference/api-comparison.md](api-reference/api-comparison.md)** - Comparação de APIs Odoo (XML-RPC, JSON-RPC, REST, GraphQL)
- **[api-reference/integration-guide.md](api-reference/integration-guide.md)** - Guia completo de integração com API Odoo 18
- **[api-reference/examples.py](api-reference/examples.py)** - Exemplos executáveis em Python

---

## 🚀 Início Rápido

### Para Desenvolvedores
1. Leia o [README.md](../README.md) principal
2. Configure o ambiente seguindo as instruções de instalação
3. Consulte [task-html-spec.md](task-html-spec.md) para formato de descrições

### Para Arquitetos de Software
1. Entenda a arquitetura em [architecture/multi-agent-timesheets.md](architecture/multi-agent-timesheets.md)
2. Veja comparação de APIs em [api-reference/api-comparison.md](api-reference/api-comparison.md)
3. Consulte guia completo em [api-reference/integration-guide.md](api-reference/integration-guide.md)

### Para Integradores de API
1. Comece com [api-reference/README.md](api-reference/README.md)
2. Leia [api-reference/api-comparison.md](api-reference/api-comparison.md) para escolher abordagem
3. Execute exemplos em [api-reference/examples.py](api-reference/examples.py)
4. Consulte [api-reference/integration-guide.md](api-reference/integration-guide.md) para detalhes

---

## 📝 Notas

- Toda documentação assume **Odoo 18+**
- **Idioma obrigatório**: Português (pt-BR) para tarefas e comunicação
- Arquitetura **stateless**: Odoo é a única fonte de verdade

---

**Última atualização:** Mar 02, 2026
