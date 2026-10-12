import { Routes } from '@angular/router';
import { InicioPage } from './pages/inicio.page';
import { LangchainPage } from './pages/langchain.page';
import { LanggraphPage } from './pages/langgraph.page';
import { ProyectoPage } from './pages/proyecto.page';
import { UsoPage } from './pages/uso.page';
import { EjemplosPage } from './pages/ejemplos.page';
import { DemoPage } from './demo/demo.component';

export const routes: Routes = [
  { path: '', component: InicioPage, title: 'Inicio · Multi-Agente Docs' },
  { path: 'langchain', component: LangchainPage, title: 'LangChain · Multi-Agente Docs' },
  { path: 'langgraph', component: LanggraphPage, title: 'LangGraph · Multi-Agente Docs' },
  { path: 'proyecto', component: ProyectoPage, title: 'El proyecto · Multi-Agente Docs' },
  { path: 'uso', component: UsoPage, title: 'Guía de uso · Multi-Agente Docs' },
  { path: 'ejemplos', component: EjemplosPage, title: 'Ejemplos · Multi-Agente Docs' },
  { path: 'demo', component: DemoPage, title: 'Demo en vivo · Multi-Agente Docs' },
  { path: '**', redirectTo: '' },
];
