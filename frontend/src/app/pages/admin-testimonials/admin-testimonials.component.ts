import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { Observable, finalize } from 'rxjs';

import { TestimonialDetail, TestimonialStatus } from '../../core/models/testimonial.model';
import { TestimonialAdminService } from '../../core/services/testimonial-admin.service';
import { StarRatingComponent } from '../../shared/components/star-rating/star-rating.component';

@Component({
  selector: 'app-admin-testimonials',
  standalone: true,
  imports: [DatePipe, StarRatingComponent],
  templateUrl: './admin-testimonials.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin-testimonials.component.css'
})
export class AdminTestimonialsComponent implements OnInit {
  private readonly testimonialAdminService = inject(TestimonialAdminService);

  readonly testimonials = signal<TestimonialDetail[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly statusFilter = signal<TestimonialStatus | ''>('pending');
  readonly statusOptions: (TestimonialStatus | '')[] = ['pending', 'approved', 'rejected', ''];
  readonly pendingActionIds = signal<Set<string>>(new Set());

  ngOnInit(): void {
    this.loadTestimonials();
  }

  loadTestimonials(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    const status = this.statusFilter() || undefined;

    this.testimonialAdminService
      .listAll(status)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: testimonials => this.testimonials.set(testimonials),
        error: () => this.errorMessage.set('Unable to load testimonials. Please try again.')
      });
  }

  onFilterChange(status: TestimonialStatus | ''): void {
    this.statusFilter.set(status);
    this.loadTestimonials();
  }

  approve(testimonial: TestimonialDetail): void {
    this.runAction(testimonial.id, this.testimonialAdminService.approve(testimonial.id));
  }

  reject(testimonial: TestimonialDetail): void {
    this.runAction(testimonial.id, this.testimonialAdminService.reject(testimonial.id));
  }

  remove(testimonial: TestimonialDetail): void {
    if (!confirm(`Delete the testimonial from ${testimonial.customerName}? This can't be undone.`)) {
      return;
    }

    this.markPending(testimonial.id);
    this.testimonialAdminService
      .delete(testimonial.id)
      .pipe(finalize(() => this.clearPending(testimonial.id)))
      .subscribe({
        next: () => {
          this.testimonials.update(items => items.filter(item => item.id !== testimonial.id));
        },
        error: () => this.errorMessage.set('Unable to delete that testimonial.')
      });
  }

  isPending(id: string): boolean {
    return this.pendingActionIds().has(id);
  }

  private runAction(id: string, action: Observable<TestimonialDetail>): void {
    this.markPending(id);
    action.pipe(finalize(() => this.clearPending(id))).subscribe({
      next: updated => {
        this.testimonials.update(items =>
          items.map(item => (item.id === updated.id ? updated : item))
        );
      },
      error: () => this.errorMessage.set('Unable to update that testimonial.')
    });
  }

  private markPending(id: string): void {
    this.pendingActionIds.update(pending => new Set(pending).add(id));
  }

  private clearPending(id: string): void {
    this.pendingActionIds.update(pending => {
      const next = new Set(pending);
      next.delete(id);
      return next;
    });
  }
}
