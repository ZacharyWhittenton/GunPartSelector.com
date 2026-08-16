import { Component, ChangeDetectionStrategy } from '@angular/core';

import { RouterLink } from '@angular/router';

import { UiCardComponent } from '../../shared/components/ui-card/ui-card.component';

import { SERVICES } from '../../core/data/services.data';

import { SeoService } from '../../core/services/seo.service';

import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';

import { TestimonialCarouselComponent } from '../../shared/components/testimonial-carousel/testimonial-carousel.component';



@Component({

  selector: 'app-home',

  standalone: true,

  imports: [

    RouterLink,

    UiCardComponent,

    HeroVideoComponent,

    TestimonialCarouselComponent

  ],

  templateUrl:

    './home.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:

    './home.component.css'

})
export class HomeComponent {


services = SERVICES.slice(0,3);



constructor(

private seoService: SeoService

)

{


this.seoService.updatePage(

'WD Web Solutions | Website Design & Development',

'Professional website design, web application development, e-commerce, and ongoing support for growing businesses in Austin, TX.'

);


}



}