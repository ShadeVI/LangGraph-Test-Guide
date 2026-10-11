import { Component, ElementRef, OnDestroy, OnInit, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RevealDirective } from '../shared/reveal.directive';
import { ApiService, RunResult, StateSnapshot } from './api.service';

interface TimelineEvent {
  node: string;
  summary: string;
  provider: string;
  at: string;
}

interface HistoryLine {
  n: number;
  kind: 'start' | 'node' | 'route' | 'done' | 'error';
  text: string;
  at: string;
}

type Status = 'idle' | 'running' | 'done' | 'error';

const NODE_ICONS: Record<string, string> = {
  researcher: '🔍',
  writer: '✍️',
  editor: '📝',
};

const FLOW = ['researcher', 'writer', 'editor'] as const;

@Component({
  selector: 'app-page-demo',
  imports: [FormsModule, RevealDirective],
  template: `
    <section class="section">
      <div class="container">
        <div appReveal>
          <span class="kicker">07 · Consola en vivo</span>
          <h2>Demo <span class="hl">real</span>: los agentes, en directo</h2>
          <p class="lead">
            Esta página ejecuta el grafo Python de verdad a través de la API FastAPI.
            Elige <strong>cómo</strong> quieres verlo: paso a paso mientras ocurre (SSE)
            o directamente el dossier final (POST).
          </p>
        </div>

        <div class="card" appReveal [delay]="50">
          <h3>¿Qué es SSE y por qué se usa aquí?</h3>
          <p>
            <strong>SSE (Server-Sent Events)</strong> es una técnica donde el servidor mantiene
            abierta una conexión HTTP y va <strong>empujando mensajes</strong> al navegador a medida
            que ocurren (texto con formato <code>event: … / data: …</code>). Es unidireccional:
            solo habla el servidor, y al navegador le basta el <code>EventSource</code> nativo, sin
            librerías ni protocolo nuevo.
          </p>
          <table class="doc-table">
            <tr><th>Técnica</th><th>Cómo funciona</th><th>Cuándo conviene</th></tr>
            <tr><td>Polling</td><td>El navegador pregunta «¿ya?» cada X segundos</td><td>Datos que cambian poco; desperdicia peticiones</td></tr>
            <tr><td><strong>SSE</strong></td><td>El servidor avisa solo cuando hay algo nuevo</td><td><strong>Retransmitir un proceso</strong> (nuestro caso)</td></tr>
            <tr><td>WebSockets</td><td>Canal bidireccional permanente</td><td>Chat, juegos: hablan los dos lados</td></tr>
          </table>
          <p style="margin-bottom: 0.3rem"><strong>Por eso encaja con el grafo:</strong></p>
          <ul class="why">
            <li>Cada nodo terminado es un evento natural (<code>node</code>, <code>route</code>, <code>done</code>): el backend los emite con <code>graph.stream()</code> sin guardar estado extra.</li>
            <li>El usuario ve el progreso <strong>en tiempo real</strong> en vez de un spinner de 60 s.</li>
            <li>Si se cae la conexión, el navegador la reintenta solo; y es HTTP normal (pasa por proxies y CORS sin pelear).</li>
          </ul>
          <pre class="code"><span class="c"># Backend: genera eventos a medida que el grafo avanza</span>
<span class="k">for</span> chunk <span class="k">in</span> graph.<span class="f">stream</span>(estado):
    <span class="k">yield</span> <span class="s">"event: node\ndata: {{ '{' }}...{{ '}' }}\n\n"</span>

<span class="c">// Frontend: escucha sin librerías</span>
<span class="k">const</span> es = <span class="k">new</span> <span class="f">EventSource</span>(url);
es.<span class="f">addEventListener</span>(<span class="s">"node"</span>, e =&gt; pintar(JSON.<span class="f">parse</span>(e.data)));</pre>
        </div>

        <div class="card" appReveal>
          <div class="api-row">
            <label>
              URL de la API
              <input
                class="field"
                [ngModel]="api.baseUrl()"
                (ngModelChange)="api.baseUrl.set($event)"
                placeholder="http://localhost:8000"
              />
            </label>
            <button class="btn ghost" (click)="checkHealth()" [disabled]="busy()">
              Comprobar conexión
            </button>
            <span class="badge" [class.ok]="apiOk()" [class.bad]="apiOk() === false">
              @if (apiOk() === null) { sin comprobar }
              @else if (apiOk()) { ● API {{ apiMode() }} }
              @else { ● sin conexión }
            </span>
          </div>
          @if (apiOk() === false) {
            <div class="callout warn">
              <strong>La API no responde.</strong> Arráncala en una terminal desde la raíz
              del proyecto Python:
              <pre class="code">python -m uvicorn api.main:app --port 8000   <span class="c"># modo demo, sin keys</span></pre>
            </div>
          }
        </div>

        <div class="card" appReveal [delay]="50">
          <h3>Modos demo vs live (variable API_MODE)</h3>
          <div class="grid2">
            <div>
              <p><span class="tag">demo</span> <strong>LLM guionizado, sin keys.</strong> Respuestas
              deterministas que siempre muestran el ciclo editor → writer. Instantáneo: ideal para
              ver el grafo trabajar.</p>
              <pre class="code">python -m uvicorn api.main:app --port 8000</pre>
            </div>
            <div>
              <p><span class="tag">live</span> <strong>Proveedores reales</strong> (Groq → Gemini →
              Ollama según tu <code>.env</code>). Cada ejecución tarda 30–60 s o varios minutos en
              CPU local, y consume cuota de tus API keys.</p>
              <pre class="code"><span class="c"># En tu .env (preferible: queda guardado y documentado)</span>
API_MODE=live
OLLAMA_MODEL=qwen3.5:4b

<span class="c"># Y se arranca igual que en demo:</span>
python -m uvicorn api.main:app --port 8000</pre>
            </div>
          </div>
          <div class="callout">
            <strong>La página detecta el modo sola:</strong> el distintivo «● API demo/live» sale de
            <code>GET /api/health</code>. El informe final siempre indica en qué modo se generó.
          </div>
        </div>

        <div class="card" appReveal [delay]="100">
          <label>
            Consulta para los agentes
            <input
              class="field"
              [ngModel]="query()"
              (ngModelChange)="query.set($event)"
              maxlength="500"
            />
          </label>
          <div class="examples">
            <span>Probar con:</span>
            @for (ex of examples; track ex.label) {
              <button class="chip-btn" (click)="useExample(ex.query)" [disabled]="busy()">{{ ex.label }}</button>
            }
            <small class="ex-note">En <strong>demo</strong>, <em>cualquier</em> pregunta pasa por 1 revisión (está guionizado para mostrar el ciclo). En <strong>live</strong> decide el criterio del modelo: no hay pregunta mágica garantizada, pero las vagas o muy amplias suelen dar borradores flojos que el editor devuelve. Requiere Máx. revisiones ≥ 1.</small>
          </div>
          <div class="form-row">
            <label>
              Máx. revisiones
              <input
                class="field sm"
                type="number"
                min="0"
                max="5"
                [ngModel]="maxRev()"
                (ngModelChange)="maxRev.set($event)"
              />
            </label>
            <div class="btns">
              <div class="mode">
                <button class="btn primary" (click)="runStream()" [disabled]="busy()">
                  ⚡ Transmitir en vivo
                </button>
                <small>SSE: cada nodo aparece aquí <em>mientras trabaja</em>, con su resumen.</small>
              </div>
              <div class="mode">
                <button class="btn ghost" (click)="runOnce()" [disabled]="busy()">
                  Ejecutar y esperar
                </button>
                <small>POST: sin línea de tiempo; solo el dossier final explicado.</small>
              </div>
            </div>
          </div>
        </div>

        @if (showFlow()) {
          <div class="card fade-swap">
            <div class="flow-head">
              <h3>
                @if (status() === 'running') { ⏳ Grafo en ejecución… {{ elapsed() }}s }
                @else { ✅ Ejecución terminada en {{ elapsed() }}s }
              </h3>
              @if (status() === 'running') {
                <div class="progress"><span></span></div>
              }
            </div>
            <div class="flow">
              @for (n of flowNodes; track n; let i = $index) {
                <div class="fnode" [class]="nodeClass(n)">
                  <span class="f-ico">{{ icon(n) }}</span>
                  <strong>{{ n }}</strong>
                  @if (count(n) > 1) { <em>×{{ count(n) }}</em> }
                  @else if (count(n) === 1) { <em>✓</em> }
                </div>
                @if (i < flowNodes.length - 1) {
                  <div class="flink" [class.lit]="lit(i)"></div>
                }
              }
            </div>
            <div class="loop-note">↩ arista condicional: editor —REVISAR→ writer · —APROBADO→ END</div>
          </div>
        }

        @if (history().length > 0) {
          <div class="fade-swap">
            <h3>
              @if (live()) { Historial lineal en vivo }
              @else { Historial lineal (reconstruido del resultado) }
            </h3>
            <div class="console" #consoleBox>
              @for (h of history(); track h.n) {
                <div class="hline {{ h.kind }}">
                  <span class="h-n">{{ h.n }}</span>
                  <span class="h-t">{{ h.text }}</span>
                  <span class="h-at">{{ h.at }}</span>
                </div>
              }
            </div>
          </div>
        }

        @if (snapshot(); as s) {
          <div class="card">
            <h3>🧬 Estado actual del grafo
              @if (live() && status() === 'running') { <span class="tag">en vivo</span> }
              @else { <span class="tag">final</span> }
            </h3>
            <div class="state-grid">
              <div><span>Etapa</span><strong>{{ s.current_step }}</strong></div>
              <div><span>Puntos</span><strong>{{ s.research_points.length }}</strong></div>
              <div><span>Borrador</span><strong>{{ s.draft.length }} caracteres</strong></div>
              <div><span>Revisiones</span><strong>{{ s.revision_count }}</strong></div>
              <div><span>¿Revisar?</span><strong>{{ s.needs_revision ? 'sí' : 'no' }}</strong></div>
              <div><span>Informe</span><strong>{{ s.final_report.length }} caracteres</strong></div>
            </div>
            <details>
              <summary>research_points ({{ s.research_points.length }}) — lo que lee el Writer</summary>
              <ul>
                @for (p of s.research_points; track $index) {
                  <li>{{ p }}</li>
                }
              </ul>
            </details>
            <details>
              <summary>draft — lo que evalúa el Editor</summary>
              <pre class="code report">{{ s.draft || '(vacío: el Writer aún no lo generó)' }}</pre>
            </details>
            @if (s.editor_feedback) {
              <div class="callout warn"><strong>Feedback del editor:</strong> {{ s.editor_feedback }}</div>
            }
          </div>
        }

        @if (error()) {
          <div class="callout warn fade-swap"><strong>Error:</strong> {{ error() }}</div>
        }

        @if (result()) {
          @for (r of [result()!]; track $index) {
            <div class="fade-swap">
              <h3>¿Qué ha pasado? (explicación automática)</h3>
              <div class="card narr">
                <ul>
                  @for (line of narrative(r); track $index) {
                    <li>{{ line }}</li>
                  }
                </ul>
                @if (!live()) {
                  <p class="hint">Modo directo (POST): este modo no emite eventos; usa «Transmitir en vivo» para ver el proceso nodo a nodo.</p>
                }
              </div>
              <h3>Ruta recorrida</h3>
              <div class="route">
                @for (n of r.path; track $index; let last = $last) {
                  <span class="chip">{{ icon(n) }} {{ n }}</span>
                  @if (!last) { <span class="arrow">→</span> }
                }
              </div>
              <div class="grid2">
                <div class="card">
                  <h3>Informe final (modo {{ r.mode }})</h3>
                  <pre class="code report">{{ r.final_report }}</pre>
                </div>
                <div class="card">
                  <h3>Trazabilidad</h3>
                  <p><strong>Revisiones:</strong> {{ r.revision_count }}</p>
                  <p><strong>Paso final:</strong> {{ r.current_step }}</p>
                  <p><strong>Proveedores (en orden de llamada):</strong></p>
                  @for (p of r.providers_used; track $index) {
                    <span class="tag">{{ $index + 1 }}. {{ p }}</span>
                  }
                  <p style="margin-top: 0.6rem"><strong>Errores recuperados:</strong></p>
                  @if (r.errors.length === 0) {
                    <p>ninguno: el primer proveedor respondió a todas las llamadas.</p>
                  } @else {
                    @for (e of r.errors; track $index) {
                      <div class="callout warn">{{ e }}</div>
                    }
                  }
                </div>
              </div>
            </div>
          }
        }
      </div>
    </section>
  `,
  styles: [
    `
      .api-row { display: flex; gap: 0.8rem; align-items: end; flex-wrap: wrap; }
      .api-row label { flex: 1; min-width: 220px; }
      label { display: grid; gap: 0.35rem; font-size: 0.85rem; font-weight: 700; color: var(--muted); }
      .field {
        background: #080d1d;
        border: 1px solid var(--line);
        border-radius: 10px;
        color: var(--text);
        padding: 0.6rem 0.8rem;
        font-size: 0.9rem;
        width: 100%;
      }
      .field:focus { outline: none; border-color: var(--accent); }
      .field.sm { max-width: 110px; }
      .badge {
        font-size: 0.78rem; font-weight: 700;
        border: 1px solid var(--line); border-radius: 999px;
        padding: 0.4rem 0.8rem; color: var(--muted);
      }
      .badge.ok { color: var(--ok); border-color: rgba(52, 211, 153, 0.5); }
      .badge.bad { color: var(--err); border-color: rgba(248, 113, 113, 0.5); }
      .form-row { display: flex; gap: 1.2rem; align-items: end; flex-wrap: wrap; margin-top: 0.9rem; }
      .btns { display: flex; gap: 1.2rem; flex-wrap: wrap; }
      .mode { display: grid; gap: 0.3rem; justify-items: start; }
      .mode small { color: var(--muted); font-size: 0.76rem; max-width: 30ch; }
      .mode small em { color: var(--accent-2); font-style: normal; font-weight: 700; }
      .examples { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-top: 0.9rem; }
      .examples > span { font-size: 0.8rem; font-weight: 700; color: var(--muted); }
      .chip-btn {
        background: rgba(124, 157, 255, 0.1);
        border: 1px solid var(--line); border-radius: 999px;
        color: var(--text); font-size: 0.8rem; font-weight: 700;
        padding: 0.35rem 0.9rem; cursor: pointer;
        transition: border-color 0.2s ease, background 0.2s ease;
      }
      .chip-btn:hover:not(:disabled) { border-color: var(--accent-2); background: rgba(94, 234, 212, 0.1); }
      .chip-btn:disabled { opacity: 0.45; cursor: default; }
      .ex-note { flex-basis: 100%; color: var(--muted); font-size: 0.76rem; }
      .ex-note strong { color: var(--text); }
      .btn:disabled { opacity: 0.45; cursor: default; transform: none; }
      .card { margin-top: 1rem; }
      .flow-head h3 { margin: 0 0 0.7rem; }
      .progress { height: 6px; border-radius: 6px; background: rgba(124,157,255,.15); overflow: hidden; margin-bottom: 1rem; }
      .progress span {
        display: block; height: 100%; width: 40%;
        background: linear-gradient(90deg, var(--accent), var(--accent-2));
        border-radius: 6px;
        animation: slide 1.1s ease-in-out infinite alternate;
      }
      @keyframes slide { from { translate: -30% 0; } to { translate: 180% 0; } }
      .flow { display: flex; align-items: stretch; }
      .fnode {
        flex: 1; text-align: center;
        border: 1px solid var(--line); border-radius: 12px;
        padding: 0.7rem 0.4rem; background: var(--card);
        opacity: 0.45; transition: opacity 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
      }
      .fnode strong { display: block; font-family: var(--mono); font-size: 0.8rem; }
      .fnode em { font-style: normal; color: var(--accent-2); font-weight: 800; font-size: 0.8rem; }
      .f-ico { font-size: 1.3rem; }
      .fnode.seen { opacity: 0.85; border-color: rgba(52, 211, 153, 0.5); }
      .fnode.active {
        opacity: 1; border-color: var(--accent-2);
        animation: pulseGlow 1.2s ease-in-out infinite;
      }
      .flink { flex: 0 0 34px; align-self: center; height: 3px; border-radius: 3px; background: rgba(124,157,255,.18); transition: background 0.3s ease; }
      .flink.lit { background: linear-gradient(90deg, var(--accent), var(--accent-2)); }
      .loop-note { margin-top: 0.6rem; text-align: center; color: var(--muted); font-size: 0.78rem; font-family: var(--mono); }
      .console {
        background: #060b18;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        max-height: 340px;
        overflow-y: auto;
        font-family: var(--mono);
        font-size: 0.8rem;
        display: grid;
        gap: 0.35rem;
      }
      .hline { display: flex; gap: 0.7rem; align-items: baseline; animation: fadeSlideIn 0.3s ease; }
      .h-n { color: var(--muted); min-width: 2ch; text-align: right; }
      .h-t { flex: 1; overflow-wrap: anywhere; }
      .h-at { color: var(--muted); font-size: 0.7rem; white-space: nowrap; }
      .hline.start .h-t { color: var(--text); font-weight: 700; }
      .hline.route .h-t { color: var(--accent-2); }
      .hline.done .h-t { color: var(--ok); font-weight: 700; }
      .hline.error .h-t { color: var(--err); }
      .state-grid {
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem;
        margin-bottom: 0.8rem;
      }
      .state-grid > div {
        border: 1px solid var(--line); border-radius: 10px;
        padding: 0.5rem 0.7rem; background: rgba(8, 13, 29, 0.55);
      }
      .state-grid span { display: block; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
      .state-grid strong { font-family: var(--mono); font-size: 0.88rem; }
      details { border: 1px solid var(--line); border-radius: 10px; padding: 0.55rem 0.9rem; margin-top: 0.6rem; }
      details summary { cursor: pointer; font-size: 0.85rem; font-weight: 700; color: var(--accent-2); }
      details ul { margin: 0.5rem 0 0.2rem; padding-left: 1.2rem; color: var(--muted); font-size: 0.86rem; display: grid; gap: 0.3rem; }
      details pre { margin: 0.5rem 0 0.2rem; }
      @media (max-width: 640px) { .state-grid { grid-template-columns: repeat(2, 1fr); } }
      .route { display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem; }
      .chip {
        font-family: var(--mono); font-size: 0.8rem; font-weight: 700;
        background: rgba(124, 157, 255, 0.12);
        border: 1px solid var(--line); border-radius: 8px; padding: 0.3rem 0.7rem;
      }
      .arrow { color: var(--accent-2); font-weight: 800; }
      .narr ul { margin: 0; padding-left: 1.2rem; display: grid; gap: 0.45rem; }
      .narr li { color: var(--muted); font-size: 0.93rem; }
      .narr li::marker { color: var(--accent-2); }
      .narr .hint { margin: 0.8rem 0 0; font-size: 0.8rem; }
      ul.why { margin: 0.4rem 0 0.8rem; padding-left: 1.2rem; display: grid; gap: 0.4rem; }
      ul.why li { color: var(--muted); font-size: 0.9rem; }
      ul.why li::marker { color: var(--accent-2); }
      h3 { margin-top: 1.4rem; }
      p strong { color: var(--text); }
      @media (max-width: 640px) {
        .flow { flex-direction: column; gap: 0.35rem; }
        .flink { flex: none; width: 3px; height: 22px; margin: 0 auto; }
      }
    `,
  ],
})
export class DemoPage implements OnInit, OnDestroy {
  readonly api = inject(ApiService);
  readonly flowNodes = [...FLOW];

  readonly query = signal('¿Qué es LangGraph y para qué sirve?');
  readonly maxRev = signal(2);
  readonly examples = [
    { label: 'Caso nominal', query: '¿Qué es LangGraph y para qué sirve?' },
    { label: 'Caso revisión', query: 'Fotosíntesis' },
  ];
  readonly status = signal<Status>('idle');
  readonly live = signal(false);
  readonly events = signal<TimelineEvent[]>([]);
  readonly history = signal<HistoryLine[]>([]);
  readonly snapshot = signal<StateSnapshot | null>(null);
  /** Nodo que está trabajando AHORA (inferido del destino de la ruta). */
  readonly activeNode = signal<string | null>(null);
  readonly result = signal<RunResult | null>(null);
  readonly error = signal<string | null>(null);
  readonly apiOk = signal<boolean | null>(null);
  readonly apiMode = signal('');
  readonly elapsed = signal(0);

  private source?: EventSource;
  private timer?: ReturnType<typeof setInterval>;
  private seq = 0;
  private readonly consoleBox = viewChild<ElementRef<HTMLElement>>('consoleBox');

  ngOnInit(): void {
    void this.checkHealth();
  }

  ngOnDestroy(): void {
    this.stopTimer();
    this.source?.close();
  }

  busy(): boolean {
    return this.status() === 'running';
  }

  useExample(q: string): void {
    this.query.set(q);
  }

  showFlow(): boolean {
    return this.status() !== 'idle' && (this.events().length > 0 || this.status() === 'running');
  }

  icon(node: string): string {
    return NODE_ICONS[node] ?? '•';
  }

  count(node: string): number {
    return this.events().filter((e) => e.node === node).length;
  }

  nodeClass(node: string): string {
    // El evento llega cuando el nodo TERMINA; quien TRABAJA es el destino
    // de la última ruta (ver start/route). Así el pulso no va con retraso.
    if (this.status() === 'running' && this.activeNode() === node) return 'active';
    if (this.count(node) === 0) return '';
    return 'seen';
  }

  lit(linkIndex: number): boolean {
    const order = this.flowNodes;
    return this.count(order[linkIndex]) > 0 && this.count(order[linkIndex + 1]) > 0;
  }

  narrative(r: RunResult): string[] {
    const lines = [
      `La consulta recorrió ${r.path.length} pasos: ${r.path.join(' → ')}.`,
    ];
    if (r.revision_count > 0) {
      const motive = r.editor_feedback ? ` por «${r.editor_feedback}»` : '';
      lines.push(
        `El editor pidió ${r.revision_count} revisión${r.revision_count > 1 ? 'es' : ''}${motive}; el redactor generó un borrador nuevo y el editor lo aprobó.`,
      );
    } else {
      lines.push('El editor aprobó el primer borrador: ruta lineal sin revisiones.');
    }
    const tally = new Map<string, number>();
    for (const p of r.providers_used) tally.set(p, (tally.get(p) ?? 0) + 1);
    const who = [...tally.entries()].map(([p, n]) => `${p} ×${n}`).join(', ');
    lines.push(`Respondieron ${r.providers_used.length} llamadas LLM: ${who}.`);
    if (r.errors.length === 0) {
      lines.push('Sin fallos de proveedor: no hizo falta el fallback.');
    } else {
      lines.push(
        `Se recuperaron ${r.errors.length} fallo(s) vía fallback sin interrumpir el grafo.`,
      );
    }
    lines.push(
      `Informe final de ${r.final_report.length} caracteres, estado «${r.current_step}».`,
    );
    return lines;
  }

  async checkHealth(): Promise<void> {
    try {
      const h = await this.api.health();
      this.apiOk.set(h.status === 'ok');
      this.apiMode.set(h.mode);
    } catch {
      this.apiOk.set(false);
      this.apiMode.set('');
    }
  }

  private startTimer(): void {
    this.stopTimer();
    this.elapsed.set(0);
    const t0 = Date.now();
    this.timer = setInterval(() => this.elapsed.set((Date.now() - t0) / 1000), 200);
  }

  private stopTimer(): void {
    if (this.timer !== undefined) clearInterval(this.timer);
    this.timer = undefined;
  }

  private reset(live: boolean): void {
    this.source?.close();
    this.stopTimer();
    this.events.set([]);
    this.history.set([]);
    this.snapshot.set(null);
    this.activeNode.set(null);
    this.seq = 0;
    this.result.set(null);
    this.error.set(null);
    this.live.set(live);
    this.status.set('running');
    this.startTimer();
  }

  /** Añade una línea al historial y desplaza la consola al final. */
  private pushHistory(kind: HistoryLine['kind'], text: string): void {
    this.seq += 1;
    const n = this.seq;
    this.history.update((list) => [
      ...list,
      { n, kind, text, at: new Date().toLocaleTimeString() },
    ]);
    setTimeout(() => {
      const box = this.consoleBox()?.nativeElement;
      if (box) box.scrollTop = box.scrollHeight;
    }, 0);
  }

  private finish(status: Status): void {
    this.elapsed.set(Math.round(this.elapsed() * 10) / 10);
    this.status.set(status);
    this.activeNode.set(null);
    this.stopTimer();
    this.source?.close();
  }

  runStream(): void {
    if (!this.query().trim()) {
      this.error.set('La consulta no puede estar vacía.');
      return;
    }
    this.reset(true);
    const es = new EventSource(this.api.streamUrl(this.query().trim(), this.maxRev()));
    this.source = es;

    es.addEventListener('start', (raw) => {
      const data = JSON.parse((raw as MessageEvent).data) as {
        query: string;
        mode: string;
        max_revisions: number;
        entry?: string;
      };
      this.activeNode.set(data.entry ?? null);
      this.pushHistory(
        'start',
        `▶ inicio: "${data.query}" (modo ${data.mode}, máx. ${data.max_revisions} revisiones)`,
      );
    });

    es.addEventListener('node', (raw) => {
      const data = JSON.parse((raw as MessageEvent).data) as {
        node: string;
        summary?: string;
        providers_used?: string[];
        snapshot?: StateSnapshot;
      };
      const providers = data.providers_used ?? [];
      this.events.update((list) => [
        ...list,
        {
          node: data.node,
          summary: data.summary ?? data.node,
          provider: providers.length > 0 ? providers[providers.length - 1] : '?',
          at: new Date().toLocaleTimeString(),
        },
      ]);
      if (data.snapshot) this.snapshot.set(data.snapshot);
      this.pushHistory('node', `▸ ${data.node} — ${data.summary ?? ''}`);
    });

    es.addEventListener('route', (raw) => {
      const data = JSON.parse((raw as MessageEvent).data) as {
        from: string;
        to: string;
        detail: string;
      };
      // La ruta anuncia quién EMPIEZA a trabajar ahora (el evento de nodo
      // solo llegará cuando termine, segundos/minutos después en live).
      this.activeNode.set(data.to === 'end' ? null : data.to);
      this.pushHistory('route', `↩ ${data.from} → ${data.to} · ${data.detail}`);
    });

    es.addEventListener('done', (raw) => {
      const r = JSON.parse((raw as MessageEvent).data) as RunResult;
      this.result.set(r);
      this.activeNode.set(null);
      this.snapshot.set(this.snapshotFrom(r));
      this.pushHistory(
        'done',
        `■ fin — ${r.path.length} pasos, ${r.revision_count} revisión(es), informe de ${r.final_report.length} caracteres`,
      );
      this.finish('done');
    });

    es.addEventListener('error', (raw) => {
      const data = (raw as MessageEvent).data;
      const msg = data
        ? String(data)
        : 'La API no responde. Arráncala con: python -m uvicorn api.main:app --port 8000';
      this.error.set(msg);
      this.pushHistory('error', `✖ ${msg}`);
      this.finish('error');
    });

    es.onerror = (): void => {
      if (this.status() === 'running' && !this.result()) {
        const msg =
          'Sin conexión con la API. Arráncala con: python -m uvicorn api.main:app --port 8000';
        this.error.set(msg);
        this.pushHistory('error', `✖ ${msg}`);
        this.finish('error');
      }
    };
  }

  /** Reconstruye el snapshot final desde un RunResponse (modo POST o done). */
  private snapshotFrom(r: RunResult): StateSnapshot {
    return {
      query: r.query,
      research_points: r.research_points,
      draft: r.draft,
      final_report: r.final_report,
      revision_count: r.revision_count,
      needs_revision: false,
      editor_feedback: r.editor_feedback,
      path: r.path,
      providers_used: r.providers_used,
      errors: r.errors,
      current_step: r.current_step,
    };
  }

  async runOnce(): Promise<void> {
    if (!this.query().trim()) {
      this.error.set('La consulta no puede estar vacía.');
      return;
    }
    this.reset(false);
    try {
      const r = await this.api.run(this.query().trim(), this.maxRev());
      this.result.set(r);
      this.snapshot.set(this.snapshotFrom(r));
      this.pushHistory('start', `▶ inicio (modo directo POST): "${r.query}"`);
      for (const node of r.path) this.pushHistory('node', `▸ ${node}`);
      this.pushHistory(
        'done',
        `■ fin — ${r.path.length} pasos, ${r.revision_count} revisión(es), informe de ${r.final_report.length} caracteres`,
      );
      this.finish('done');
    } catch {
      this.error.set(
        'La API no responde o falló. Arráncala con: python -m uvicorn api.main:app --port 8000',
      );
      this.finish('error');
    }
  }
}
