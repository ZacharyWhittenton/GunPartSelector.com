import { Component, ChangeDetectionStrategy } from '@angular/core';

import { RouterLink } from '@angular/router';

import { GALLERY_ITEMS } from '../../core/data/gallery.data';
import { UiCardComponent } from '../../shared/components/ui-card/ui-card.component';
import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';
import { SeoService } from '../../core/services/seo.service';



@Component({

  selector: 'app-gallery',

  standalone: true,

  imports:[

    RouterLink,

    UiCardComponent,

    HeroVideoComponent

    ],

  templateUrl:

    './gallery.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:

    './gallery.component.css'

})
export class GalleryComponent {


  galleryItems =
    GALLERY_ITEMS;


  constructor(

    private seoService: SeoService

  ) {


    this.seoService.updatePage(

      'Project Gallery | WD Web Solutions',

      'Browse a gallery of websites and web applications built by WD Web Solutions for growing businesses.'

    );


  }


}