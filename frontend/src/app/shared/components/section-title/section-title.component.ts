import { Component, Input } from '@angular/core';

@Component({
 selector:'app-section-title',
 templateUrl:'./section-title.component.html',
 styleUrl:'./section-title.component.css'
})
export class SectionTitleComponent {

 @Input()
 title='';

 @Input()
 description='';

}