import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ContactFormPayload, ContactService } from './contact.service';

describe('ContactService', () => {
  let service: ContactService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ContactService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });

    service = TestBed.inject(ContactService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('submits the contact request to the backend API', () => {
    const payload: ContactFormPayload = {
      name: 'Taylor Client',
      emailAddress: 'taylor@example.com',
      service: 'Parking Lot Striping',
      message: 'Please provide an estimate.'
    };
    let message = '';

    service.submitContactForm(payload).subscribe(response => {
      message = response.message;
    });

    const request = http.expectOne('/api/contact-requests');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush({
      id: '9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd',
      status: 'received'
    });

    expect(message).toContain('has been received');
  });
});
