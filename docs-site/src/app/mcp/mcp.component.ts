import { Component } from '@angular/core';
import { RevealDirective } from '../shared/reveal.directive';

@Component({
  selector: 'app-section-mcp',
  imports: [RevealDirective],
  template: `
    <section id="mcp" class="section roomy">
      <div class="container">
        <div appReveal>
          <span class="kicker">08 · Protocolo</span>
          <h2>¿Por qué <span class="hl">MCP</span>?</h2>
          <p class="lead">
            <strong>MCP (Model Context Protocol)</strong> es el estándar abierto (impulsado por
            Anthropic) para conectar IAs con herramientas externas. Piensa en él como el
            <strong>USB-C de la IA</strong>: antes cada app necesitaba un conector a medida para
            cada herramienta (el problema N×M); con MCP hay <strong>una sola forma</strong> de
            exponer tools y cualquier cliente compatible las usa sin cambiar código.
          </p>
        </div>

        <div appReveal>
          <h3>Cómo funciona (3 piezas + 2 transportes)</h3>
        </div>
        <div class="grid3">
          @for (p of pieces; track p.title; let i = $index) {
            <div class="card" appReveal [delay]="i * 90">
              <div class="ico">{{ p.icon }}</div>
              <h3>{{ p.title }}</h3>
              <p>{{ p.text }}</p>
            </div>
          }
        </div>

        <div class="grid2" style="margin-top: 1rem">
          <div appReveal>
            <h3>Lo que un servidor puede exponer</h3>
            <table class="doc-table">
              <tr><th>Primitiva</th><th>Qué es</th><th>Ejemplo nuestro</th></tr>
              <tr><td>Tools</td><td>Funciones que el modelo decide llamar</td><td>get_budget_limit, get_eur_usd_rate ✓</td></tr>
              <tr><td>Resources</td><td>Datos que el cliente puede leer</td><td>(no lo usamos; budgets.json vive tras la tool)</td></tr>
              <tr><td>Prompts</td><td>Plantillas reutilizables</td><td>(no lo usamos; los prompts están en los agentes)</td></tr>
            </table>
            <div class="callout">
              <strong>Transportes:</strong> <code>stdio</code> (subproceso local: el nuestro, simple
              y sin red) o HTTP/SSE (servidor remoto compartido). Mismo protocolo, distinto cable.
            </div>
          </div>
          <div appReveal [delay]="120">
            <h3>Nuestro montaje, pieza a pieza</h3>
            <pre class="code"><span class="c"># 1. Servidor: 2 tools en ~90 líneas (mcp_server/)</span>
<span class="k">@mcp.tool</span>()
<span class="k">def</span> <span class="f">get_budget_limit</span>(categoria: str) -> str:
    <span class="k">return</span> <span class="s">"{{ '{' }}categoria, limit_eur{{ '}' }}"</span>  <span class="c"># lee budgets.json</span>

<span class="c"># 2. Cliente: una sesión por ejecución (sin estado compartido)</span>
<span class="k">async with</span> <span class="f">stdio_client</span>(...) <span class="k">as</span> (read, write):
    session = <span class="f">ClientSession</span>(read, write)
    tools = <span class="f">convertir</span>(<span class="k">await</span> session.<span class="f">list_tools</span>())

<span class="c"># 3. El grafo las usa como tools LangChain normales</span>
analyst ⇄ ToolNode(tools)  <span class="c"># loop acotado a 5 vueltas</span></pre>
          </div>
        </div>

        <div appReveal>
          <h3>MCP frente a alternativas (decisión honesta)</h3>
          <table class="doc-table">
            <tr><th>Opción</th><th>Cuándo gana</th><th>Por qué no aquí</th></tr>
            @for (row of compare; track row[0]) {
              <tr><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td></tr>
            }
          </table>
          <div class="callout warn">
            <strong>Cuándo NO usar MCP:</strong> si las tools solo las usa tu app y nada más las va
            a consumir, funciones directas son más simples (un subproceso + latencia extra no salen
            gratis). Lo elegimos porque queríamos el ejemplo didáctico y la interoperabilidad real:
            estas mismas tools se inspeccionan y reutilizan fuera del proyecto.
          </div>
        </div>

        <div appReveal>
          <h3>Pruébalo tú (sin nuestra API)</h3>
          <pre class="code"><span class="c"># Tests: incluyen roundtrip real contra el servidor por stdio</span>
python tests/test_finance.py

<span class="c"># Servidor suelto (habla stdio; conéctalo desde un inspector MCP)</span>
python -m mcp_server.server</pre>
        </div>
      </div>
    </section>
  `,
  styles: [
    `
      .roomy { padding: 5.5rem 0 4.5rem; }
      .roomy .lead { line-height: 1.85; margin-bottom: 1.5rem; }
      .roomy .card { padding: 1.5rem 1.6rem; }
      .roomy .card p { line-height: 1.8; margin-bottom: 0.9rem; }
      .roomy table.doc-table th, .roomy table.doc-table td { padding: 0.9rem 1rem; }
      .roomy pre.code { padding: 1.3rem 1.4rem; line-height: 1.75; margin: 1.2rem 0; }
      .roomy .callout { padding: 1.1rem 1.4rem; margin: 1.5rem 0; line-height: 1.75; }
      h3 { margin-top: 2.2rem; margin-bottom: 1.1rem; }
      code { font-family: var(--mono); font-size: 0.82em; color: var(--accent-2); }
    `,
  ],
})
export class McpSectionComponent {
  readonly pieces = [
    {
      icon: '🖥️',
      title: 'Host',
      text: 'La app con IA: Claude Desktop, un inspector… o nuestro grafo financiero. Es quien quiere usar herramientas.',
    },
    {
      icon: '🔌',
      title: 'Cliente',
      text: 'Pieza que habla MCP: abre sesión, lista tools y las invoca. La nuestra vive en src/finance/mcp_tools.py (una sesión por ejecución).',
    },
    {
      icon: '🗄️',
      title: 'Servidor',
      text: 'Expone las capacidades: mcp_server/ con 2 tools (presupuestos + tasa). No sabe quién lo llama: eso es lo potente.',
    },
  ];

  readonly compare: string[][] = [
    ['Funciones directas', 'Solo tu app las usa; máximo rendimiento', 'Queríamos ejemplo interoperable, no atajo'],
    ['Tools LangChain a mano', 'Sin protocolo, todo en un proceso', 'Acopla las tools a este repo para siempre'],
    ['API REST propia', 'Múltiples clientes HTTP heterogéneos', 'Más código (schemas, auth, versionado) para 2 tools'],
    ['MCP', 'Estándar: un servidor, N clientes compatibles', 'Elegido: didáctico, testeable e interoperable'],
  ];
}
