import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { BlogAdminService, PostWritePayload } from './blog-admin.service';

describe('BlogAdminService', () => {
  let service: BlogAdminService;
  let http: HttpTestingController;

  const payload: PostWritePayload = {
    title: 'Sealing Your Parking Lot',
    excerpt: 'Why sealing matters.',
    body: 'Full body text.',
    tags: ['asphalt'],
    coverImageUrl: null
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [BlogAdminService, provideHttpClient(), provideHttpClientTesting()]
    });

    service = TestBed.inject(BlogAdminService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('creates a post', () => {
    service.createPost(payload).subscribe();

    const request = http.expectOne('/api/admin/blog/posts');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush({});
  });

  it('publishes a post', () => {
    service.publishPost('9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd').subscribe();

    const request = http.expectOne(
      '/api/admin/blog/posts/9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd/publish'
    );
    expect(request.request.method).toBe('POST');
    request.flush({});
  });

  it('uploads an image as multipart form data', () => {
    const file = new File(['fake-bytes'], 'photo.jpg', { type: 'image/jpeg' });

    service.uploadImage(file).subscribe();

    const request = http.expectOne('/api/admin/blog/images');
    expect(request.request.method).toBe('POST');
    expect(request.request.body instanceof FormData).toBe(true);
    request.flush({ url: '/api/uploads/blog/photo.jpg' });
  });
});
