import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';

import { TestimonialSummary } from '../../../core/models/testimonial.model';
import { TestimonialService } from '../../../core/services/testimonial.service';
import { StarRatingComponent } from '../star-rating/star-rating.component';

const ROTATE_INTERVAL_MS = 6000;
const MAX_TESTIMONIALS = 10;

@Component({
  selector: 'app-testimonial-carousel',
  standalone: true,
  imports: [StarRatingComponent],
  templateUrl: './testimonial-carousel.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './testimonial-carousel.component.css'
})
export class TestimonialCarouselComponent implements OnInit, OnDestroy {
  private readonly testimonialService = inject(TestimonialService);

  readonly testimonials = signal<TestimonialSummary[]>([]);
  readonly currentIndex = signal(0);

  private rotateHandle: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.testimonialService.listApproved(MAX_TESTIMONIALS).subscribe(testimonials => {
      this.testimonials.set(testimonials);
      if (testimonials.length > 1) {
        this.rotateHandle = setInterval(() => this.next(), ROTATE_INTERVAL_MS);
      }
    });
  }

  ngOnDestroy(): void {
    if (this.rotateHandle) {
      clearInterval(this.rotateHandle);
    }
  }

  next(): void {
    const total = this.testimonials().length;
    if (total === 0) {
      return;
    }
    this.currentIndex.update(index => (index + 1) % total);
  }

  goTo(index: number): void {
    this.currentIndex.set(index);
  }
}
