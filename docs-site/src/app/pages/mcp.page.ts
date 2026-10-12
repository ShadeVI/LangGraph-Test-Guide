import { Component } from '@angular/core';
import { McpSectionComponent } from '../mcp/mcp.component';

@Component({
  selector: 'app-page-mcp',
  imports: [McpSectionComponent],
  template: `<app-section-mcp />`,
})
export class McpPage {}
