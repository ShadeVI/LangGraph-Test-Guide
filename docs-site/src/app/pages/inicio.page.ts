import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { HeroComponent } from '../hero/hero.component';
import { RevealDirective } from '../shared/reveal.directive';

@Component({
  selector: 'app-page-inicio',
  imports: [HeroComponent, RouterLink, RevealDirective],
  template: `
    <app-hero />
    <section class="section">
      <div class="container">
        <div appReveal>
          <span class="kicker">Explora la documentación</span>
          <h2>Cada tema, en su propia página</h2>
        </div>
        <div class="grid3">
          @for (card of cards; track card.path; let i = $index) {
            <a class="card link-card" [routerLink]="card.path" appReveal [delay]="i * 80">
              <div class="ico">{{ card.icon }}</div>
              <h3>{{ card.title }}</h3>
              <p>{{ card.text }}</p>
              <span class="go">Abrir →</span>
            </a>
          }
        </div>
      </div>
    </section>
  `,
  styles: [
    `
      .link-card { text-decoration: none; display: block; }
      .link-card .go { color: var(--accent-2); font-weight: 700; font-size: 0.86rem; }
    `,
  ],
})
export class InicioPage {
  readonly cards = [
    { icon: '🧠', path: '/langchain', title: 'LangChain', text: 'Framework para apps con LLMs: modelos, prompts, cadenas y herramientas.' },
    { icon: '🕸️', path: '/langgraph', title: 'LangGraph', text: 'Orquestación como grafos de estado: nodos, aristas, ciclos y memoria.' },
    { icon: '🏗️', path: '/proyecto', title: 'El proyecto', text: 'Pipeline, decisiones de arquitectura y protocolo MCP, todo en un sitio.' },
    { icon: '📖', path: '/uso', title: 'Guía de uso', text: 'Instalación, .env, CLI y uso como librería.' },
    { icon: '🔬', path: '/demo', title: 'Demo en vivo', text: 'Ejecuta los agentes de verdad contra la API y míralos trabajar nodo a nodo.' },
  ];
}
