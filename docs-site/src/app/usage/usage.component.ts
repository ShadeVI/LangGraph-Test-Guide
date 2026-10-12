import { Component } from '@angular/core';
import { RevealDirective } from '../shared/reveal.directive';

@Component({
  selector: 'app-section-usage',
  imports: [RevealDirective],
  template: `
    <section id="uso" class="section">
      <div class="container">
        <div appReveal>
          <span class="kicker">05 · Guía técnica</span>
          <h2>Prepara y prueba <span class="hl">todo, paso a paso</span></h2>
          <p class="lead">
            Sigue los pasos en orden y al final tendrás el pipeline, la API y la web
            funcionando en tu PC. Todo se opera desde la raíz del repositorio
            <code>python-langGraph</code> (el backend) y <code>docs-site/</code> (la web).
          </p>
        </div>

        <div appReveal>
          <h3>Paso 0 · Requisitos (comprueba que los tienes)</h3>
          <table class="doc-table">
            <tr><th>Qué</th><th>Para qué</th><th>Cómo comprobarlo</th></tr>
            <tr><td>Python 3.12 – 3.15</td><td>Backend, agentes y API</td><td>python --version</td></tr>
            <tr><td>Ollama (opcional)</td><td>Modelos locales sin API keys</td><td>ollama --version</td></tr>
            <tr><td>Node.js 20+</td><td>Solo para ver la web en local</td><td>node --version</td></tr>
          </table>
          <div class="callout warn">
            <strong>Nota Python 3.15:</strong> <code>requirements.txt</code> lleva pines
            compatibles (<code>langgraph==0.2.28</code>) porque LangGraph 1.x exige
            <code>ormsgpack</code>, sin wheel para 3.15. En Python ≤3.12 puedes usar
            versiones recientes sin pines.
          </div>
        </div>

        <div appReveal>
          <h3>Paso 1 · Ollama en local (mini-guía completa)</h3>
          <div class="grid2">
            <div>
              <p class="lead" style="font-size: 0.93rem">
                <strong>1. Instala Ollama.</strong> En Windows descarga el instalador desde
                <code>ollama.com</code> o con winget (deja el servidor residente en la bandeja):
              </p>
              <pre class="code">winget install Ollama.Ollama
ollama --version   <span class="c"># confirma la instalación</span></pre>
              <p class="lead" style="font-size: 0.93rem">
                <strong>2. Descarga un modelo</strong> (verificado en este proyecto con
                <code>qwen3.5:4b</code>; vale cualquier otro cambiando el nombre):
              </p>
              <pre class="code">ollama pull qwen3.5:4b
ollama list        <span class="c"># debe aparecer qwen3.5:4b</span></pre>
            </div>
            <div>
              <p class="lead" style="font-size: 0.93rem">
                <strong>3. Arranca el servidor</strong> (solo si no está ya en la bandeja):
              </p>
              <pre class="code">ollama serve   <span class="c"># escucha en http://localhost:11434</span></pre>
              <p class="lead" style="font-size: 0.93rem">
                <strong>4. Comprueba que todo vive</strong> (la misma API que usa el backend):
              </p>
              <pre class="code">curl.exe -s http://localhost:11434/api/tags
ollama ps          <span class="c"># qué modelo está cargado y si usa CPU/GPU</span></pre>
              <div class="callout">
                <strong>¿Cómo sabe serve qué modelo servir? No lo elige: los sirve TODOS.</strong>
                <code>ollama serve</code> solo expone la API en el puerto 11434; el modelo concreto
                se decide en <strong>cada petición</strong> (en nuestro caso,
                <code>.env → OLLAMA_MODEL=qwen3.5:4b</code>). Si al arrancar dice
                «puerto en uso», es buena señal: ya estaba corriendo en la bandeja.
              </div>
              <div class="callout warn">
                <strong>Ojo en CPU:</strong> sin GPU cada llamada tarda ~30–90 s. Por eso el
                proyecto trae <code>OLLAMA_NUM_PREDICT=1024</code> (tope de tokens) y
                <code>OLLAMA_THINK=false</code> (sin razonamiento interno en qwen3.x).
              </div>
            </div>
          </div>
        </div>

        <div class="grid2">
          <div appReveal>
            <h3>Paso 2 · Python y configuración (.env)</h3>
            <pre class="code"><span class="c"># 1. Dependencias (incluye fastapi, uvicorn y httpx para la API)</span>
pip install -r requirements.txt

<span class="c"># 2. Crea tu .env a partir del ejemplo</span>
Copy-Item .env.example .env

<span class="c"># 3. Edita .env. Ejemplo mínimo SOLO local (sin keys):</span>
OLLAMA_MODEL=qwen3.5:4b
OLLAMA_NUM_PREDICT=1024
OLLAMA_THINK=false
MAX_REVISIONS=2

<span class="c"># Para la API en modo live, añade en el mismo .env:</span>
API_MODE=live

<span class="c"># Con nube, añade además: GROQ_API_KEY=…  GOOGLE_API_KEY=…</span></pre>
            <div class="callout ok">
              <strong>Sin keys no pasa nada:</strong> Groq y Gemini se omiten con un aviso único
              al arrancar y todo lo resuelve Ollama. Es el setup perfecto para aprender gratis.
            </div>
          </div>
          <div appReveal [delay]="120">
            <h3>Paso 3 · Prueba el pipeline (CLI + tests)</h3>
            <pre class="code"><span class="c"># Consulta directa + guardar informe</span>
python main.py -q <span class="s">"¿Qué es LangGraph?"</span> -o output/informe.md

<span class="c"># Modo interactivo (te pide la pregunta)</span>
python main.py

<span class="c"># 3 inputs que recorren rutas distintas (lineal, revisión, fallback+tope)</span>
python demo_paths.py

<span class="c"># Tests: 21 del grafo + 6 de la API + 14 de finanzas (dobles, sin red ni keys)</span>
python tests/test_pipeline.py
python tests/test_api.py
python tests/test_finance.py</pre>
            <div class="callout">
              <strong>Qué mirar en los logs:</strong> la cadena de fallback al arrancar, el veredicto
              del editor, las decisiones de <code>Enrutado: editor -&gt; writer/END</code> y el resumen
              final con la <code>Ruta recorrida</code>.
            </div>
          </div>
        </div>

        <div appReveal>
          <h3>Modos demo vs live (variable API_MODE)</h3>
          <p class="lead" style="font-size: 0.95rem">
            La API tiene dos modos y se eligen en el <code>.env</code>. Entiende la diferencia
            antes de arrancar nada:
          </p>
          <div class="grid2">
            <div class="card">
              <p><span class="tag">demo</span> <strong>LLM guionizado, sin keys.</strong> Respuestas
              deterministas que siempre muestran el ciclo editor → writer. Instantáneo: ideal para
              ver el grafo trabajar y para la web sin backend.</p>
              <pre class="code"><span class="c"># .env (es el valor por defecto)</span>
API_MODE=demo</pre>
            </div>
            <div class="card">
              <p><span class="tag">live</span> <strong>Proveedores reales</strong> (Groq → Gemini →
              Ollama según tu <code>.env</code>). Cada ejecución tarda 30–60 s o varios minutos en
              CPU local, y consume cuota de tus API keys.</p>
              <pre class="code"><span class="c"># .env (preferible: queda guardado y documentado)</span>
API_MODE=live
OLLAMA_MODEL=qwen3.5:4b</pre>
            </div>
          </div>
          <div class="callout">
            <strong>El arranque es idéntico</strong> (<code>python -m uvicorn api.main:app --port 8000</code>);
            solo cambia el modo. La página <code>/demo</code> lo detecta sola (distintivo
            «● API demo/live») y el informe final siempre indica en qué modo se generó.
          </div>
        </div>

        <div class="grid2">
          <div appReveal>
            <h3>Paso 4 · Prueba la API en modo demo (sin keys, instantáneo)</h3>
            <pre class="code"><span class="c"># Terminal 1: arranca la API (modo demo por defecto)</span>
python -m uvicorn api.main:app --port 8000

<span class="c"># Terminal 2: comprueba salud y lanza una ejecución</span>
curl.exe -s http://localhost:8000/api/health
curl.exe -s -X POST http://localhost:8000/api/run -H <span class="s">"Content-Type: application/json"</span> -d <span class="s">'{{ '{' }}"query": "¿Qué es LangGraph?", "max_revisions": 2{{ '}' }}'</span>

<span class="c"># Documentación interactiva (Swagger):</span>
<span class="c"># abre http://localhost:8000/docs en el navegador</span></pre>
            <div class="callout ok">
              <strong>Qué esperar:</strong> el distintivo dirá <code>mode: demo</code> y la ruta
              siempre será <code>researcher → writer → editor → writer → editor</code> (el guion
              fuerza una revisión para que veas el ciclo). Tarda segundos.
            </div>
          </div>
          <div appReveal [delay]="120">
            <h3>Paso 5 · Prueba en modo live + la web (con tu Ollama)</h3>
            <pre class="code"><span class="c"># Terminal 1: API en modo live (ya configurado en tu .env)</span>
python -m uvicorn api.main:app --port 8000
<span class="c"># Revisa que tu .env tenga: OLLAMA_MODEL=qwen3.5:4b y API_MODE=live</span>

<span class="c"># Terminal 2: la web (primera vez: npm install)</span>
cd docs-site
npx ng serve --open   <span class="c"># http://localhost:4200/demo</span></pre>
            <div class="callout">
              <strong>En /demo:</strong> comprueba que el distintivo pone <code>● API live</code>,
              escribe tu pregunta y pulsa <strong>Transmitir en vivo</strong>. Verás cada nodo,
              cada transición y el estado del grafo en tiempo real. En CPU local calcula
              ~30–90 s por llamada (3–5 llamadas por ejecución).
            </div>
            <div class="callout warn">
              <strong>Si algo falla:</strong> 1) ¿Ollama responde? (<code>ollama ps</code> y
              <code>/api/tags</code>). 2) ¿El nombre en <code>OLLAMA_MODEL</code> es exacto?
              (<code>ollama list</code>). 3) ¿La API está en el puerto 8000? Mira el distintivo
              de conexión de /demo: te dice el comando exacto.
            </div>
          </div>
        </div>

        <div appReveal>
          <h3>Probar el flujo financiero (CSV + MCP + informe)</h3>
          <div class="grid2">
            <div>
              <p class="lead" style="font-size: 0.93rem">
                <strong>Directo (un paso):</strong> sube tu CSV o nada (usa el mock con 1 alerta
                garantizada):
              </p>
              <pre class="code"><span class="c"># Con tu CSV</span>
curl.exe -s -X POST http://localhost:8000/api/finance/run -F <span class="s">"file=@gastos.csv"</span>

<span class="c"># Sin fichero → mock_gastos.csv</span>
curl.exe -s -X POST http://localhost:8000/api/finance/run</pre>
            </div>
            <div>
              <p class="lead" style="font-size: 0.93rem">
                <strong>En vivo (dos pasos):</strong> guarda un job y retransmite por SSE, igual
                que la consola /demo:
              </p>
              <pre class="code"><span class="c"># 1. Valida y guarda → {{ '{' }}"job_id": "..."{{ '}' }}</span>
curl.exe -s -X POST http://localhost:8000/api/finance/jobs

<span class="c"># 2. Retransmite: start → node → route … → done</span>
curl.exe -s -N <span class="s">"http://localhost:8000/api/finance/stream?job_id=..."</span></pre>
              <div class="callout ok">
                <strong>Inspecciona el MCP aparte:</strong> el servidor también habla con
                herramientas estándar (<code>mcp dev</code> o cualquier inspector MCP contra
                <code>python -m mcp_server.server</code>).
              </div>
            </div>
          </div>
        </div>

        <div appReveal>
          <h3>Variables de entorno (.env): referencia rápida</h3>
          <table class="doc-table">
            <tr><th>Variable</th><th>Defecto</th><th>Rol</th></tr>
            @for (row of env; track row[0]) {
              <tr><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td></tr>
            }
          </table>
        </div>

        <div appReveal>
          <h3>Extra · Usarlo como librería (DIP: todo se inyecta)</h3>
          <pre class="code"><span class="k">from</span> config.settings <span class="k">import</span> get_settings
<span class="k">from</span> src.graph.builder <span class="k">import</span> build_graph
<span class="k">from</span> src.state <span class="k">import</span> initial_state

graph = <span class="f">build_graph</span>(<span class="f">get_settings</span>())
final = graph.<span class="f">invoke</span>(<span class="f">initial_state</span>(<span class="s">"¿Qué es LangGraph?"</span>))

print(final[<span class="s">"final_report"</span>])    <span class="c"># informe Markdown</span>
print(final[<span class="s">"providers_used"</span>])  <span class="c"># ['gemini', 'gemini', 'groq']…</span>
print(final[<span class="s">"errors"</span>])          <span class="c"># fallos recuperados vía fallback</span></pre>
        </div>
      </div>
    </section>
  `,
  styles: [
    `
      h3 { margin-top: 1.6rem; }
      code { font-family: var(--mono); font-size: 0.82em; color: var(--accent-2); }
    `,
  ],
})
export class UsageSectionComponent {
  readonly env: string[][] = [
    ['GROQ_API_KEY', '—', 'Proveedor prioritario (nube)'],
    ['GOOGLE_API_KEY', '—', 'Segundo en el fallback (nube)'],
    ['GROQ_MODEL / GEMINI_MODEL', 'llama-3.3-70b… / gemini-flash-latest', 'Modelos por proveedor'],
    ['OLLAMA_MODEL / OLLAMA_BASE_URL', 'llama3.1 / localhost:11434', 'Respaldo local sin key'],
    ['OLLAMA_NUM_PREDICT', '1024', 'Tope de tokens por llamada (imprescindible en CPU)'],
    ['OLLAMA_THINK', 'false', 'Razonamiento interno qwen3.x (en CPU, dejar en false)'],
    ['LLM_TEMPERATURE / LLM_TIMEOUT', '0.2 / 60', 'Generación y timeout (s)'],
    ['LOG_LEVEL', 'INFO', 'INFO, DEBUG, WARNING, ERROR'],
    ['MAX_REVISIONS', '2', 'Vueltas máximas del ciclo editor→writer (0 = lineal)'],
    ['FINANCE_BUDGETS', 'data/budgets.json', 'Ruta de la BD ficticia del servidor MCP'],
    ['FINANCE_FX_URL', 'Frankfurter (dev)', 'Endpoint de la tasa EUR→USD (override para tests)'],
    ['API_MODE', 'demo', 'demo = LLM guionizado (web sin keys) · live = proveedores reales'],
  ];
}
