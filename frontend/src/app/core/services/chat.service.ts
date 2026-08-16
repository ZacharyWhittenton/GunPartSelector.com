import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { ChatTurn } from '../models/chat.model';

interface ChatResponse {
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  constructor(private readonly http: HttpClient) {}

  sendMessage(messages: ChatTurn[], pageContext: string | null): Observable<ChatResponse> {
    return this.http.post<ChatResponse>('/api/chat/messages', { messages, pageContext });
  }
}
