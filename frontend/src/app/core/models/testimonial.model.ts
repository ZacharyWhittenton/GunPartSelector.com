export type TestimonialStatus = 'pending' | 'approved' | 'rejected';

export interface TestimonialSummary {
  id: string;
  customerName: string;
  rating: number;
  body: string;
  createdAt: string;
}

export interface TestimonialDetail extends TestimonialSummary {
  status: TestimonialStatus;
  updatedAt: string;
}
