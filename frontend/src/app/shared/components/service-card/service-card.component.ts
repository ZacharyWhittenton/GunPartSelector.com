import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-service-card',
  imports: [],
  templateUrl: './service-card.component.html',
  styleUrl: './service-card.component.css'
})
export class ServiceCardComponent {

  @Input()
  title = '';

  @Input()
  description = '';

  @Input()
  image = '';

}