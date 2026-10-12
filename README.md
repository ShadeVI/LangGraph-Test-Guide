# Sistema Multi-Agente con LangGraph — Investigación → Redacción → Edición

Pipeline resiliente con **fallback de proveedores** (Groq → Gemini → Ollama) y observabilidad total.

## Arquitectura (módulos)

```
python-langGraph/
├── main.py                    # CLI: --query / --output, imprime + guarda Markdown
├── config/
│   ├── settings.py            # Pydantic Settings (.env) — DIP
│   └── logging_config.py      # logging estándar (INFO/WARNING/ERROR), sin prints
├── src/
│   ├── state.py               # GraphState (TypedDict estricto) + initial_state()
│   ├── llm/                   # Strategy Pattern
│   │   ├── base.py            # LLMStrategy (ABC) + LLMProviderError
│   │   ├── groq_strategy.py   # Prioridad 1
│   │   ├── gemini_strategy.py # Prioridad 2
│   │   ├── ollama_strategy.py # Prioridad 3 (local, sin key)
│   │   ├── resilient_client.py# Fallback: WARNING + siguiente proveedor
│   │   └── factory.py         # Orden Groq→Gemini→Ollama
│   ├── agents/                # SRP: 1 agente = 1 responsabilidad
│   │   ├── base_agent.py      # Template Method + trazabilidad (duración, path)
│   │   ├── researcher.py      # Consulta → `research_points: list[str]`
│   │   ├── writer.py          # Puntos (+feedback) → `draft`, cuenta revisiones
│   │   └── editor.py          # Borrador → veredicto + `final_report` (Markdown)
│   └── graph/
│       ├── nodes.py           # Adaptadores puros para StateGraph
│       └── builder.py         # researcher → writer → editor -[REVISAR]→ writer / -[APROBADO]→ END
└── tests/test_pipeline.py     # Tests con dobles (sin red ni keys)
└── demo_paths.py              # 3 inputs que recorren rutas distintas del grafo
```

## Principios aplicados

| Principio | Dónde |
|---|---|
| SRP | Cada agente/estrategia tiene una única responsabilidad |
| OCP | Nuevo proveedor = nueva subclase `LLMStrategy`, sin tocar cliente ni agentes |
| DIP | Agentes dependen de `ResilientLLMClient` (abstracción inyectada), no de SDKs |
| Strategy + Factory | `src/llm/` — fallback ordenado y tolerante a fallos |
| Template Method | `BaseAgent.run()` (logging) + `_execute()` (lógica) |
| Clean Code | Type hints completos, docstrings Google-style, sin `print` en librería |

## Instalación

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env   # y rellena GROQ_API_KEY / GEMINI_API_KEY
# Ollama (opcional, respaldo local): ollama serve; ollama pull llama3.1
```

## Uso

```powershell
python main.py --query "¿Qué es LangGraph y para qué sirve?" --output output/informe.md
python main.py   # modo interactivo
python tests/test_pipeline.py   # 15 tests sin red (dobles deterministas)
python tests/test_api.py        # 6 tests de la API REST (modo demo)
python demo_paths.py            # 3 inputs de ejemplo: lineal, 1 revisión, fallback+tope
```

## Sitio de documentación (Angular 22, multipágina)

Páginas con routing (`/`, `/langchain`, `/langgraph`, `/proyecto`, `/por-que`,
`/uso`, `/ejemplos`) más la consola **`/demo`**, que ejecuta los agentes de verdad
contra la API y muestra la línea de tiempo nodo a nodo por SSE:

```powershell
cd docs-site
npm install
npx ng serve --open   # http://localhost:4200
```

## Flujo financiero (CSV + tools MCP → informe)

Segundo grafo de ejemplo: `loader → extractor → analyst ⇄ tools → reporter`.
Subes un CSV de gastos (`fecha,concepto,categoria,importe,moneda`) y el analista
consulta por protocolo MCP un servidor propio (`mcp_server/`, stdio):

- `get_budget_limit(categoria)` → lee `data/budgets.json` (BD ficticia).
- `get_eur_usd_rate()` → tasa EUR→USD en tiempo real (Frankfurter, sin key).

Sin fichero se usa `data/mock_gastos.csv` (provoca 1 alerta a propósito).
El loop analyst↔tools está acotado (`MAX_TOOL_ITERATIONS=5`) y el informe
Markdown lo compone un reporter determinista (sin llamada LLM: rápido y testeable).

```powershell
python tests/test_finance.py   # 12 tests (MCP real por stdio incluido)
```

## API REST (FastAPI, `api/`)

Expone el grafo por HTTP para integrarlo en la web (o en cualquier cliente).
Dos modos vía `API_MODE`: `demo` (LLM guionizado, sin keys, muestra el ciclo) y
`live` (Groq → Gemini → Ollama reales). Auto-documentación en `/docs`.

```powershell
pip install -r requirements.txt   # incluye fastapi, uvicorn y httpx
python -m uvicorn api.main:app --port 8000   # demo (API_MODE=demo en .env)
# live: pon API_MODE=live en tu .env (+ keys de nube si las tienes) y arranca igual
```

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/health` | Sonda de vida + modo activo |
| GET | `/api/config` | Config pública (orden de proveedores, sin secretos) |
| POST | `/api/run` | Ejecuta el grafo; devuelve informe, ruta, proveedores y errores |
| GET | `/api/run/stream` | SSE: `start` → (`node` → `route`)* → `done` (ideal para la demo web) |
| POST | `/api/finance/run` | Sube un CSV de gastos (multipart `file`; sin fichero usa el mock) → informe Markdown + trazabilidad |
| POST | `/api/finance/jobs` | Valida y guarda el CSV → `{job_id}` para el streaming |
| GET | `/api/finance/stream?job_id=…` | SSE del análisis: `start` → (`node` → `route`)* → `done` (mismos componentes web) |

## Resiliencia (fallback) y ciclo de revisión

Dos dimensiones independientes, una demostración de LangGraph real:

1. **Fallback intra-nodo**: cada nodo llama a `ResilientLLMClient.generate()`:
   Groq → Gemini → Ollama, con `WARNING` y continuación sin interrumpir el grafo.
2. **Ciclo inter-nodos**: el Editor emite `VEREDICTO: APROBADO | REVISAR - motivo`.
   Con REVISAR, la arista condicional devuelve el flujo a `writer` con el feedback;
   `MAX_REVISIONS=2` (ver `.env`) acota el ciclo y garantiza terminación.

Rutas posibles: `researcher→writer→editor→END` ·
`…→editor→writer→editor→END` · `…→END forzado por tope (WARNING)`.

Detalle del fallback intra-nodo (orden de prioridad):

1. Intenta **Groq** → si `LLMProviderError` (429, red, credenciales), `WARNING` + sigue.
2. Intenta **Gemini** → mismo manejo.
3. Intenta **Ollama local** → si responde, el grafo continúa sin interrupción.
4. Si todos fallan → `LLMAllProvidersFailedError` (único fallo fatal, log `ERROR`).

Cada llamada registra `providers_used` y `errors` en el `GraphState` para auditoría.

## Observabilidad (logging)

```
2026-… | INFO     | …builder | Grafo compilado: researcher -> writer -> editor -[REVISAR]-> writer (máx. 2) / -[APROBADO]-> END.
2026-… | INFO     | …resilient_client | Probando proveedor LLM: groq
2026-… | WARNING  | …resilient_client | Fallo proveedor 'groq': 429… Aplicando fallback…
2026-… | INFO     | …resilient_client | Proveedor 'gemini' respondió correctamente.
2026-… | INFO     | …editor | Veredicto: REVISAR (motivo: falta el ciclo de Calvin).
2026-… | INFO     | …builder | Enrutado: editor -> writer (revisión 1/2; motivo: …).
2026-… | INFO     | …editor | ✔ Nodo 'editor' finalizado en 1.84s.
2026-… | INFO     | main | Ruta recorrida: researcher -> writer -> editor -> writer -> editor
```

Niveles: `INFO` (ciclo de vida, aciertos), `WARNING` (fallo + fallback), `ERROR` (fallo total).
