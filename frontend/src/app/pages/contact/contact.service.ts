import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';

export interface ContactFormPayload {
  name: string;
  emailAddress: string;
  company?: string;
  phone?: string;
  service: string;
  message: string;
}

export interface ContactResponse {
  message: string;
}

interface ContactApiResponse {
  id: string;
  status: 'received';
}

@Injectable({
  providedIn: 'root'
})
export class ContactService {
  constructor(private readonly http: HttpClient) {}

  submitContactForm(
    payload: ContactFormPayload
  ): Observable<ContactResponse> {
    return this.http
      .post<ContactApiResponse>('/api/contact-requests', payload)
      .pipe(
        map(() => ({
          message:
            'Your estimate request has been received. WD Web Solutions will contact you soon.'
        }))
      );
  }
}
