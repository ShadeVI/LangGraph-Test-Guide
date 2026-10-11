import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';

export interface HealthStatus {
  status: string;
  mode: string;
}

export interface RunResult {
  query: string;
  mode: string;
  final_report: string;
  path: string[];
  providers_used: string[];
  errors: string[];
  revision_count: number;
  current_step: string;
  editor_feedback: string;
  research_points: string[];
  draft: string;
}

export interface StateSnapshot {
  query: string;
  research_points: string[];
  draft: string;
  final_report: string;
  revision_count: number;
  needs_revision: boolean | null;
  editor_feedback: string;
  path: string[];
  providers_used: string[];
  errors: string[];
  current_step: string;
}

/** Cliente HTTP de la API FastAPI (por defecto, uvicorn local). */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  /** Base editable desde la UI (en prod apunta al backend desplegado). */
  readonly baseUrl = signal(environment.apiBaseUrl);

  health(): Promise<HealthStatus> {
    return firstValueFrom(this.http.get<HealthStatus>(`${this.baseUrl()}/api/health`));
  }

  run(query: string, maxRevisions: number): Promise<RunResult> {
    return firstValueFrom(
      this.http.post<RunResult>(`${this.baseUrl()}/api/run`, {
        query,
        max_revisions: maxRevisions,
      }),
    );
  }

  streamUrl(query: string, maxRevisions: number): string {
    return (
      `${this.baseUrl()}/api/run/stream` +
      `?query=${encodeURIComponent(query)}&max_revisions=${maxRevisions}`
    );
  }
}
