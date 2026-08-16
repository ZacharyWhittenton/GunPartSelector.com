import { ApplicationConfig } from '@angular/core';

import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';

import { provideRouter } from '@angular/router';

import { routes } from './app.routes';

import { authInterceptor } from './core/interceptors/auth.interceptor';


export const appConfig: ApplicationConfig = {

  providers: [

    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),

    provideRouter(routes)

  ]

};
