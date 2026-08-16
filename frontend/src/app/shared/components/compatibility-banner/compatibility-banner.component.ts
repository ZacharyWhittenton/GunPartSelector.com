import { NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import { CompatibilityIssue } from '../../../core/models/build.model';

@Component({
  selector: 'app-compatibility-banner',
  standalone: true,
  imports: [NgFor, NgIf],
  templateUrl: './compatibility-banner.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CompatibilityBannerComponent {
  @Input({ required: true }) issues!: CompatibilityIssue[];
}
