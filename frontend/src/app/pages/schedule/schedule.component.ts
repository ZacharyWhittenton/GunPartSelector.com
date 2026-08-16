import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AppointmentDetail, SlotSummary } from '../../core/models/scheduling.model';
import { AuthService } from '../../core/services/auth.service';
import { SchedulingService } from '../../core/services/scheduling.service';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-schedule',
  standalone: true,
  imports: [FormsModule, DatePipe, RouterLink],
  templateUrl: './schedule.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './schedule.component.css'
})
export class ScheduleComponent implements OnInit {
  private readonly schedulingService = inject(SchedulingService);
  private readonly authService = inject(AuthService);
  private readonly seoService = inject(SeoService);

  readonly isAuthenticated = this.authService.isAuthenticated;

  readonly openSlots = signal<SlotSummary[]>([]);
  readonly isLoadingSlots = signal(false);
  readonly slotsError = signal('');

  readonly myAppointments = signal<AppointmentDetail[]>([]);
  readonly isLoadingAppointments = signal(false);
  readonly appointmentsError = signal('');

  readonly selectedSlotId = signal<string | null>(null);
  readonly isBooking = signal(false);
  readonly bookingError = signal('');
  bookingNotes = '';

  readonly pendingAppointmentIds = signal<Set<string>>(new Set());

  ngOnInit(): void {
    this.seoService.updatePage(
      'Schedule a Consultation | WD Web Solutions',
      'Book a free consultation with WD Web Solutions to discuss your website design or development project.'
    );

    this.loadOpenSlots();
    if (this.isAuthenticated) {
      this.loadMyAppointments();
    }
  }

  loadOpenSlots(): void {
    this.isLoadingSlots.set(true);
    this.slotsError.set('');

    this.schedulingService
      .listOpenSlots()
      .pipe(finalize(() => this.isLoadingSlots.set(false)))
      .subscribe({
        next: slots => this.openSlots.set(slots),
        error: () => this.slotsError.set('Unable to load available times. Please try again.')
      });
  }

  loadMyAppointments(): void {
    this.isLoadingAppointments.set(true);
    this.appointmentsError.set('');

    this.schedulingService
      .listMyAppointments()
      .pipe(finalize(() => this.isLoadingAppointments.set(false)))
      .subscribe({
        next: appointments => this.myAppointments.set(appointments),
        error: () => this.appointmentsError.set('Unable to load your appointments.')
      });
  }

  selectSlot(slot: SlotSummary): void {
    this.bookingError.set('');
    this.bookingNotes = '';
    this.selectedSlotId.set(this.selectedSlotId() === slot.id ? null : slot.id);
  }

  confirmBooking(slotId: string): void {
    this.isBooking.set(true);
    this.bookingError.set('');

    this.schedulingService
      .bookSlot(slotId, this.bookingNotes.trim() || null)
      .pipe(finalize(() => this.isBooking.set(false)))
      .subscribe({
        next: appointment => {
          this.openSlots.update(slots => slots.filter(slot => slot.id !== slotId));
          this.myAppointments.update(appointments => [appointment, ...appointments]);
          this.selectedSlotId.set(null);
          this.bookingNotes = '';
        },
        error: error => {
          this.bookingError.set(
            error.status === 409
              ? 'That time was just booked by someone else. Please choose another.'
              : 'Unable to book that time. Please try again.'
          );
        }
      });
  }

  cancelAppointment(appointment: AppointmentDetail): void {
    this.pendingAppointmentIds.update(pending => new Set(pending).add(appointment.id));

    this.schedulingService
      .cancelMyAppointment(appointment.id)
      .pipe(
        finalize(() => {
          this.pendingAppointmentIds.update(pending => {
            const next = new Set(pending);
            next.delete(appointment.id);
            return next;
          });
        })
      )
      .subscribe({
        next: updated => {
          this.myAppointments.update(appointments =>
            appointments.map(existing => (existing.id === updated.id ? updated : existing))
          );
        },
        error: () => this.appointmentsError.set('Unable to cancel that appointment.')
      });
  }

  isPendingCancel(appointmentId: string): boolean {
    return this.pendingAppointmentIds().has(appointmentId);
  }

  get upcomingAppointments(): AppointmentDetail[] {
    return this.myAppointments().filter(appointment => appointment.status !== 'cancelled');
  }
}
