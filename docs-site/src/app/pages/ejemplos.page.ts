import { Component } from '@angular/core';
import { ExamplesSectionComponent } from '../examples/examples.component';

@Component({
  selector: 'app-page-ejemplos',
  imports: [ExamplesSectionComponent],
  template: `<app-section-examples />`,
})
export class EjemplosPage {}
