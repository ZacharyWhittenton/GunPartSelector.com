import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

export type PageHeroHeight = 'tall' | 'short';

@Component({
  selector: 'app-page-hero',
  standalone: true,
  imports: [],
  templateUrl: './page-hero.component.html',
  styleUrl: './page-hero.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PageHeroComponent {
  @Input({ required: true }) imageUrl!: string;
  @Input() imageAlt = '';
  @Input() eyebrow = '';
  @Input() title = '';
  @Input() subtitle = '';
  @Input() height: PageHeroHeight = 'tall';
}
