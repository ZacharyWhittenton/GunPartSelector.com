export interface PageViewSummary {
  path: string;
  viewCount: number;
  uniqueSessions: number;
}

export interface ClickPoint {
  xPercent: number;
  yPercent: number;
  elementLabel: string | null;
  createdAt: string;
}
