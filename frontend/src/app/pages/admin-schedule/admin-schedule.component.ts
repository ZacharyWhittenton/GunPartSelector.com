import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, finalize } from 'rxjs';

import { AppointmentDetail, AppointmentStatus } from '../../core/models/scheduling.model';
import { SchedulingAdminService } from '../../core/services/scheduling-admin.service';

@Component({
  selector: 'app-admin-schedule',
  standalone: true,
  imports: [FormsModule, DatePipe, RouterLink],
  templateUrl: './admin-schedule.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin-schedule.component.css'
})
export class AdminScheduleComponent implements OnInit {
  private readonly schedulingAdminService = inject(SchedulingAdminService);

  readonly appointments = signal<AppointmentDetail[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly statusFilter = signal<AppointmentStatus | ''>('');
  readonly statusOptions: (AppointmentStatus | '')[] = ['', 'open', 'booked', 'cancelled'];

  readonly pendingIds = signal<Set<string>>(new Set());
  readonly rowErrors = signal<Record<string, string>>({});

  readonly isCreating = signal(false);
  readonly createError = signal('');
  newSlotStartsAt = '';
  newSlotEndsAt = '';

  ngOnInit(): void {
    this.loadAppointments();
  }

  loadAppointments(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    const status = this.statusFilter() || undefined;

    this.schedulingAdminService
      .listAllAppointments(status)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: appointments => this.appointments.set(appointments),
        error: () => this.errorMessage.set('Unable to load appointments. Please try again.')
      });
  }

  onFilterChange(status: AppointmentStatus | ''): void {
    this.statusFilter.set(status);
    this.loadAppointments();
  }

  submitCreateSlot(): void {
    this.createError.set('');

    if (!this.newSlotStartsAt || !this.newSlotEndsAt) {
      this.createError.set('Start and end times are required.');
      return;
    }

    const startsAt = new Date(this.newSlotStartsAt);
    const endsAt = new Date(this.newSlotEndsAt);

    if (endsAt <= startsAt) {
      this.createError.set('End time must be after the start time.');
      return;
    }

    this.isCreating.set(true);

    this.schedulingAdminService
      .createSlot({ startsAt: startsAt.toISOString(), endsAt: endsAt.toISOString() })
      .pipe(finalize(() => this.isCreating.set(false)))
      .subscribe({
        next: () => {
          this.newSlotStartsAt = '';
          this.newSlotEndsAt = '';
          this.loadAppointments();
        },
        error: error => {
          this.createError.set(
            error.status === 409
              ? 'Slot start time must be in the future.'
              : 'Unable to create that slot. Please try again.'
          );
        }
      });
  }

  cancelAppointment(appointment: AppointmentDetail): void {
    this.runRowAction(appointment.id, () =>
      this.schedulingAdminService.cancelAppointment(appointment.id)
    );
  }

  deleteSlot(appointment: AppointmentDetail): void {
    if (!confirm('Delete this open slot? This cannot be undone.')) {
      return;
    }

    this.setRowError(appointment.id, '');
    this.pendingIds.update(pending => new Set(pending).add(appointment.id));

    this.schedulingAdminService
      .deleteSlot(appointment.id)
      .pipe(
        finalize(() => {
          this.pendingIds.update(pending => {
            const next = new Set(pending);
            next.delete(appointment.id);
            return next;
          });
        })
      )
      .subscribe({
        next: () => {
          this.appointments.update(appointments =>
            appointments.filter(existing => existing.id !== appointment.id)
          );
        },
        error: () =>
          this.setRowError(appointment.id, 'Only open slots can be deleted; cancel it instead.')
      });
  }

  isPending(appointmentId: string): boolean {
    return this.pendingIds().has(appointmentId);
  }

  rowError(appointmentId: string): string {
    return this.rowErrors()[appointmentId] ?? '';
  }

  private runRowAction(
    appointmentId: string,
    action: () => Observable<AppointmentDetail>
  ): void {
    this.setRowError(appointmentId, '');
    this.pendingIds.update(pending => new Set(pending).add(appointmentId));

    action()
      .pipe(
        finalize(() => {
          this.pendingIds.update(pending => {
            const next = new Set(pending);
            next.delete(appointmentId);
            return next;
          });
        })
      )
      .subscribe({
        next: updated => {
          this.appointments.update(appointments =>
            appointments.map(existing => (existing.id === updated.id ? updated : existing))
          );
        },
        error: () => this.setRowError(appointmentId, 'That action failed. Please try again.')
      });
  }

  private setRowError(appointmentId: string, message: string): void {
    this.rowErrors.update(errors => ({ ...errors, [appointmentId]: message }));
  }
}
