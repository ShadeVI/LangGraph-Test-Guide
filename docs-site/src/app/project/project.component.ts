import { Component } from '@angular/core';
import { RevealDirective } from '../shared/reveal.directive';

@Component({
  selector: 'app-section-project',
  imports: [RevealDirective],
  template: `
    <section id="proyecto" class="section">
      <div class="container">
        <div appReveal>
          <span class="kicker">03 · Caso real</span>
          <h2>El proyecto, <span class="hl">explicado desde cero</span></h2>
          <p class="lead">
            Escribes una pregunta y el sistema te devuelve un
            <strong>informe en Markdown</strong>. Por dentro, tres especialistas de IA
            trabajan en cadena —como en la redacción de un periódico: el reportero
            investiga, el redactor escribe y el editor jefe corrige y maqueta— coordinados
            por un <strong>grafo</strong> que decide el camino de cada consulta.
          </p>
        </div>

        <div appReveal>
          <h3>El viaje de una consulta (5 pasos)</h3>
          <ol class="journey">
            @for (s of journey; track s.title; let i = $index) {
              <li appReveal [delay]="i * 80">
                <span class="j-num">{{ i + 1 }}</span>
                <div>
                  <strong>{{ s.title }}</strong>
                  <p>{{ s.text }}</p>
                </div>
              </li>
            }
          </ol>
          <div class="callout">
            <strong>¿Y si el borrador es malo?</strong> El editor no lo aprueba: emite
            <code>REVISAR + motivo</code> y el grafo <strong>vuelve al redactor</strong> con ese
            feedback (máximo 2 vueltas, configurado en <code>MAX_REVISIONS</code>). Eso —un flujo
            que puede ciclar según lo que decide una IA— es lo que una simple tubería lineal no
            puede hacer, y por eso existe LangGraph.
          </div>
        </div>

        <div appReveal>
          <h3>Los tres agentes (cada uno hace UNA cosa)</h3>
        </div>

        <div class="agents">
          @for (a of agents; track a.node; let i = $index) {
            <div class="card agent" appReveal [delay]="i * 100">
              <div class="agent-head">
                <span class="ico">{{ a.icon }}</span>
                <div>
                  <h3>{{ a.title }}</h3>
                  <span class="tag">{{ a.node }}</span>
                </div>
              </div>
              <p><strong>Lee:</strong> {{ a.reads }}<br /><strong>Escribe:</strong> {{ a.writes }}</p>
              <p>{{ a.text }}</p>
            </div>
          }
        </div>

        <div appReveal>
          <h3>Herramientas utilizadas (qué es cada una y para qué está aquí)</h3>
        </div>
        <div class="grid3">
          @for (t of tools; track t.name; let i = $index) {
            <div class="card" appReveal [delay]="(i % 3) * 90">
              <div class="ico">{{ t.icon }}</div>
              <h3>{{ t.name }}</h3>
              <p><strong>Qué es:</strong> {{ t.what }}</p>
              <p><strong>Aquí sirve para:</strong> {{ t.use }}</p>
            </div>
          }
        </div>

        <div appReveal>
          <h3>Cómo está construido el backend (por capas, de fuera a dentro)</h3>
          <ol class="layers">
            @for (l of layers; track l.name; let i = $index) {
              <li appReveal [delay]="i * 70">
                <div>
                  <strong>{{ l.name }}</strong>
                  <p>{{ l.text }}</p>
                  <div>
                    @for (f of l.files; track f) {
                      <span class="tag">{{ f }}</span>
                    }
                  </div>
                </div>
              </li>
            }
          </ol>
        </div>

        <div class="grid2" style="margin-top: 1rem">
          <div appReveal>
            <h3>El estado: la "carpeta" que se pasan los agentes</h3>
            <p class="lead" style="font-size: 0.93rem">
              Técnicamente es un <code>TypedDict</code> (un diccionario con claves y tipos fijos).
              Cada agente solo lee lo suyo y añade su parte: así pueden cambiar por dentro sin
              romperse entre ellos.
            </p>
            <pre class="code"><span class="k">class</span> <span class="f">GraphState</span>(TypedDict, total=<span class="k">False</span>):
    query: str                  <span class="c"># tu pregunta</span>
    research_points: list[str]  <span class="c"># ← Investigador</span>
    draft: str                  <span class="c"># ← Redactor</span>
    final_report: str           <span class="c"># ← Editor</span>
    needs_revision: bool        <span class="c"># veredicto REVISAR</span>
    revision_count: int         <span class="c"># vueltas dadas</span>
    editor_feedback: str        <span class="c"># motivo a corregir</span>
    providers_used: list[str]   <span class="c"># quién respondió</span>
    errors: list[str]           <span class="c"># fallos recuperados</span>
    path: list[str]             <span class="c"># ruta recorrida</span>
    current_step: str           <span class="c"># etapa actual</span></pre>
          </div>
          <div appReveal [delay]="120">
            <h3>El fallback: si un proveedor falla, el siguiente lo intenta</h3>
            <p class="lead" style="font-size: 0.93rem">
              Patrón <strong>Strategy</strong>: los tres proveedores cumplen la misma interfaz
              (<code>generate(prompt)</code>), así que el cliente resiliente los prueba en orden
              Groq → Gemini → Ollama hasta que uno responde.
            </p>
            <pre class="code"><span class="c"># Cada nodo llama al cliente resiliente:</span>
<span class="k">for</span> strategy <span class="k">in</span> [groq, gemini, ollama]:
    <span class="k">try</span>:
        <span class="k">return</span> strategy.<span class="f">generate</span>(prompt)
    <span class="k">except</span> LLMProviderError <span class="k">as</span> exc:
        log.<span class="f">warning</span>(f<span class="s">"{{ '{' }}s.name{{ '}' }} falla, fallback…"</span>)</pre>
            <div class="callout warn">
              <strong>Tolerancia real:</strong> sin API keys, Groq y Gemini fallan "con gracia"
              y el grafo sigue con Ollama local. Solo si caen los 3 se aborta
              (<code>LLMAllProvidersFailedError</code>).
            </div>
          </div>
        </div>

        <div appReveal>
          <h3>Cómo está construido el frontend (esta web)</h3>
          <p class="lead" style="font-size: 0.95rem">
            Aplicación <strong>Angular 22</strong> multipágina (una ruta por tema) en
            <code>docs-site/</code>. Cada página es un componente standalone; la página
            <code>/demo</code> es una consola en vivo: abre un <strong>SSE</strong> contra la API
            y pinta cada nodo, cada transición y el estado del grafo a medida que ocurren, sin
            librerías de gráficos (solo CSS + <code>EventSource</code> nativo).
          </p>
          <pre class="code">docs-site/src/app/ ──► pages/ (8 rutas: /, /langchain, … /demo)
                    ├── hero, navbar, footer (componentes compartidos)
                    ├── langchain, langgraph, project, … (contenido por tema)
                    └── demo/ (ApiService + consola SSE en vivo)</pre>
        </div>

        <div appReveal>
          <h3>Estructura completa del repositorio</h3>
          <pre class="code">main.py ──► src/graph/builder.py ──► researcher ──► writer ──► editor ──► END
              │            │ (arista condicional)         ▲────────── REVISAR (máx. 2)
              ├── config/ (settings.py ← .env, logging_config.py)
              ├── src/llm/ (groq → gemini → ollama + ResilientLLMClient)
              ├── api/ (FastAPI: /health, /config, POST /run, SSE /run/stream)
              ├── tests/ (test_pipeline.py 17 tests · test_api.py 6 tests)
              └── docs-site/ (esta web en Angular)</pre>
        </div>
      </div>
    </section>
  `,
  styles: [
    `
      .agents { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
      @media (max-width: 860px) { .agents { grid-template-columns: 1fr; } }
      .agent-head { display: flex; gap: 0.7rem; align-items: center; margin-bottom: 0.5rem; }
      .agent p strong { color: var(--text); font-weight: 600; }
      .journey, .layers { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.7rem; }
      .journey li, .layers li {
        display: flex; gap: 0.9rem;
        border: 1px solid var(--line); border-radius: 12px;
        padding: 0.8rem 1rem; background: rgba(8, 13, 29, 0.55);
      }
      .j-num {
        flex: none; display: grid; place-items: center;
        width: 30px; height: 30px; border-radius: 50%;
        background: linear-gradient(135deg, var(--accent), #5a7bff);
        color: #060a18; font-weight: 800; font-size: 0.85rem;
      }
      .journey strong, .layers strong { display: block; font-size: 0.95rem; margin-bottom: 0.2rem; }
      .journey p, .layers p { margin: 0 0 0.4rem; color: var(--muted); font-size: 0.9rem; }
      h3 { margin-top: 1.8rem; }
      code { font-family: var(--mono); font-size: 0.82em; color: var(--accent-2); }
    `,
  ],
})
export class ProjectSectionComponent {
  readonly journey = [
    {
      title: 'Escribes una pregunta',
      text: 'Puede ser cualquier tema ("¿Qué es LangGraph?"). El sistema la valida y abre una "carpeta" vacía (el estado) con tu pregunta dentro.',
    },
    {
      title: 'El Investigador la analiza',
      text: 'Lee tu pregunta y extrae de 5 a 8 puntos clave: definiciones, causas, consecuencias. Es lo único que hace, pero lo hace bien.',
    },
    {
      title: 'El Redactor escribe el borrador',
      text: 'Toma los puntos y redacta un texto técnico con introducción, desarrollo y cierre. Todavía sin formato bonito: texto plano.',
    },
    {
      title: 'El Editor evalúa y maqueta',
      text: 'Primero juzga: ¿cubre los puntos? Si sí → APROBADO y lo convierte a Markdown. Si no → REVISAR con el motivo, y el grafo vuelve al paso 3 con ese feedback.',
    },
    {
      title: 'Recibes el informe (y la trazabilidad)',
      text: 'El Markdown final más el registro de qué proveedor respondió en cada llamada, qué ruta se recorrió y qué fallos se recuperaron por el camino.',
    },
  ];

  readonly agents = [
    {
      icon: '🔍',
      title: 'Agente 1 · Investigador',
      node: 'nodo: researcher',
      reads: 'query',
      writes: 'research_points: list[str]',
      text: 'Analiza la consulta y extrae de 5 a 8 puntos clave en formato lista. Si el LLM no devuelve lista, usa la respuesta como bloque único.',
    },
    {
      icon: '✍️',
      title: 'Agente 2 · Redactor',
      node: 'nodo: writer',
      reads: 'query + research_points',
      writes: 'draft (texto plano)',
      text: 'Sintetiza los puntos en un borrador técnico: introducción, desarrollo y cierre. Sin inventar datos fuera de la investigación.',
    },
    {
      icon: '📝',
      title: 'Agente 3 · Editor',
      node: 'nodo: editor',
      reads: 'query + draft (+ puntos)',
      writes: 'veredicto + final_report (Markdown)',
      text: 'Emite VEREDICTO: APROBADO o REVISAR con motivo. Su veredicto alimenta la arista condicional: REVISAR devuelve el flujo al redactor con feedback; APROBADO cierra en END.',
    },
  ];

  readonly tools = [
    {
      icon: '🐍',
      name: 'Python',
      what: 'Lenguaje de programación, el más usado en IA por su ecosistema.',
      use: 'Todo el backend: agentes, grafo, API y CLI están escritos en Python con tipado estricto.',
    },
    {
      icon: '🦜',
      name: 'LangChain',
      what: 'Framework para llamar a LLMs con una interfaz única, da igual el proveedor.',
      use: 'La capa de acceso a Groq, Gemini y Ollama; cambiar de proveedor es cambiar una clase.',
    },
    {
      icon: '🕸️',
      name: 'LangGraph',
      what: 'Orquestador que modela flujos de IA como grafos con estado (nodos + aristas).',
      use: 'El pipeline researcher → writer → editor con su ciclo de revisión condicional.',
    },
    {
      icon: '⚡',
      name: 'Groq',
      what: 'Nube de inferencia rapidísima con plan gratuito (modelos Llama).',
      use: 'Primer intento del fallback: con API key, casi todo se resuelve aquí en segundos.',
    },
    {
      icon: '✨',
      name: 'Google Gemini',
      what: 'Familia de modelos de Google con API gratuita generosa.',
      use: 'Segundo intento del fallback si Groq falla o no hay key.',
    },
    {
      icon: '🦙',
      name: 'Ollama',
      what: 'Ejecuta modelos open-source en tu propio PC, sin nube ni keys.',
      use: 'Tercer intento (respaldo local) y pruebas 100% offline. Verificado con qwen3.5:4b.',
    },
    {
      icon: '🚀',
      name: 'FastAPI',
      what: 'Framework Python para crear APIs REST rápidas con documentación automática.',
      use: 'Expone el grafo por HTTP (/run y /run/stream por SSE) para que la web lance agentes reales.',
    },
    {
      icon: '🅰️',
      name: 'Angular 22',
      what: 'Framework de Google para aplicaciones web por componentes.',
      use: 'Esta documentación multipágina y la consola /demo que consume la API en vivo.',
    },
    {
      icon: '📐',
      name: 'Pydantic',
      what: 'Validación de datos y configuración con tipos en Python.',
      use: 'El .env se convierte en un objeto Settings tipado; la API valida peticiones y respuestas.',
    },
  ];

  readonly layers = [
    {
      name: 'Entrada: CLI o API REST',
      text: 'Dos puertas al mismo grafo. main.py es la terminal (pregunta → informe por pantalla o archivo). api/ es la puerta HTTP que usa la web: valida la petición, ejecuta y retransmite cada nodo por SSE.',
      files: ['main.py', 'api/main.py', 'api/schemas.py', 'api/service.py'],
    },
    {
      name: 'Configuración y logs',
      text: 'Todo lo ajustable (keys, modelos, timeouts, revisiones, modo demo/live) vive en .env y se lee una sola vez al arrancar. Los logs cuentan la historia de cada ejecución con niveles INFO, WARNING y ERROR.',
      files: ['.env', 'config/settings.py', 'config/logging_config.py'],
    },
    {
      name: 'El grafo: el plano del edificio',
      text: 'Define los nodos (uno por agente), las flechas fijas y la flecha condicional del editor. Compilarlo produce un ejecutable al que le pasas el estado inicial y te devuelve el estado final.',
      files: ['src/graph/builder.py', 'src/graph/nodes.py', 'src/state.py'],
    },
    {
      name: 'Los agentes: los especialistas',
      text: 'Cada uno es una clase pequeña con un prompt enfocado. Comparten una base que mide tiempos y acumula trazabilidad (quién respondió, qué falló, qué ruta se siguió).',
      files: ['src/agents/base_agent.py', 'researcher.py', 'writer.py', 'editor.py'],
    },
    {
      name: 'Los proveedores LLM: los motores intercambiables',
      text: 'Tres clases con la misma interfaz. El cliente resiliente las prueba en orden y el primero que responde gana; si todos fallan, el error sube limpio hasta el usuario.',
      files: ['src/llm/base.py', 'groq/gemini/ollama_strategy.py', 'resilient_client.py'],
    },
  ];
}
