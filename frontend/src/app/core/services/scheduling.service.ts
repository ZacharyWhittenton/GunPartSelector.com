import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AppointmentDetail, SlotSummary } from '../models/scheduling.model';

@Injectable({
  providedIn: 'root'
})
export class SchedulingService {
  constructor(private readonly http: HttpClient) {}

  listOpenSlots(): Observable<SlotSummary[]> {
    return this.http.get<SlotSummary[]>('/api/scheduling/slots');
  }

  bookSlot(slotId: string, notes: string | null): Observable<AppointmentDetail> {
    return this.http.post<AppointmentDetail>(`/api/scheduling/slots/${slotId}/book`, { notes });
  }

  listMyAppointments(): Observable<AppointmentDetail[]> {
    return this.http.get<AppointmentDetail[]>('/api/scheduling/appointments/mine');
  }

  cancelMyAppointment(appointmentId: string): Observable<AppointmentDetail> {
    return this.http.post<AppointmentDetail>(
      `/api/scheduling/appointments/${appointmentId}/cancel`,
      {}
    );
  }
}
