import { Component } from '@angular/core';
import { RevealDirective } from '../shared/reveal.directive';

@Component({
  selector: 'app-section-langchain',
  imports: [RevealDirective],
  template: `
    <section id="langchain" class="section">
      <div class="container">
        <div appReveal>
          <span class="kicker">01 · Fundamento</span>
          <h2>¿Qué es <span class="hl">LangChain</span>?</h2>
          <p class="lead">
            LangChain es un <strong>framework de código abierto</strong> para construir
            aplicaciones con modelos de lenguaje (LLM). Resuelve el problema de pasar del
            "prompt suelto en un chat" a <strong>software real</strong>: componer llamadas,
            conectar datos propios, usar herramientas y encadenar pasos de forma
            reproducible y testeable.
          </p>
        </div>

        <div class="grid3">
          @for (c of blocks; track c.title; let i = $index) {
            <div class="card" appReveal [delay]="i * 90">
              <div class="ico">{{ c.icon }}</div>
              <h3>{{ c.title }}</h3>
              <p>{{ c.text }}</p>
              @for (t of c.tags; track t) {
                <span class="tag">{{ t }}</span>
              }
            </div>
          }
        </div>

        <div class="grid2" style="margin-top: 1rem">
          <div appReveal>
            <h3>¿Cómo funciona? El patrón en 4 pasos</h3>
            <ol class="steps">
              @for (s of steps; track s.title; let i = $index) {
                <li appReveal [delay]="i * 80">
                  <strong>{{ i + 1 }}. {{ s.title }}</strong>
                  <span>{{ s.text }}</span>
                </li>
              }
            </ol>
          </div>
          <div appReveal [delay]="120">
            <h3>¿Por qué usarlo?</h3>
            <div class="callout ok">
              <strong>Sin LangChain:</strong> prompts hardcodeados, reintentos manuales,
              parsing frágil con <code>split()</code> y cada proveedor con un SDK distinto.
            </div>
            <div class="callout">
              <strong>Con LangChain:</strong> interfaz única (<code>ChatModel.invoke()</code>)
              para Groq, Gemini, Ollama y decenas más; prompts versionables, salidas
              estructuradas y cadenas componibles con LCEL (<code>prompt | model | parser</code>).
            </div>
            <p class="lead" style="font-size: 0.95rem">
              En este proyecto, LangChain aporta justo eso: la
              <strong>capa de acceso uniforme a los LLM</strong> que permite el fallback
              Groq → Gemini → Ollama sin cambiar ni una línea de los agentes.
            </p>
          </div>
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
export class LangchainSectionComponent {
  readonly blocks = [
    {
      icon: '🧠',
      title: 'Modelos (I/O unificado)',
      text: 'Una misma interfaz ChatModel para llamar a cualquier proveedor. Cambiar de Groq a Gemini es cambiar una clase, no tu lógica.',
      tags: ['ChatGroq', 'ChatGoogleGenerativeAI', 'ChatOllama'],
    },
    {
      icon: '🧩',
      title: 'Prompts y parsers',
      text: 'Plantillas reutilizables y parsers que convierten la respuesta libre del LLM en datos estructurados (listas, JSON, objetos).',
      tags: ['PromptTemplate', 'OutputParser'],
    },
    {
      icon: '🔗',
      title: 'Cadenas (LCEL)',
      text: 'Composición declarativa con el operador pipe: prompt | modelo | parser. Cada eslabón es testeable por separado.',
      tags: ['LCEL', 'Runnable'],
    },
    {
      icon: '🛠️',
      title: 'Herramientas y agentes',
      text: 'El modelo puede decidir llamar a funciones externas (búsqueda, APIs, código) y usar el resultado para continuar razonando.',
      tags: ['Tools', 'Agents'],
    },
    {
      icon: '📚',
      title: 'Datos propios (RAG)',
      text: 'Conecta embeddings y bases vectoriales para que el modelo responda con tu documentación, no solo con su entrenamiento.',
      tags: ['Embeddings', 'VectorStore'],
    },
    {
      icon: '🔭',
      title: 'Observabilidad',
      text: 'Traza cada llamada (LangSmith) para depurar prompts, costes y latencias en producción.',
      tags: ['LangSmith', 'Callbacks'],
    },
  ];

  readonly steps = [
    { title: 'Entrada estructurada', text: 'El prompt template recibe variables y genera la instrucción final.' },
    { title: 'Invocación al modelo', text: 'ChatModel.invoke() envía la instrucción al proveedor configurado.' },
    { title: 'Salida parseada', text: 'El parser convierte texto libre en datos tipados que tu código entiende.' },
    { title: 'Composición', text: 'Los runnables se encadenan y reutilizan como piezas de LEGO tipadas.' },
  ];
}
