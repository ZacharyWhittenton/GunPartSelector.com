import { Component, ChangeDetectionStrategy } from '@angular/core';

import { RouterLink } from '@angular/router';


@Component({

  selector: 'app-footer',

  standalone: true,

  imports: [

    RouterLink

  ],

  templateUrl:
    './footer.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:
    './footer.component.css'

})
export class FooterComponent {


  year = new Date().getFullYear();


}