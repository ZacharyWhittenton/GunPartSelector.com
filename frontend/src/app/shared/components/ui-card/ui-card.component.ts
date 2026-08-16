import { Component, Input, ChangeDetectionStrategy } from '@angular/core';

import { RouterLink } from '@angular/router';



@Component({

  selector: 'app-ui-card',

  standalone: true,

  imports: [

    RouterLink

  ],

  templateUrl:

    './ui-card.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:

    './ui-card.component.css'

})
export class UiCardComponent {


  @Input()

  title = '';



  @Input()

  description = '';



  @Input()

  category = '';



  @Input()

  image?: string;



  @Input()

  link = '';



  @Input()

  icon = '';



}