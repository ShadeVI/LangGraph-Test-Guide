import { Component } from '@angular/core';

@Component({
  selector: 'app-footer',
  template: `
    <footer class="footer">
      <div class="container foot-inner">
        <div>
          <strong>◈ Multi-Agente Docs</strong>
          <p>
            Documentación del pipeline Analizador → Sintetizador → Reviewer
            (LangChain + LangGraph · Groq → Gemini → Ollama).
          </p>
        </div>
        <div class="foot-links">
          <span>Proyecto: <code>python-langGraph</code></span>
          <a href="https://github.com/ShadeVI/LangGraph-Test-Guide" target="_blank" rel="noopener"
            >★ Ver en GitHub</a
          >
        </div>
      </div>
    </footer>
  `,
  styles: [
    `
      .footer {
        border-top: 1px solid var(--line);
        margin-top: 2rem;
        background: rgba(8, 13, 29, 0.7);
      }
      .foot-inner {
        display: flex;
        justify-content: space-between;
        gap: 1.5rem;
        flex-wrap: wrap;
        padding-top: 2rem;
        padding-bottom: 2rem;
      }
      .foot-inner p { color: var(--muted); font-size: 0.86rem; margin: 0.3rem 0 0; max-width: 52ch; }
      .foot-links { display: grid; gap: 0.3rem; color: var(--muted); font-size: 0.82rem; align-content: start; }
      .foot-links a { color: var(--accent-2); text-decoration: none; font-weight: 700; }
      .foot-links a:hover { text-decoration: underline; }
      code { font-family: var(--mono); color: var(--accent-2); }
    `,
  ],
})
export class FooterComponent {}
