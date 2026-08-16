import { Component, Input } from '@angular/core';

import { RouterLink } from '@angular/router';



@Component({

  selector: 'app-ui-button',

  standalone: true,

  imports: [

    RouterLink

  ],

  templateUrl:

    './ui-button.component.html',

  styleUrl:

    './ui-button.component.css'

})
export class UiButtonComponent {


@Input()

text = '';



@Input()

link = '';



}