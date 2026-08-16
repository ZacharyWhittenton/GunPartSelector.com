import { Component, ChangeDetectionStrategy } from '@angular/core';

import { RouterOutlet } from '@angular/router';

import { NavbarComponent } from './navbar/navbar.component';

import { FooterComponent } from './footer/footer.component';

import { ChatWidgetComponent } from '../../shared/components/chat-widget/chat-widget.component';


@Component({

  selector: 'app-public-layout',

  standalone: true,

  imports: [

    RouterOutlet,

    NavbarComponent,

    FooterComponent,

    ChatWidgetComponent

  ],

  templateUrl:
    './public-layout.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:
    './public-layout.component.css'

})
export class PublicLayoutComponent {


}