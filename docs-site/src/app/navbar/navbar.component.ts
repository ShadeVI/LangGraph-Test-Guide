import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { signal } from '@angular/core';

interface NavLink {
  path: string;
  label: string;
  exact?: boolean;
  demo?: boolean;
}

@Component({
  selector: 'app-navbar',
  imports: [RouterLink, RouterLinkActive],
  template: `
    <header class="nav" [class.scrolled]="scrolled()">
      <div class="container nav-inner">
        <a class="brand" routerLink="/" title="Ir al inicio">
          <span class="brand-mark">◈</span>
          <span class="brand-text">Multi-Agente <em>Docs</em></span>
        </a>
        <nav class="links" [class.open]="open()">
          @for (link of links; track link.path) {
            <a
              [routerLink]="link.path"
              routerLinkActive="active"
              [routerLinkActiveOptions]="{ exact: link.exact ?? false }"
              [class.demo-link]="link.demo"
              (click)="open.set(false)"
              >{{ link.label }}</a
            >
          }
        </nav>
        <button class="burger" (click)="open.set(!open())" aria-label="Abrir menú">
          <span></span><span></span><span></span>
        </button>
      </div>
    </header>
  `,
  styles: [
    `
      .nav {
        position: fixed;
        inset: 0 0 auto 0;
        height: var(--nav-h);
        z-index: 50;
        backdrop-filter: blur(12px);
        background: rgba(11, 16, 32, 0.72);
        border-bottom: 1px solid transparent;
        transition: border-color 0.3s ease, background 0.3s ease;
      }
      .nav.scrolled {
        border-bottom-color: var(--line);
        background: rgba(11, 16, 32, 0.92);
      }
      .nav-inner {
        height: var(--nav-h);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
      }
      .brand {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        cursor: pointer;
        text-decoration: none;
        color: var(--text);
        font-weight: 800;
        white-space: nowrap;
      }
      .brand-mark {
        display: grid;
        place-items: center;
        width: 32px;
        height: 32px;
        border-radius: 9px;
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        color: #060a18;
        animation: pulseGlow 3s ease-in-out infinite;
      }
      .brand-text em { font-style: normal; color: var(--accent-2); }
      .links { display: flex; gap: 0.15rem; align-items: center; }
      .links a {
        position: relative;
        cursor: pointer;
        text-decoration: none;
        color: var(--muted);
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.5rem 0.55rem;
        border-radius: 8px;
        white-space: nowrap;
        transition: color 0.2s ease, background 0.2s ease;
      }
      .links a:hover { color: var(--text); background: rgba(124, 157, 255, 0.1); }
      .links a::after {
        content: '';
        position: absolute;
        left: 0.7rem;
        right: 0.7rem;
        bottom: 2px;
        height: 2px;
        border-radius: 2px;
        background: var(--accent-2);
        scale: 0 1;
        transition: scale 0.25s ease;
        transform-origin: left;
      }
      .links a.active { color: var(--text); }
      .links a.active::after { scale: 1 1; }
      .links a.demo-link {
        border: 1px solid rgba(94, 234, 212, 0.45);
        color: var(--accent-2);
        margin-left: 0.4rem;
      }
      .links a.demo-link::after { display: none; }
      .links a.demo-link:hover, .links a.demo-link.active {
        background: rgba(94, 234, 212, 0.12);
        color: var(--accent-2);
      }
      .burger {
        display: none;
        flex-direction: column;
        gap: 5px;
        background: none;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.55rem;
        cursor: pointer;
      }
      .burger span { width: 20px; height: 2px; background: var(--text); border-radius: 2px; }
      @media (max-width: 1220px) {
        .burger { display: flex; }
        .links {
          position: absolute;
          top: var(--nav-h);
          left: 0;
          right: 0;
          flex-direction: column;
          align-items: stretch;
          background: rgba(11, 16, 32, 0.97);
          border-bottom: 1px solid var(--line);
          padding: 0.6rem 1.25rem 1rem;
          display: none;
        }
        .links.open { display: flex; animation: fadeSlideIn 0.3s ease; }
        .links a.demo-link { margin-left: 0; text-align: center; }
      }
    `,
  ],
})
export class NavbarComponent {
  readonly links: NavLink[] = [
    { path: '/', label: 'Inicio', exact: true },
    { path: '/langchain', label: 'LangChain' },
    { path: '/langgraph', label: 'LangGraph' },
    { path: '/proyecto', label: 'El proyecto' },
    { path: '/por-que', label: '¿Por qué LangGraph?' },
    { path: '/mcp', label: '¿Por qué MCP?' },
    { path: '/uso', label: 'Guía de uso' },
    { path: '/ejemplos', label: 'Ejemplos' },
    { path: '/demo', label: '▶ Demo en vivo', demo: true },
  ];

  readonly open = signal(false);
  readonly scrolled = signal(false);

  constructor() {
    window.addEventListener('scroll', () => this.scrolled.set(window.scrollY > 12), {
      passive: true,
    });
  }
}
