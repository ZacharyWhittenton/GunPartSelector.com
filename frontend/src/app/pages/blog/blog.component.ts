import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { BlogPostSummary } from '../../core/models/blog.model';
import { BlogService } from '../../core/services/blog.service';
import { SeoService } from '../../core/services/seo.service';
import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';

@Component({
  selector: 'app-blog',
  standalone: true,
  imports: [RouterLink, DatePipe, HeroVideoComponent],
  templateUrl: './blog.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './blog.component.css'
})
export class BlogComponent implements OnInit {
  private readonly blogService = inject(BlogService);
  private readonly seoService = inject(SeoService);

  readonly posts = signal<BlogPostSummary[]>([]);
  readonly tags = signal<string[]>([]);
  readonly selectedTag = signal<string | null>(null);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  ngOnInit(): void {
    this.seoService.updatePage(
      'Blog | WD Web Solutions',
      'Articles and updates on website design, development, and growing your business online from WD Web Solutions.'
    );

    this.blogService.listTags().subscribe({
      next: tags => this.tags.set(tags)
    });
    this.loadPosts();
  }

  selectTag(tag: string | null): void {
    this.selectedTag.set(tag);
    this.loadPosts();
  }

  private loadPosts(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.blogService
      .listPosts(this.selectedTag() ?? undefined)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: posts => this.posts.set(posts),
        error: () => this.errorMessage.set('Unable to load blog posts. Please try again.')
      });
  }
}
