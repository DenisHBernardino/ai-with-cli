# 🍕 IA com CLI e MCP: por que ela acerta mais

🇺🇸 [English](README.md) | 🇧🇷 Português

Um experimento simples para mostrar uma ideia:

> **Uma IA sem acesso aos dados inventa. Com um CLI ou um MCP para consultar, ela acerta.**

Aqui, a IA atende a **Nona Byte Pizza**, uma pizzaria fictícia.
Ela não tem como "saber" o cardápio.
Então fazemos as mesmas perguntas em 3 cenários:

- **Sem ferramenta:** a IA só tem a própria memória.
- **Com CLI:** a IA roda o comando `pizza` no terminal.
- **Com MCP:** a IA recebe "botões" prontos de um servidor MCP.

E comparamos acertos e custo.

> ℹ️ O código, os comandos e as perguntas estão em inglês. A explicação está em português.

---

## 🧠 CLI ou MCP? Pensa numa pizzaria

![CLI é pedir no balcão, MCP é o app de delivery](docs/cli-vs-mcp.svg)

**CLI é pedir no balcão.**
Você fala direto: "uma Margherita grande".
É rápido e barato. Mas você precisa estar lá e saber pedir.

**MCP é o app de delivery.**
Tem botões, login e pagamento. Qualquer um usa, de qualquer lugar.
Mas o app carrega o cardápio inteiro toda vez que abre.

Na IA, esse "cardápio" são as descrições das ferramentas.
Elas vão junto em **toda** pergunta e custam tokens.

---

## 🧭 Qual eu uso?

```mermaid
flowchart TD
    A[A IA precisa de dados reais] --> B{Ela tem um terminal?}
    B -- Não, é um app de chat --> MCP[🔌 Use MCP]
    B -- Sim --> C{Já existe um CLI bom?<br/>git, docker, gh, aws...}
    C -- Sim --> CLI[🖥️ Use CLI]
    C -- Não --> D{Muitas ferramentas, pessoas<br/>não-devs ou precisa de login?}
    D -- Sim --> MCP
    D -- Não --> CLI2[🖥️ Crie um CLI simples]
```

| Situação | Melhor escolha |
|---|---|
| Agente de código no seu projeto | 🖥️ CLI |
| Ferramenta que já tem CLI (git, docker, gh, aws) | 🖥️ CLI |
| Quer gastar poucos tokens | 🖥️ CLI |
| App de chat, sem terminal | 🔌 MCP |
| Muitas ferramentas ou APIs | 🔌 MCP |
| Time com pessoas que não programam | 🔌 MCP |
| Precisa de login, permissões e auditoria | 🔌 MCP |

**Não é guerra.** Muitos projetos usam os dois.

---

## 📁 Estrutura

| Arquivo | O que faz |
|---|---|
| `pizza.py` | O CLI. Lê o cardápio e responde comandos. |
| `mcp_server.py` | O servidor MCP. Mesmos dados, entregues como ferramentas. |
| `data.json` | O cardápio (a "base de dados"). |
| `questions.json` | As perguntas do teste e as respostas certas. |
| `experiment.py` | Faz as perguntas nos 3 modos e mostra o placar. |
| `docs/cli-vs-mcp.svg` | O infográfico acima. |

---

## 🚀 Passo a passo

### 1. Clone e instale

```bash
git clone https://github.com/DenisHBernardino/ai-with-cli.git
cd ai-with-cli
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Precisa de Python 3.10 ou mais novo.

### 2. Brinque com o CLI você mesmo

Antes da IA, teste você. É isso que ela vai usar.

```bash
python pizza.py --help
python pizza.py menu
python pizza.py menu --vegetarian
python pizza.py search mushroom
python pizza.py price four cheese --size L
python pizza.py price pepperoni --json
```

### 3. Coloque sua chave da API

Pegue uma chave em [console.anthropic.com](https://console.anthropic.com).

```bash
export ANTHROPIC_API_KEY="sua-chave"          # Mac/Linux
$env:ANTHROPIC_API_KEY="sua-chave"            # Windows (PowerShell)
```

### 4. Rode o experimento

```bash
python experiment.py
```

O servidor MCP liga sozinho. Você vai ver a IA trabalhando:

```
❓ 1. How much is a large Margherita?
  ❌ [no tools] I don't have access to the current menu...
     🔧 AI ran: pizza --help
     🔧 AI ran: pizza price margherita --size L
  ✅ [with CLI] A large Margherita costs $52.00.
     🔌 AI called: get_price({"pizza": "Margherita", "size": "L"})
  ✅ [with MCP] A large Margherita costs $52.00.
```

*(Exemplo ilustrativo. As respostas da IA variam.)*

No fim, sai o placar. Cole o seu aqui. 👇

| Modo | Acertos | Tokens totais | Chamadas de ferramenta | Custo fixo por chamada |
|---|---|---|---|---|
| no tools | ? / 6 | ? | 0 | 0 tokens |
| with CLI | ? / 6 | ? | ? | ? tokens |
| with MCP | ? / 6 | ? | ? | ? tokens |

**Custo fixo** = tokens que as descrições das ferramentas somam em **toda** chamada.

---

## 🔍 O que observar no resultado

**1. Sem ferramenta, a IA erra.**
O cardápio é inventado. Ela só pode chutar ou dizer "não sei".

**2. CLI e MCP devem acertar parecido.**
Os dois dão acesso aos mesmos dados.

**3. Aqui, o custo fica perto do empate.**
São só 3 ferramentas MCP, então o "cardápio" é pequeno.
O CLI pode gastar uma chamada a mais rodando `--help`.
Com 30 ou mais ferramentas, o MCP pesaria bem mais.

---

## ✨ O que torna uma ferramenta boa para IA

Vale para CLI e para MCP:

| Detalhe | No CLI | No MCP |
|---|---|---|
| Explica como usar | `--help` com exemplos | Descrição clara em cada ferramenta |
| Saída fácil de ler | `--json` | Retorna JSON |
| Erro com dica | `Hint: run 'menu'` | `Hint: use list_menu` |
| Não estraga nada | Só leitura + comandos permitidos | Só leitura |

---

## ⚖️ Ressalvas honestas

- **Com ferramenta, a IA gasta mais tokens que sem.** Ela consulta e lê saídas. O ganho é **acerto**.
- **CLI não vence sempre.** Com muitas ferramentas, há estudos em que o MCP teve mais sucesso.
- **Ferramenta ruim atrapalha.** Sem boa descrição e erros claros, a IA se perde, seja CLI ou MCP.

Leituras (em inglês):
- [MCP vs CLI: benchmark real na AWS (dev.to)](https://dev.to/webramos/mcp-vs-cli-for-ai-agents-a-real-aws-benchmark-and-why-the-popular-narrative-asks-the-wrong-4h8)
- [MCP vs CLI: qual usar em 2026 (Firecrawl)](https://www.firecrawl.dev/blog/mcp-vs-cli)
- [MCP vs CLI: qual é melhor para IA agêntica (Nordic APIs)](https://nordicapis.com/mcp-vs-cli-which-is-better-for-agentic-ai/)
- [MCP vs CLI para agentes: guia corporativo (Tyk)](https://tyk.io/learning-center/mcp-vs-cli-for-ai-agents-enterprise-comparison-guide/)

---

## 🎯 Desafios para você

1. Remova os exemplos do `--help`. A IA com CLI erra mais?
2. Apague as descrições das ferramentas MCP. O que muda?
3. Crie 20 ferramentas MCP falsas. Veja o "custo fixo" subir.
4. Crie o comando `pizza combo` e a ferramenta `combo` com desconto.
5. Mude `available` da Pepperoni para `true` e rode de novo.

---

## 📄 Licença

MIT. Use, copie e ensine. 🍕
