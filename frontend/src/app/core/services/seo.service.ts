import { Injectable } from '@angular/core';

import {
  Title,
  Meta
} from '@angular/platform-browser';



const DEFAULT_OG_IMAGE = '/assets/images/hero-poster.jpg';

@Injectable({

  providedIn: 'root'

})
export class SeoService {


  constructor(

    private title: Title,

    private meta: Meta

  ) {}



  updatePage(

    title: string,

    description: string,

    imageUrl: string = DEFAULT_OG_IMAGE

  ): void {


    this.title.setTitle(title);



    this.meta.updateTag({

      name: 'description',

      content: description

    });



    this.meta.updateTag({

      property: 'og:title',

      content: title

    });



    this.meta.updateTag({

      property: 'og:description',

      content: description

    });



    this.meta.updateTag({

      property: 'og:image',

      content: this.absoluteUrl(imageUrl)

    });



    this.meta.updateTag({

      name: 'twitter:title',

      content: title

    });



    this.meta.updateTag({

      name: 'twitter:description',

      content: description

    });



    this.meta.updateTag({

      name: 'twitter:image',

      content: this.absoluteUrl(imageUrl)

    });


  }



  private absoluteUrl(url: string): string {

    if (url.startsWith('http://') || url.startsWith('https://')) {

      return url;

    }

    return `${window.location.origin}${url.startsWith('/') ? '' : '/'}${url}`;

  }


}