import { Component } from '@angular/core';
import { LangchainSectionComponent } from '../langchain/langchain.component';

@Component({
  selector: 'app-page-langchain',
  imports: [LangchainSectionComponent],
  template: `<app-section-langchain />`,
})
export class LangchainPage {}
