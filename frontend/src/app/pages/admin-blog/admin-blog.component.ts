import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Observable, finalize } from 'rxjs';

import { BlogPostSummary } from '../../core/models/blog.model';
import { BlogAdminService } from '../../core/services/blog-admin.service';

@Component({
  selector: 'app-admin-blog',
  standalone: true,
  imports: [RouterLink, DatePipe],
  templateUrl: './admin-blog.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin-blog.component.css'
})
export class AdminBlogComponent implements OnInit {
  private readonly blogAdminService = inject(BlogAdminService);

  readonly posts = signal<BlogPostSummary[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly pendingPostIds = signal<Set<string>>(new Set());

  ngOnInit(): void {
    this.loadPosts();
  }

  loadPosts(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.blogAdminService
      .listAllPosts()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: posts => this.posts.set(posts),
        error: () => this.errorMessage.set('Unable to load posts. Please try again.')
      });
  }

  togglePublish(post: BlogPostSummary): void {
    const action$ =
      post.status === 'published'
        ? this.blogAdminService.unpublishPost(post.id)
        : this.blogAdminService.publishPost(post.id);

    this.withPending(post.id, action$).subscribe({
      next: updated => {
        this.posts.update(posts => posts.map(p => (p.id === updated.id ? updated : p)));
      }
    });
  }

  deletePost(post: BlogPostSummary): void {
    if (!confirm(`Delete "${post.title}"? This cannot be undone.`)) {
      return;
    }

    this.withPending(post.id, this.blogAdminService.deletePost(post.id)).subscribe({
      next: () => this.posts.update(posts => posts.filter(p => p.id !== post.id))
    });
  }

  isPending(postId: string): boolean {
    return this.pendingPostIds().has(postId);
  }

  private withPending<T>(postId: string, source: Observable<T>): Observable<T> {
    this.pendingPostIds.update(pending => new Set(pending).add(postId));
    return source.pipe(
      finalize(() => {
        this.pendingPostIds.update(pending => {
          const next = new Set(pending);
          next.delete(postId);
          return next;
        });
      })
    );
  }
}
