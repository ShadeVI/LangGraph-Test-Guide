import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { RevealDirective } from '../shared/reveal.directive';

@Component({
  selector: 'app-hero',
  imports: [RevealDirective],
  template: `
    <section id="inicio" class="hero">
      <div class="container hero-inner">
        <div appReveal>
          <span class="kicker">LangChain · LangGraph · Python</span>
          <h1>
            Pipeline <span class="hl">multi-agente</span> resiliente:<br />
            investiga, redacta y edita
          </h1>
          <p class="lead">
            Tres agentes especializados orquestados por un
            <strong>StateGraph</strong> con fallback automático de proveedores LLM
            (Groq → Gemini → Ollama). Esta página documenta la teoría, la
            arquitectura del proyecto y su guía de uso técnico.
          </p>
          <div class="cta">
            <a class="btn primary" (click)="go('proyecto')">Ver el proyecto</a>
            <a class="btn ghost" (click)="go('uso')">Guía de uso técnico</a>
            <a
              class="btn ghost"
              href="https://github.com/ShadeVI/LangGraph-Test-Guide"
              target="_blank"
              rel="noopener"
              >★ GitHub</a
            >
          </div>
        </div>

        <div class="pipe" appReveal [delay]="150" aria-label="Diagrama del pipeline">
          @for (node of nodes; track node.name; let i = $index) {
            <div class="pipe-node" [style.animation-delay]="i * 0.45 + 's'">
              <span class="pipe-ico">{{ node.icon }}</span>
              <strong>{{ node.name }}</strong>
              <small>{{ node.sub }}</small>
            </div>
            @if (i < nodes.length - 1) {
              <div class="pipe-link" [style.animation-delay]="i * 0.45 + 0.2 + 's'"></div>
            }
          }
        </div>

        <div class="pipe-caption" appReveal [delay]="200">
          ↩ Arista condicional tras el editor: <code>REVISAR → writer</code> (máx. 2 revisiones) ·
          <code>APROBADO → END</code> — el grafo puede ciclar, no es una tubería lineal.
        </div>

        <div class="stats" appReveal [delay]="250">
          @for (stat of stats; track stat.label) {
            <div class="stat">
              <strong>{{ stat.value }}</strong>
              <span>{{ stat.label }}</span>
            </div>
          }
        </div>
      </div>
    </section>
  `,
  styles: [
    `
      .hero { padding: calc(var(--nav-h) + 3.5rem) 0 4rem; }
      .hero h1 { font-size: clamp(2rem, 5vw, 3.2rem); margin: 0 0 1rem; }
      .hero .lead strong { color: var(--text); }
      .cta { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 1.5rem; }
      .cta a { cursor: pointer; }
      .cta a[href] { text-decoration: none; }

      .pipe {
        display: flex;
        align-items: stretch;
        margin-top: 2.75rem;
        background: rgba(8, 13, 29, 0.6);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        padding: 1.25rem;
      }
      .pipe-node {
        flex: 1;
        text-align: center;
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 0.9rem 0.5rem;
        animation: pulseGlow 2.6s ease-in-out infinite;
      }
      .pipe-node strong { display: block; font-size: 0.88rem; }
      .pipe-node small { color: var(--muted); font-size: 0.72rem; font-family: var(--mono); }
      .pipe-ico { font-size: 1.4rem; }
      .pipe-link {
        position: relative;
        flex: 0 0 44px;
        align-self: center;
        height: 3px;
        border-radius: 3px;
        background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent));
        background-size: 200% 100%;
        animation: flow 1.8s linear infinite;
      }
      .pipe-link::after {
        content: '';
        position: absolute;
        top: 50%;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--accent-2);
        translate: 0 -50%;
        animation: travel 1.8s linear infinite;
      }
      @keyframes flow {
        from { background-position: 200% 0; }
        to { background-position: 0 0; }
      }
      @keyframes travel {
        from { left: -4px; opacity: 0; }
        20% { opacity: 1; }
        to { left: calc(100% - 5px); opacity: 0; }
      }

      .pipe-caption {
        margin-top: 0.7rem;
        text-align: center;
        color: var(--muted);
        font-size: 0.85rem;
      }
      .pipe-caption code { font-family: var(--mono); color: var(--accent-2); font-size: 0.8em; }

      .stats {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-top: 1.5rem;
      }
      .stat {
        text-align: center;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 0.9rem 0.5rem;
        background: rgba(124, 157, 255, 0.05);
      }
      .stat strong { display: block; font-size: 1.5rem; color: var(--accent-2); }
      .stat span { color: var(--muted); font-size: 0.8rem; }
      @media (max-width: 860px) {
        .pipe { flex-direction: column; gap: 0.4rem; }
        .pipe-link { flex: none; width: 3px; height: 30px; margin: 0 auto; }
        .pipe-link::after { display: none; }
        .stats { grid-template-columns: repeat(2, 1fr); }
      }
    `,
  ],
})
export class HeroComponent {
  private readonly router = inject(Router);
  readonly nodes = [
    { icon: '❓', name: 'Query', sub: 'input usuario' },
    { icon: '🔍', name: 'Researcher', sub: 'research_points' },
    { icon: '✍️', name: 'Writer', sub: 'draft' },
    { icon: '📝', name: 'Editor', sub: 'final_report' },
  ];

  readonly stats = [
    { value: '3', label: 'agentes + router condicional' },
    { value: '3', label: 'proveedores en fallback' },
    { value: '2', label: 'revisiones máx. (anti-bucle)' },
    { value: '15/15', label: 'tests superados' },
  ];

  go(id: string): void {
    void this.router.navigate([id === 'inicio' ? '/' : `/${id}`]);
  }
}
