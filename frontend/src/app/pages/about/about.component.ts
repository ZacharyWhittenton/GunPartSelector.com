import { Component, ChangeDetectionStrategy } from '@angular/core';

import { RouterLink } from '@angular/router';

import { SeoService } from '../../core/services/seo.service';

import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';



@Component({

  selector: 'app-about',

  standalone: true,

  imports: [

    RouterLink,

    HeroVideoComponent

  ],

  templateUrl:

    './about.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:

    './about.component.css'

})
export class AboutComponent {



constructor(

private seoService: SeoService

) {



this.seoService.updatePage(

'About WD Web Solutions | Web Design & Development Agency',

'Learn about WD Web Solutions, our story, experience, and commitment to building great websites and web applications.'

);


}



}