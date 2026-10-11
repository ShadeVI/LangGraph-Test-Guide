import { Component } from '@angular/core';
import { ProjectSectionComponent } from '../project/project.component';

@Component({
  selector: 'app-page-proyecto',
  imports: [ProjectSectionComponent],
  template: `<app-section-project />`,
})
export class ProyectoPage {}
