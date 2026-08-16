import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink } from '@angular/router';

import { RESOURCES } from '../../core/data/resources.data';
import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';
import { SeoService } from '../../core/services/seo.service';



@Component({

  selector: 'app-resources',

  standalone: true,

  imports: [HeroVideoComponent, RouterLink],

  templateUrl:

    './resources.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:

    './resources.component.css'

})
export class ResourcesComponent {


resources =
RESOURCES;


constructor(

private seoService: SeoService

) {


this.seoService.updatePage(

'Resources | WD Web Solutions',

'Guides and resources on website design, development, and growing your business online from WD Web Solutions.'

);


}


}