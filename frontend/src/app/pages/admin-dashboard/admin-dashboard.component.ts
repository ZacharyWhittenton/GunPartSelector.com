import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { DashboardSummary } from '../../core/models/dashboard.model';
import { DashboardAdminService } from '../../core/services/dashboard-admin.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, DatePipe],
  templateUrl: './admin-dashboard.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin-dashboard.component.css'
})
export class AdminDashboardComponent implements OnInit {
  private readonly dashboardAdminService = inject(DashboardAdminService);

  readonly summary = signal<DashboardSummary | null>(null);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  ngOnInit(): void {
    this.loadSummary();
  }

  loadSummary(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.dashboardAdminService
      .getSummary()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: summary => this.summary.set(summary),
        error: () => this.errorMessage.set('Unable to load dashboard data. Please try again.')
      });
  }
}
