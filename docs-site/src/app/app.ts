import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from './navbar/navbar.component';
import { HeroComponent } from './hero/hero.component';
import { LangchainSectionComponent } from './langchain/langchain.component';
import { LanggraphSectionComponent } from './langgraph/langgraph.component';
import { ProjectSectionComponent } from './project/project.component';
import { WhySectionComponent } from './why/why.component';
import { UsageSectionComponent } from './usage/usage.component';
import { ExamplesSectionComponent } from './examples/examples.component';
import { FooterComponent } from './footer/footer.component';

@Component({
  imports: [
    RouterOutlet,
    NavbarComponent,
    FooterComponent,
  ],
  selector: 'app-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})
export class App {}
