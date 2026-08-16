import { Component, ChangeDetectionStrategy } from '@angular/core';

import { ActivatedRoute } from '@angular/router';

import { RouterLink } from '@angular/router';

import { SERVICES } from '../../core/data/services.data';

import { Service } from '../../core/models/service.model';

import { SeoService } from '../../core/services/seo.service';

import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';



@Component({

  selector: 'app-service-detail',

  standalone: true,

  imports: [

    RouterLink,

    HeroVideoComponent

  ],

  templateUrl:

    './service-detail.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:

    './service-detail.component.css'

})
export class ServiceDetailComponent {


service?: Service;



constructor(

private route: ActivatedRoute,

private seoService: SeoService

) {



const slug =

this.route.snapshot.paramMap.get('slug');




if(slug)

{

this.service = SERVICES.find(

(service) => service.slug === slug

);



if(this.service)

{

this.seoService.updatePage(

`${this.service.title} | WD Web Solutions`,

this.service.description

);


}

}



}



}