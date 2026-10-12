import { Component } from '@angular/core';
import { RevealDirective } from '../shared/reveal.directive';

@Component({
  selector: 'app-section-langgraph',
  imports: [RevealDirective],
  template: `
    <section id="langgraph" class="section alt">
      <div class="container">
        <div appReveal>
          <span class="kicker">02 · Orquestación</span>
          <h2>¿Qué es <span class="hl">LangGraph</span>?</h2>
          <p class="lead">
            LangGraph es la librería (creada por el equipo de LangChain, inspirada en
            <strong>Pregel</strong> de Google) para construir aplicaciones con LLMs como
            <strong>grafos de estado</strong>. Cuando el flujo deja de ser una línea recta
            —necesitas ciclos, decisiones, reintentos o varios agentes que colaboran—,
            las cadenas lineales se quedan cortas: necesitas un grafo.
          </p>
        </div>

        <div appReveal>
          <h3>¿Cómo funciona? El patrón en 5 pasos</h3>
          <ol class="steps">
            @for (s of steps; track s.title; let i = $index) {
              <li appReveal [delay]="i * 80">
                <strong>{{ i + 1 }}. {{ s.title }}</strong>
                <span>{{ s.text }}</span>
              </li>
            }
          </ol>
        </div>

        <div class="grid2" style="margin-top: 1rem">
          <div appReveal>
            <h3>El patrón en código (nuestro proyecto)</h3>
            <pre class="code"><span class="k">from</span> langgraph.graph <span class="k">import</span> END, StateGraph

grafo = <span class="f">StateGraph</span>(Estado)   <span class="c"># 1. el estado viaja</span>

grafo.<span class="f">add_node</span>(<span class="s">"analyzer"</span>, analizar)  <span class="c"># 2. nodos</span>
grafo.<span class="f">add_node</span>(<span class="s">"synthesizer"</span>, sintetizar)
grafo.<span class="f">add_node</span>(<span class="s">"reviewer"</span>, revisar)

grafo.<span class="f">set_entry_point</span>(<span class="s">"analyzer"</span>)  <span class="c"># 3. entrada</span>
grafo.<span class="f">add_edge</span>(<span class="s">"analyzer"</span>, <span class="s">"synthesizer"</span>)  <span class="c"># 4a. fija</span>
grafo.<span class="f">add_edge</span>(<span class="s">"synthesizer"</span>, <span class="s">"reviewer"</span>)

grafo.<span class="f">add_conditional_edges</span>(  <span class="c"># 4b. decide según estado</span>
    <span class="s">"reviewer"</span>, donde_voy,
    {{ '{' }}<span class="s">"synthesizer"</span>: <span class="s">"synthesizer"</span>, <span class="s">"end"</span>: END{{ '}' }})

app = grafo.<span class="f">compile</span>()  <span class="c"># 5. ejecutable</span></pre>
          </div>
          <div appReveal [delay]="120">
            <h3>Ejecutarlo: todo de golpe o paso a paso</h3>
            <pre class="code"><span class="c"># Una llamada → estado final (lo usa POST /api/run)</span>
final = app.<span class="f">invoke</span>({{ '{' }}<span class="s">"query"</span>: <span class="s">"¿Qué es…?"</span>{{ '}' }})
final[<span class="s">"final_report"</span>]  <span class="c"># informe Markdown</span>
final[<span class="s">"path"</span>]          <span class="c"># ruta recorrida</span>

<span class="c"># Paso a paso → un evento por nodo (lo usa el SSE)</span>
<span class="k">for</span> paso <span class="k">in</span> app.<span class="f">stream</span>(estado):
    <span class="f">emitir</span>(paso)  <span class="c"># analyzer… synthesizer… reviewer…</span></pre>
            <div class="callout ok">
              <strong>El router decide con datos, no con magia:</strong>
              <code>donde_voy</code> lee <code>needs_revision</code> y
              <code>revision_count</code> del estado: REVISAR + vueltas restantes → synthesizer;
              si no → END. Pruébalo en vivo en la página <code>/demo</code>.
            </div>
          </div>
        </div>

        <div class="grid3">
          @for (c of concepts; track c.title; let i = $index) {
            <div class="card" appReveal [delay]="i * 90">
              <div class="ico">{{ c.icon }}</div>
              <h3>{{ c.title }}</h3>
              <p>{{ c.text }}</p>
            </div>
          }
        </div>

        <div class="grid2" style="margin-top: 1rem">
          <div class="card" appReveal>
            <h3>🔁 Lo que una cadena no puede hacer</h3>
            <p>
              Una <em>chain</em> es un DAG lineal: A → B → C. Pero los sistemas multi-agente
              reales necesitan <strong>ciclos</strong> (reintentar el borrador hasta que el
              reviewer lo apruebe), <strong>ramas condicionales</strong> (si falla un proveedor,
              ir a otro) y <strong>estado persistente</strong> entre pasos. LangGraph modela
              todo eso de forma nativa.
            </p>
            <span class="tag">ciclos</span>
            <span class="tag">edges condicionales</span>
            <span class="tag">persistencia / memoria</span>
            <span class="tag">human-in-the-loop</span>
            <span class="tag">streaming por nodo</span>
          </div>
          <div class="card" appReveal [delay]="120">
            <h3>⚖️ LangChain vs LangGraph</h3>
            <table class="doc-table">
              <tr><th></th><th>LangChain</th><th>LangGraph</th></tr>
              @for (row of compare; track row[0]) {
                <tr>
                  <td>{{ row[0] }}</td>
                  <td>{{ row[1] }}</td>
                  <td>{{ row[2] }}</td>
                </tr>
              }
            </table>
          </div>
        </div>

        <div class="callout" appReveal>
          <strong>Idea clave:</strong> el <strong>estado</strong> (un diccionario tipado) viaja
          por el grafo; cada <strong>nodo</strong> lee lo que necesita y devuelve un
          <em>patch</em> parcial; cada <strong>arista</strong> decide el siguiente paso. Esa es
          exactamente la anatomía de nuestro proyecto: <code>GraphState → analyzer →
          synthesizer → reviewer → END</code>.
        </div>
      </div>
    </section>
  `,
  styles: [
    `
      .steps { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.7rem; }
      .steps li {
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 0.7rem 0.9rem;
        background: rgba(8, 13, 29, 0.55);
      }
      .steps li strong { display: block; font-size: 0.93rem; }
      .steps li span { color: var(--muted); font-size: 0.88rem; }
      h3 { margin-top: 1.6rem; }
      code { font-family: var(--mono); font-size: 0.82em; color: var(--accent-2); }
    `,
  ],
})
export class LanggraphSectionComponent {
  readonly steps = [
    {
      title: 'Define el estado',
      text: 'Un TypedDict con todo lo que viaja: la pregunta, lo que aporta cada agente y la trazabilidad. Es el único contrato entre nodos.',
    },
    {
      title: 'Añade nodos (funciones puras)',
      text: 'Cada nodo recibe el estado y devuelve un patch parcial (research_points, draft…). No se llaman entre ellos: solo existen dentro del grafo.',
    },
    {
      title: 'Conecta con aristas',
      text: 'Flechas fijas para lo determinista (analyzer → synthesizer) y condicionales para lo que depende del contenido (el veredicto del revisor).',
    },
    {
      title: 'Compila el grafo',
      text: 'El builder valida el plano y produce un ejecutable: mismo grafo, usable desde CLI, tests, API o streaming.',
    },
    {
      title: 'Ejecuta como quieras',
      text: 'invoke() devuelve el estado final de una vez; stream() emite un evento por nodo, ideal para retransmitir el progreso por SSE.',
    },
  ];

  readonly concepts = [
    {
      icon: '🕸️',
      title: 'StateGraph',
      text: 'Defines nodos (funciones) y aristas (transiciones). Al compilar obtienes un ejecutable que puedes invocar, inspeccionar y persistir.',
    },
    {
      icon: '📦',
      title: 'Estado compartido',
      text: 'Un TypedDict que fluye entre nodos. Cada nodo aporta su parte (research_points, draft, final_report) sin acoplarse a los demás.',
    },
    {
      icon: '🚦',
      title: 'Control total del flujo',
      text: 'Aristas fijas o condicionales, punto de entrada configurable y nodo END. Sabes exactamente qué se ejecuta y en qué orden.',
    },
  ];

  readonly compare: string[][] = [
    ['Modelo mental', 'Tubería lineal (pipe)', 'Grafo con estado (red)'],
    ['Flujo ideal', 'Pregunta → respuesta', 'Agentes que colaboran por fases'],
    ['Ciclos / reintentos', 'Manuales y frágiles', 'Nativos del grafo'],
    ['Varios agentes', 'Difícil de coordinar', 'Nodos con responsabilidades únicas'],
    ['Depuración', 'Caja gris', 'Logs por nodo + estado inspeccionable'],
  ];
}
