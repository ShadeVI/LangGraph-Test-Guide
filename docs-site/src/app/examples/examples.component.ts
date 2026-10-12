import { Component, signal } from '@angular/core';
import { RevealDirective } from '../shared/reveal.directive';

interface Step {
  stage: string;
  title: string;
  text: string;
  state: string;
}

interface Example {
  tab: string;
  input: string;
  logs: string;
  output: string;
  trace: string;
}

@Component({
  selector: 'app-section-examples',
  imports: [RevealDirective],
  template: `
    <section id="ejemplos" class="section alt">
      <div class="container">
        <div appReveal>
          <span class="kicker">06 · Input → proceso → output</span>
          <h2>Ejemplos <span class="hl">paso a paso</span></h2>
          <p class="lead">
            Pulsa cada etapa para ver cómo el <code>GraphState</code> se enriquece a medida
            que avanza por el grafo. Luego, dos casos reales completos.
          </p>
        </div>

        <div class="stepper" appReveal>
          <div class="dots">
            @for (s of steps; track s.stage; let i = $index) {
              <button
                [class.on]="i === selected()"
                [class.done]="i < selected()"
                (click)="selected.set(i)"
              >
                <span class="dot">{{ i < selected() ? '✓' : i + 1 }}</span>
                {{ s.stage }}
              </button>
            }
          </div>
          @for (s of [steps[selected()]]; track $index) {
            <div class="card fade-swap">
              <div class="step-nav">
                <h3>{{ s.title }}</h3>
                <div>
                  <button class="btn ghost sm" (click)="prev()" [disabled]="selected() === 0">←</button>
                  <button class="btn ghost sm" (click)="next()" [disabled]="selected() === steps.length - 1">→</button>
                </div>
              </div>
              <p>{{ s.text }}</p>
              <pre class="code">{{ s.state }}</pre>
            </div>
          }
        </div>

        <div class="tabs" appReveal>
          <div class="tab-bar">
            @for (e of examples; track e.tab; let i = $index) {
              <button [class.on]="i === tab()" (click)="tab.set(i)">{{ e.tab }}</button>
            }
          </div>
          @for (e of [examples[tab()]]; track $index) {
            <div class="fade-swap">
              <h3>Input</h3>
              <pre class="code">python main.py -q "{{ e.input }}" -o output/informe.md</pre>
              <h3>Procesamiento (logs reales)</h3>
              <pre class="code">{{ e.logs }}</pre>
              <h3>Output (extracto del Markdown final)</h3>
              <pre class="code">{{ e.output }}</pre>
              <div class="callout ok"><strong>Trazabilidad:</strong> {{ e.trace }}</div>
            </div>
          }
        </div>
      </div>
    </section>
  `,
  styles: [
    `
      code { font-family: var(--mono); font-size: 0.82em; color: var(--accent-2); }
      h3 { margin-top: 1.4rem; }
      .stepper { margin-top: 1rem; }
      .dots { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
      .dots button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: var(--card);
        border: 1px solid var(--line);
        color: var(--muted);
        border-radius: 999px;
        padding: 0.4rem 0.9rem 0.4rem 0.4rem;
        font-size: 0.82rem;
        font-weight: 700;
        cursor: pointer;
        transition: border-color 0.2s ease, color 0.2s ease;
      }
      .dots button.on { border-color: var(--accent-2); color: var(--text); }
      .dots button.done { border-color: rgba(52, 211, 153, 0.5); color: var(--text); }
      .dot {
        display: grid;
        place-items: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: rgba(124, 157, 255, 0.15);
        font-size: 0.75rem;
      }
      button.on .dot { background: var(--accent-2); color: #060a18; }
      button.done .dot { background: var(--ok); color: #060a18; }
      .step-nav { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
      .step-nav h3 { margin: 0; }
      .btn.sm { padding: 0.3rem 0.7rem; margin-left: 0.4rem; }
      .btn.sm:disabled { opacity: 0.35; cursor: default; transform: none; }
      .tabs { margin-top: 2.5rem; }
      .tab-bar { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
      .tab-bar button {
        background: transparent;
        border: 1px solid var(--line);
        color: var(--muted);
        border-radius: 10px;
        padding: 0.55rem 1.1rem;
        font-weight: 700;
        font-size: 0.86rem;
        cursor: pointer;
        transition: all 0.2s ease;
      }
      .tab-bar button.on {
        background: linear-gradient(135deg, var(--accent), #5a7bff);
        color: #060a18;
        border-color: transparent;
      }
    `,
  ],
})
export class ExamplesSectionComponent {
  readonly selected = signal(0);
  readonly tab = signal(0);

  readonly steps: Step[] = [
    {
      stage: 'Input',
      title: 'Etapa 0 · Consulta del usuario',
      text: 'El CLI valida la consulta y crea el estado inicial: resto de campos vacíos, current_step en "started".',
      state:
        'GraphState({\n  query: "¿Qué es LangGraph y para qué sirve?",\n  research_points: [],\n  draft: "",\n  final_report: "",\n  providers_used: [],\n  errors: [],\n  current_step: "started"\n})',
    },
    {
      stage: 'Researcher',
      title: 'Etapa 1 · Investigador (nodo researcher)',
      text: 'Llama al LLM con el prompt de análisis y parsea la respuesta en una lista de puntos clave. Registra qué proveedor respondió.',
      state:
        'research_points: [\n  "LangGraph modela flujos como grafos…",\n  "El estado viaja entre nodos…",\n  "Soporta ciclos y persistencia…",\n  …\n]\nproviders_used: ["groq"]\ncurrent_step: "researcher"',
    },
    {
      stage: 'Writer',
      title: 'Etapa 2 · Redactor (nodo writer)',
      text: 'Sintetiza los puntos en un borrador técnico en texto plano: introducción, desarrollo y cierre, sin formato todavía.',
      state:
        'draft: "LangGraph es una librería para…\\n\\nEn primer lugar…"\nproviders_used: ["groq", "groq"]\ncurrent_step: "writer"',
    },
    {
      stage: 'Editor',
      title: 'Etapa 3 · Editor (nodo editor → writer | END)',
      text: 'Pule el estilo y emite un veredicto en la primera línea: APROBADO cierra el grafo (END); REVISAR devuelve el flujo al redactor con el motivo como feedback. La arista condicional + MAX_REVISIONS=2 acotan el ciclo: capacidad no lineal que una cadena simple no puede expresar.',
      state:
        'needs_revision: false  // o true → vuelta a writer\nfinal_report: "# ¿Qué es LangGraph…\\n\\n## Definición…"\nproviders_used: ["groq", "groq", "groq"]\npath: ["researcher", "writer", "editor"]  // o […, "writer", "editor"]\ncurrent_step: "done"',
    },
  ];

  readonly examples: Example[] = [
    {
      tab: 'Caso A · Flujo nominal',
      input: '¿Qué es LangGraph y para qué sirve?',
      logs: [
        "INFO  | Grafo compilado: researcher -> writer -> editor -> END.",
        "INFO  | ▶ Iniciando nodo 'researcher'.",
        'INFO  | Probando proveedor LLM: groq',
        "INFO  | Proveedor 'groq' respondió correctamente.",
        "INFO  | ✔ Nodo 'researcher' finalizado.",
        "INFO  | ▶ Iniciando nodo 'writer'. … ✔ finalizado.",
        "INFO  | ▶ Iniciando nodo 'editor'. … ✔ finalizado.",
        'INFO  | Grafo: pipeline completado.',
      ].join('\n'),
      output:
        '# ¿Qué es LangGraph y para qué sirve?\n\n## Definición\n**LangGraph** es una librería para construir aplicaciones con LLMs como **grafos de estado**…\n\n## Casos de uso\n- Agentes que colaboran por fases\n- Flujos con ciclos y reintentos\n- …',
      trace: 'providers_used = [groq, groq, groq] · errors = [] · informe guardado en output/informe.md',
    },
    {
      tab: 'Caso B · Fallback ante 429',
      input: 'Explica el patrón Strategy en este proyecto',
      logs: [
        'INFO  | Probando proveedor LLM: groq',
        "WARNING | Fallo proveedor 'groq': 429 rate limit superado. Aplicando fallback…",
        'INFO  | Probando proveedor LLM: gemini',
        "INFO  | Proveedor 'gemini' respondió correctamente.",
        "INFO  | ✔ Nodo 'researcher' finalizado. (el grafo continúa sin interrupción)",
      ].join('\n'),
      output:
        '# El patrón Strategy en este proyecto\n\n## Idea\nCada proveedor LLM implementa la interfaz **LLMStrategy** con el método `generate()`…\n\n## Beneficio\nAñadir un proveedor nuevo es añadir una subclase, sin tocar agentes ni grafo.',
      trace:
        'providers_used = [gemini, …] · errors = [[groq] 429 rate limit…] · el usuario solo nota unos segundos más de latencia',
    },
    {
      tab: 'Caso C · Loop + tope',
      input: 'Compara Strategy vs Factory con ejemplos (MAX_REVISIONS=1)',
      logs: [
        'INFO  | Veredicto: REVISAR (motivo: siempre se puede mejorar).',
        'INFO  | Enrutado: editor -> writer (revisión 1/1; motivo: …).',
        'INFO  | Borrador Nº 2 de 12 caracteres (2 puntos base).',
        'INFO  | Veredicto: REVISAR (motivo: siempre se puede mejorar).',
        'WARNING | Enrutado: editor -> END (límite de revisiones alcanzado, máx. 1).',
      ].join('\n'),
      output: '# Parcial v1\n\n…(última versión del editor publicada tal cual)…',
      trace:
        'path = [researcher, writer, editor, writer, editor] · revision_count = 1 · current_step = done · el ciclo siempre termina: garantía anti-bucle infinito',
    },
    {
      tab: 'Caso D · Finanzas + MCP',
      input: 'POST /api/finance/run (sin fichero → mock_gastos.csv, 12 filas)',
      logs: [
        'INFO  | Loader: 12 filas válidas (0 descartadas), mock=True.',
        'INFO  | Extractor: 3 categorías, top=[COMIDA, TRANSPORTE, OCIO].',
        'INFO  | MCP: 2 tools disponibles: [get_budget_limit, get_eur_usd_rate].',
        'INFO  | Analista responde con 4 tool_calls (vía demo-finance).',
        'INFO  | MCP → get_budget_limit + get_eur_usd_rate (tasa 1.1181 del día).',
        'INFO  | Enrutado finance: analyst -> reporter (sin tool_calls).',
        'INFO  | Reporter: informe de 862 caracteres, 2 alertas.',
      ].join('\n'),
      output: '# Informe de gastos — mock_gastos.csv\n\n| COMIDA | 502.00 | — | 502.00 |\n| OCIO | 36.99 | 239.99 (~214.64 EUR) | 251.63 |\n\n- ⚠ COMIDA: supera el límite 300.00 EUR\n- ⚠ OCIO: supera el límite 150.00 EUR',
      trace:
        'path = [loader, extractor, analyst, tools, analyst, reporter] · tool_iterations = 1 · tasa Frankfurter en vivo · informe descargable en /demo',
    },
  ];

  prev(): void {
    this.selected.set(Math.max(0, this.selected() - 1));
  }

  next(): void {
    this.selected.set(Math.min(this.steps.length - 1, this.selected() + 1));
  }
}
