import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

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

export interface FinanceResult {
  filename: string;
  used_mock: boolean;
  mode: string;
  kind: string;
  row_count: number;
  totals: Record<string, Record<string, number>>;
  fx_rate: number | null;
  fx_date: string;
  fx_source: string;
  fx_stale: boolean;
  budget_alerts: string[];
  findings: string[];
  final_report: string;
  path: string[];
  providers_used: string[];
  errors: string[];
  tool_iterations: number;
  current_step: string;
}

export interface FinanceSnapshot {
  kind: 'finance';
  filename: string;
  row_count: number;
  totals: Record<string, Record<string, number>>;
  fx_rate: number | null;
  fx_date: string;
  alerts: string[];
  findings: string[];
  path: string[];
  providers_used: string[];
  errors: string[];
  current_step: string;
}

/** Cliente HTTP de la API FastAPI (por defecto, uvicorn local). */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  /** Base editable desde la UI (útil si la API corre en otro host/puerto). */
  readonly baseUrl = signal('http://localhost:8000');

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

  analyzeFinance(file: File | null): Promise<FinanceResult> {
    const data = new FormData();
    if (file) data.append('file', file, file.name);
    return firstValueFrom(this.http.post<FinanceResult>(`${this.baseUrl()}/api/finance/run`, data));
  }

  uploadFinanceJob(file: File | null): Promise<{ job_id: string }> {
    const data = new FormData();
    if (file) data.append('file', file, file.name);
    return firstValueFrom(this.http.post<{ job_id: string }>(`${this.baseUrl()}/api/finance/jobs`, data));
  }

  financeStreamUrl(jobId: string): string {
    return `${this.baseUrl()}/api/finance/stream?job_id=${encodeURIComponent(jobId)}`;
  }
}
