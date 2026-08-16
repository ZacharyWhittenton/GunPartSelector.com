import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  inject,
  signal
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ClickPoint, PageViewSummary } from '../../core/models/site-analytics.model';
import { SiteAnalyticsAdminService } from '../../core/services/site-analytics-admin.service';

const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 600;
const POINT_RADIUS = 36;

function buildColorLookup(): Uint8ClampedArray {
  const gradientCanvas = document.createElement('canvas');
  gradientCanvas.width = 256;
  gradientCanvas.height = 1;
  const ctx = gradientCanvas.getContext('2d')!;
  const gradient = ctx.createLinearGradient(0, 0, 256, 0);
  gradient.addColorStop(0, 'rgba(0,0,255,0)');
  gradient.addColorStop(0.2, 'rgba(0,0,255,0.6)');
  gradient.addColorStop(0.45, 'rgba(0,255,255,0.75)');
  gradient.addColorStop(0.65, 'rgba(0,255,0,0.8)');
  gradient.addColorStop(0.85, 'rgba(255,255,0,0.9)');
  gradient.addColorStop(1, 'rgba(255,0,0,1)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 256, 1);
  return ctx.getImageData(0, 0, 256, 1).data;
}

@Component({
  selector: 'app-admin-analytics',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './admin-analytics.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin-analytics.component.css'
})
export class AdminAnalyticsComponent implements OnInit {
  @ViewChild('heatmapCanvas') private readonly heatmapCanvas?: ElementRef<HTMLCanvasElement>;

  private readonly analyticsAdminService = inject(SiteAnalyticsAdminService);

  readonly canvasWidth = CANVAS_WIDTH;
  readonly canvasHeight = CANVAS_HEIGHT;

  readonly topPages = signal<PageViewSummary[]>([]);
  readonly isLoadingPages = signal(false);
  readonly errorMessage = signal('');

  readonly days = signal(30);
  readonly selectedPath = signal<string | null>(null);
  readonly heatmapPoints = signal<ClickPoint[]>([]);
  readonly isLoadingHeatmap = signal(false);

  ngOnInit(): void {
    this.loadTopPages();
  }

  loadTopPages(): void {
    this.isLoadingPages.set(true);
    this.errorMessage.set('');

    this.analyticsAdminService
      .getTopPages(this.days())
      .pipe(finalize(() => this.isLoadingPages.set(false)))
      .subscribe({
        next: pages => {
          this.topPages.set(pages);
          if (!this.selectedPath() && pages.length > 0) {
            this.selectPage(pages[0].path);
          }
        },
        error: () =>
          this.errorMessage.set('Unable to load page view analytics. Please try again.')
      });
  }

  onDaysChange(value: string): void {
    this.days.set(Number(value));
    this.loadTopPages();
    const path = this.selectedPath();
    if (path) {
      this.selectPage(path);
    }
  }

  selectPage(path: string): void {
    this.selectedPath.set(path);
    this.isLoadingHeatmap.set(true);

    this.analyticsAdminService
      .getHeatmap(path, this.days())
      .pipe(finalize(() => this.isLoadingHeatmap.set(false)))
      .subscribe({
        next: points => {
          this.heatmapPoints.set(points);
          queueMicrotask(() => this.renderHeatmap(points));
        },
        error: () => this.errorMessage.set('Unable to load the heatmap for that page.')
      });
  }

  private renderHeatmap(points: ClickPoint[]): void {
    const canvas = this.heatmapCanvas?.nativeElement;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) {
      return;
    }

    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

    if (points.length === 0) {
      return;
    }

    const density = document.createElement('canvas');
    density.width = CANVAS_WIDTH;
    density.height = CANVAS_HEIGHT;
    const densityCtx = density.getContext('2d')!;
    densityCtx.globalCompositeOperation = 'lighter';

    for (const point of points) {
      const x = (point.xPercent / 100) * CANVAS_WIDTH;
      const y = (point.yPercent / 100) * CANVAS_HEIGHT;
      const gradient = densityCtx.createRadialGradient(x, y, 0, x, y, POINT_RADIUS);
      gradient.addColorStop(0, 'rgba(0,0,0,0.25)');
      gradient.addColorStop(1, 'rgba(0,0,0,0)');
      densityCtx.fillStyle = gradient;
      densityCtx.beginPath();
      densityCtx.arc(x, y, POINT_RADIUS, 0, Math.PI * 2);
      densityCtx.fill();
    }

    const colorLookup = buildColorLookup();
    const imageData = densityCtx.getImageData(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    const pixels = imageData.data;

    for (let i = 0; i < pixels.length; i += 4) {
      const alpha = pixels[i + 3];
      if (alpha === 0) {
        continue;
      }
      const lookupIndex = Math.min(255, alpha) * 4;
      pixels[i] = colorLookup[lookupIndex];
      pixels[i + 1] = colorLookup[lookupIndex + 1];
      pixels[i + 2] = colorLookup[lookupIndex + 2];
      pixels[i + 3] = colorLookup[lookupIndex + 3];
    }

    ctx.putImageData(imageData, 0, 0);
  }
}
