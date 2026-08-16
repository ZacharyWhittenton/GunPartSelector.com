import { Component, ChangeDetectionStrategy, inject } from '@angular/core';

import { RouterOutlet } from '@angular/router';

import { AnalyticsService } from './core/services/analytics.service';
import { VisitorTrackingService } from './core/services/visitor-tracking.service';


@Component({

  selector: 'app-root',

  standalone: true,

  imports: [

    RouterOutlet

  ],

  templateUrl:
    './app.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:
    './app.component.css'

})
export class AppComponent {

  private readonly analyticsService = inject(AnalyticsService);
  private readonly visitorTrackingService = inject(VisitorTrackingService);

  constructor() {
    this.analyticsService.init();
    this.visitorTrackingService.init();
  }

}