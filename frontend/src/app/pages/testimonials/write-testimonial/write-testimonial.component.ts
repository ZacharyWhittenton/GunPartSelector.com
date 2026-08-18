import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { TestimonialDetail } from '../../../core/models/testimonial.model';
import { AuthService } from '../../../core/services/auth.service';
import { TestimonialService } from '../../../core/services/testimonial.service';
import { SeoService } from '../../../core/services/seo.service';
import { StarRatingComponent } from '../../../shared/components/star-rating/star-rating.component';

@Component({
  selector: 'app-write-testimonial',
  standalone: true,
  imports: [FormsModule, RouterLink, StarRatingComponent],
  templateUrl: './write-testimonial.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './write-testimonial.component.css'
})
export class WriteTestimonialComponent implements OnInit {
  private readonly testimonialService = inject(TestimonialService);
  private readonly authService = inject(AuthService);
  private readonly seoService = inject(SeoService);

  readonly isAuthenticated = this.authService.isAuthenticated;

  readonly myTestimonial = signal<TestimonialDetail | null>(null);
  readonly isLoading = signal(true);
  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  rating = 0;
  body = '';

  ngOnInit(): void {
    this.seoService.updatePage(
      'Share Your Experience | GunPartSelector.com',
      'Tell us about your experience using GunPartSelector.com to plan your build.'
    );

    if (!this.isAuthenticated) {
      this.isLoading.set(false);
      return;
    }

    this.testimonialService
      .getMine()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: testimonial => {
          if (testimonial) {
            this.myTestimonial.set(testimonial);
            this.rating = testimonial.rating;
            this.body = testimonial.body;
          }
        },
        error: () => this.errorMessage.set('Unable to load your testimonial right now.')
      });
  }

  onRatingChange(rating: number): void {
    this.rating = rating;
  }

  submit(): void {
    this.errorMessage.set('');
    this.successMessage.set('');

    if (this.rating < 1 || this.rating > 5) {
      this.errorMessage.set('Please choose a star rating.');
      return;
    }
    if (!this.body.trim()) {
      this.errorMessage.set('Please write a few words about your experience.');
      return;
    }

    this.isSubmitting.set(true);
    this.testimonialService
      .submitMine({ rating: this.rating, body: this.body.trim() })
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: testimonial => {
          this.myTestimonial.set(testimonial);
          this.successMessage.set(
            'Thanks! Your testimonial has been submitted and is awaiting approval.'
          );
        },
        error: () => this.errorMessage.set('Unable to submit your testimonial. Please try again.')
      });
  }
}
