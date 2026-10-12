import { Component } from '@angular/core';
import { RevealDirective } from '../shared/reveal.directive';

@Component({
  selector: 'app-section-why',
  imports: [RevealDirective],
  template: `
    <section id="por-que" class="section alt">
      <div class="container">
        <div appReveal>
          <span class="kicker">04 · Decisión de arquitectura</span>
          <h2>¿Por qué se usó <span class="hl">LangGraph</span>?</h2>
          <p class="lead">
            El problema encaja con la definición de LangGraph: un flujo por
            <strong>fases con estado acumulativo</strong> donde cada fase la ejecuta un
            especialista distinto. Estas son las razones concretas, trazables al código:
          </p>
        </div>
        <div class="grid2">
          @for (r of reasons; track r.title; let i = $index) {
            <div class="card" appReveal [delay]="(i % 2) * 100">
              <h3>{{ r.icon }} {{ r.title }}</h3>
              <p>{{ r.text }}</p>
              <span class="tag">{{ r.code }}</span>
            </div>
          }
        </div>
        <div class="callout ok" appReveal>
          <strong>En una frase:</strong> LangChain nos da los <em>proveedores LLM
          intercambiables</em>; LangGraph nos da el <em>flujo multi-agente observable y
          determinista</em>. Uno sin el otro dejaría el sistema cojo: sin LangChain no hay
          fallback limpio; sin LangGraph no hay orquestación auditable.
        </div>
      </div>
    </section>
  `,
  styles: [],
})
export class WhySectionComponent {
  readonly reasons = [
    {
      icon: '📦',
      title: 'Estado compartido y tipado',
      text: 'GraphState es el único contrato entre agentes. Añadir una fase nueva (p. ej. "fact-checker") es añadir un nodo que lea y escriba campos, sin tocar a los demás.',
      code: 'src/state.py',
    },
    {
      icon: '🔭',
      title: 'Observabilidad por nodo',
      text: 'Cada nodo registra inicio, fin, proveedor ganador y fallos recuperados. El estado final incluye providers_used y errors: auditoría completa del pipeline.',
      code: 'BaseAgent.run() + logging',
    },
    {
      icon: '🧪',
      title: 'Testabilidad del flujo',
      text: 'Los nodos son funciones puras estado → patch. Con un LLM de mentira se verifica el grafo entero sin red ni API keys: 6/6 tests en milisegundos.',
      code: 'tests/test_pipeline.py',
    },
    {
      icon: '🧩',
      title: 'Separación de incumbencias',
      text: 'Un agente, una responsabilidad. El analizador no sabe sintetizar y el revisor no investiga: cada prompt es corto, enfocado y fácil de mejorar.',
      code: 'src/agents/ (SRP)',
    },
    {
      icon: '🛡️',
      title: 'Resiliencia sin enredar el flujo',
      text: 'El fallback vive dentro del cliente LLM, no en el grafo. El grafo siempre ve "texto generado"; quién lo generó es un detalle encapsulado.',
      code: 'ResilientLLMClient',
    },
    {
      icon: '🚀',
      title: 'Evolución futura barata',
      text: 'Mañana se puede añadir una arista condicional (reintentar el draft si el revisor lo rechaza) o streaming por nodo sin reescribir nada existente.',
      code: 'src/graph/builder.py',
    },
  ];
}
