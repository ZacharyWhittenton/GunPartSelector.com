import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { BlogService } from './blog.service';
import { BlogPostSummary } from '../models/blog.model';

describe('BlogService', () => {
  let service: BlogService;
  let http: HttpTestingController;

  const post: BlogPostSummary = {
    id: '9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd',
    title: 'Sealing Your Parking Lot',
    slug: 'sealing-your-parking-lot',
    excerpt: 'Why sealing matters.',
    coverImageUrl: null,
    tags: ['asphalt'],
    authorName: 'Admin Person',
    status: 'published',
    publishedAt: '2026-08-09T12:00:00Z',
    createdAt: '2026-08-09T12:00:00Z'
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [BlogService, provideHttpClient(), provideHttpClientTesting()]
    });

    service = TestBed.inject(BlogService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('lists posts without a tag filter', () => {
    service.listPosts().subscribe();

    const request = http.expectOne(r => r.url === '/api/blog/posts');
    expect(request.request.params.has('tag')).toBe(false);
    request.flush([post]);
  });

  it('lists posts filtered by tag', () => {
    service.listPosts('asphalt').subscribe();

    const request = http.expectOne(r => r.url === '/api/blog/posts');
    expect(request.request.params.get('tag')).toBe('asphalt');
    request.flush([post]);
  });

  it('gets a post by slug', () => {
    service.getPost('sealing-your-parking-lot').subscribe();

    const request = http.expectOne('/api/blog/posts/sealing-your-parking-lot');
    expect(request.request.method).toBe('GET');
    request.flush({ ...post, body: 'Full body', updatedAt: post.createdAt });
  });

  it('adds a comment', () => {
    service.addComment('sealing-your-parking-lot', 'Great post!').subscribe();

    const request = http.expectOne('/api/blog/posts/sealing-your-parking-lot/comments');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ body: 'Great post!' });
    request.flush({
      id: '1',
      authorId: '2',
      authorName: 'Taylor Client',
      body: 'Great post!',
      createdAt: post.createdAt
    });
  });

  it('subscribes and unsubscribes to a tag', () => {
    service.subscribeToTag('asphalt').subscribe();
    http.expectOne('/api/blog/tags/asphalt/subscribe').flush(null);

    service.unsubscribeFromTag('asphalt').subscribe();
    http.expectOne('/api/blog/tags/asphalt/subscribe').flush(null);
  });
});
