import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AppointmentDetail, AppointmentStatus } from '../models/scheduling.model';

export interface CreateSlotPayload {
  startsAt: string;
  endsAt: string;
}

@Injectable({
  providedIn: 'root'
})
export class SchedulingAdminService {
  constructor(private readonly http: HttpClient) {}

  createSlot(payload: CreateSlotPayload): Observable<AppointmentDetail> {
    return this.http.post<AppointmentDetail>('/api/admin/scheduling/slots', payload);
  }

  listAllAppointments(status?: AppointmentStatus): Observable<AppointmentDetail[]> {
    const url = status
      ? `/api/admin/scheduling/appointments?status=${status}`
      : '/api/admin/scheduling/appointments';
    return this.http.get<AppointmentDetail[]>(url);
  }

  cancelAppointment(appointmentId: string): Observable<AppointmentDetail> {
    return this.http.post<AppointmentDetail>(
      `/api/admin/scheduling/appointments/${appointmentId}/cancel`,
      {}
    );
  }

  deleteSlot(slotId: string): Observable<void> {
    return this.http.delete<void>(`/api/admin/scheduling/slots/${slotId}`);
  }
}
