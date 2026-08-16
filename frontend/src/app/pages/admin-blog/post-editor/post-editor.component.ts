import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { BlogAdminService } from '../../../core/services/blog-admin.service';
import { BlogService } from '../../../core/services/blog.service';

@Component({
  selector: 'app-post-editor',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './post-editor.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './post-editor.component.css'
})
export class PostEditorComponent implements OnInit {
  private readonly formBuilder = inject(FormBuilder);
  private readonly blogService = inject(BlogService);
  private readonly blogAdminService = inject(BlogAdminService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly isEditMode = signal(false);
  readonly isLoading = signal(false);
  readonly isSaving = signal(false);
  readonly isUploadingImage = signal(false);
  readonly errorMessage = signal('');
  readonly coverImageUrl = signal<string | null>(null);

  private postId: string | null = null;

  postForm = this.formBuilder.nonNullable.group({
    title: ['', [Validators.required, Validators.maxLength(200)]],
    excerpt: ['', [Validators.required, Validators.maxLength(500)]],
    body: ['', [Validators.required]],
    tags: ['']
  });

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    if (!slug) {
      return;
    }

    this.isEditMode.set(true);
    this.isLoading.set(true);

    this.blogService
      .getPost(slug)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: post => {
          this.postId = post.id;
          this.coverImageUrl.set(post.coverImageUrl);
          this.postForm.patchValue({
            title: post.title,
            excerpt: post.excerpt,
            body: post.body,
            tags: post.tags.join(', ')
          });
        },
        error: () => this.errorMessage.set('Unable to load this post.')
      });
  }

  onImageSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    this.isUploadingImage.set(true);

    this.blogAdminService
      .uploadImage(file)
      .pipe(finalize(() => this.isUploadingImage.set(false)))
      .subscribe({
        next: response => this.coverImageUrl.set(response.url),
        error: () => this.errorMessage.set('Unable to upload image. Please try again.')
      });
  }

  submit(): void {
    this.errorMessage.set('');

    if (this.postForm.invalid) {
      this.postForm.markAllAsTouched();
      return;
    }

    const { title, excerpt, body, tags } = this.postForm.getRawValue();
    const payload = {
      title,
      excerpt,
      body,
      tags: tags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0),
      coverImageUrl: this.coverImageUrl()
    };

    this.isSaving.set(true);

    const request$ =
      this.isEditMode() && this.postId
        ? this.blogAdminService.updatePost(this.postId, payload)
        : this.blogAdminService.createPost(payload);

    request$.pipe(finalize(() => this.isSaving.set(false))).subscribe({
      next: () => this.router.navigateByUrl('/admin/blog'),
      error: () => this.errorMessage.set('Unable to save this post. Please try again.')
    });
  }

  hasError(controlName: keyof typeof this.postForm.controls): boolean {
    const control = this.postForm.controls[controlName];
    return control.invalid && (control.touched || control.dirty);
  }
}
