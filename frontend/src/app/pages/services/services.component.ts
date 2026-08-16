import { Component, ChangeDetectionStrategy } from '@angular/core';

import { UiCardComponent } from '../../shared/components/ui-card/ui-card.component';
import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';

import { SERVICES } from '../../core/data/services.data';

import { SeoService } from '../../core/services/seo.service';



@Component({

  selector: 'app-services',

  standalone: true,

  imports: [

    UiCardComponent,

    HeroVideoComponent

  ],

  templateUrl:

    './services.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:

    './services.component.css'

})
export class ServicesComponent {


  services = SERVICES;



  constructor(

    private seoService: SeoService

  ) {


    this.seoService.updatePage(

      'Website Design & Development Services | WD Web Solutions',

      'Website design, web application development, e-commerce, and ongoing support services from WD Web Solutions.'

    );


  }


}