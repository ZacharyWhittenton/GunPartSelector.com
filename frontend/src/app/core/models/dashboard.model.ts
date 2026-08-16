export type ActivityType = 'lead' | 'appointment' | 'order';

export interface ActivityItem {
  activityType: ActivityType;
  id: string;
  label: string;
  occurredAt: string;
}

export interface DashboardSummary {
  newLeadsToday: number;
  newLeadsThisWeek: number;
  upcomingAppointments: number;
  revenueThisWeekCents: number;
  revenueThisMonthCents: number;
  pendingTestimonials: number;
  leadsNeedingFollowUp: number;
  recentActivity: ActivityItem[];
}
