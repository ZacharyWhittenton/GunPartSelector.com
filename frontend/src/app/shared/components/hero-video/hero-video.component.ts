import { AfterViewInit, Component, ElementRef, ViewChild } from '@angular/core';

@Component({
  selector: 'app-hero-video',
  imports: [],
  templateUrl: './hero-video.component.html',
  styleUrl: './hero-video.component.css'
})
export class HeroVideoComponent implements AfterViewInit {

  @ViewChild('heroVideo') heroVideo?: ElementRef<HTMLVideoElement>;

  ngAfterViewInit(): void {
    const video = this.heroVideo?.nativeElement;
    if (!video) return;
    video.muted = true;
    video.play().catch(() => {});
  }

}
