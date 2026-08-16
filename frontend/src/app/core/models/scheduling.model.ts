export type AppointmentStatus = 'open' | 'booked' | 'cancelled';

export interface SlotSummary {
  id: string;
  startsAt: string;
  endsAt: string;
}

export interface AppointmentDetail {
  id: string;
  startsAt: string;
  endsAt: string;
  status: AppointmentStatus;
  clientId: string | null;
  clientName: string | null;
  clientEmail: string | null;
  notes: string | null;
  createdByAdminId: string;
  createdAt: string;
  updatedAt: string;
}
