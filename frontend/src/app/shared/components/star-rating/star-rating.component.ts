import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'app-star-rating',
  standalone: true,
  imports: [],
  templateUrl: './star-rating.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './star-rating.component.css'
})
export class StarRatingComponent {
  @Input()
  rating = 0;

  @Input()
  interactive = false;

  @Input()
  size: 'sm' | 'lg' = 'sm';

  @Output()
  ratingChange = new EventEmitter<number>();

  readonly stars = [1, 2, 3, 4, 5];

  hoverRating = 0;

  isFilled(star: number): boolean {
    const active = this.interactive && this.hoverRating > 0 ? this.hoverRating : this.rating;
    return star <= active;
  }

  onStarClick(star: number): void {
    if (!this.interactive) {
      return;
    }
    this.rating = star;
    this.ratingChange.emit(star);
  }

  onStarHover(star: number): void {
    if (this.interactive) {
      this.hoverRating = star;
    }
  }

  onMouseLeave(): void {
    this.hoverRating = 0;
  }
}
