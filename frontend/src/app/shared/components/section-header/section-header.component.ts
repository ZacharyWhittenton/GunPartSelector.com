import { Component, Input } from '@angular/core';



@Component({

selector:'app-section-header',

standalone:true,

imports:[],

templateUrl:

'./section-header.component.html',

styleUrl:

'./section-header.component.css'

})

export class SectionHeaderComponent {



@Input()

eyebrow = '';



@Input()

title = '';



@Input()

description = '';



}