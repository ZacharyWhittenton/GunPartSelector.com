import { Routes } from '@angular/router';

import { PublicLayoutComponent } from './layouts/public-layout/public-layout.component';
import { adminGuard } from './core/guards/admin.guard';


export const routes: Routes = [


  {
    path: '',

    component: PublicLayoutComponent,

    children: [

      {
        path: '',

        loadComponent: () =>
          import('./pages/home/home.component')
            .then(m => m.HomeComponent)

      },
      {
        path: 'about',

        loadComponent: () =>
          import('./pages/about/about.component')
            .then(m => m.AboutComponent)

      },


      {
        path: 'services',

        loadComponent: () =>
          import('./pages/services/services.component')
            .then(m => m.ServicesComponent)

      },


      {
        path: 'gallery',

        loadComponent: () =>
          import('./pages/gallery/gallery.component')
            .then(m => m.GalleryComponent)

      },


      {
        path: 'resources',

        loadComponent: () =>
          import('./pages/resources/resources.component')
            .then(m => m.ResourcesComponent)

      },


      {
        path: 'blog',

        loadComponent: () =>
          import('./pages/blog/blog.component')
            .then(m => m.BlogComponent)

      },


      {
        path: 'blog/:slug',

        loadComponent: () =>
          import('./pages/blog/blog-post-detail/blog-post-detail.component')
            .then(m => m.BlogPostDetailComponent)

      },


      {
        path: 'contact',

        loadComponent: () =>
          import('./pages/contact/contact.component')
            .then(m => m.ContactComponent)

      },


      {
        path: 'faq',

        loadComponent: () =>
          import('./pages/faq/faq.component')
            .then(m => m.FaqComponent)

      },


      {
        path: 'login',

        loadComponent: () =>
          import('./pages/login/login.component')
            .then(m => m.LoginComponent)

      },


      {
        path: 'register',

        loadComponent: () =>
          import('./pages/register/register.component')
            .then(m => m.RegisterComponent)

      },


      {
        path: 'parts',

        loadComponent: () =>
          import('./pages/catalog/catalog-home/catalog-home.component')
            .then(m => m.CatalogHomeComponent)

      },


      {
        path: 'parts/:categorySlug',

        loadComponent: () =>
          import('./pages/catalog/category-browse/category-browse.component')
            .then(m => m.CategoryBrowseComponent)

      },


      {
        path: 'parts/:categorySlug/:productSlug',

        loadComponent: () =>
          import('./pages/catalog/product-detail/product-detail.component')
            .then(m => m.ProductDetailComponent)

      },


      {
        path: 'builder/share/:slug',

        loadComponent: () =>
          import('./pages/build-configurator/build-share/build-share.component')
            .then(m => m.BuildShareComponent)

      },


      {
        path: 'merch/success',

        loadComponent: () =>
          import('./pages/merch/checkout-success/checkout-success.component')
            .then(m => m.CheckoutSuccessComponent)

      },


      {
        path: 'merch',

        loadComponent: () =>
          import('./pages/merch/merch-list/merch-list.component')
            .then(m => m.MerchListComponent)

      },


      {
        path: 'merch/:slug',

        loadComponent: () =>
          import('./pages/merch/merch-detail/merch-detail.component')
            .then(m => m.MerchDetailComponent)

      },


      {
        path: 'cart',

        loadComponent: () =>
          import('./pages/cart/cart.component')
            .then(m => m.CartComponent)

      },


      {
        path: 'admin',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin/admin.component')
            .then(m => m.AdminComponent)

      },


      {
        path: 'admin/dashboard',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-dashboard/admin-dashboard.component')
            .then(m => m.AdminDashboardComponent)

      },


      {
        path: 'admin/blog',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-blog/admin-blog.component')
            .then(m => m.AdminBlogComponent)

      },


      {
        path: 'admin/blog/new',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-blog/post-editor/post-editor.component')
            .then(m => m.PostEditorComponent)

      },


      {
        path: 'admin/blog/:slug/edit',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-blog/post-editor/post-editor.component')
            .then(m => m.PostEditorComponent)

      },


      {
        path: 'admin/marketplace',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-marketplace/admin-marketplace.component')
            .then(m => m.AdminMarketplaceComponent)

      },


      {
        path: 'admin/marketplace/orders',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-marketplace/admin-marketplace-orders/admin-marketplace-orders.component')
            .then(m => m.AdminMarketplaceOrdersComponent)

      },


      {
        path: 'admin/leads',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-leads/admin-leads.component')
            .then(m => m.AdminLeadsComponent)

      },


      {
        path: 'admin/discount-codes',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-discount-codes/admin-discount-codes.component')
            .then(m => m.AdminDiscountCodesComponent)

      },


      {
        path: 'admin/analytics',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-analytics/admin-analytics.component')
            .then(m => m.AdminAnalyticsComponent)

      },


      {
        path: 'account',

        loadComponent: () =>
          import('./pages/account/account.component')
            .then(m => m.AccountComponent)

      },


      {
        path: 'testimonials/write',

        loadComponent: () =>
          import('./pages/testimonials/write-testimonial/write-testimonial.component')
            .then(m => m.WriteTestimonialComponent)

      },


      {
        path: 'admin/testimonials',

        canActivate: [adminGuard],

        loadComponent: () =>
          import('./pages/admin-testimonials/admin-testimonials.component')
            .then(m => m.AdminTestimonialsComponent)

      },


      {
        path: 'privacy-policy',

        loadComponent: () =>
          import('./pages/privacy-policy/privacy-policy.component')
            .then(m => m.PrivacyPolicyComponent)

      },


      {
        path: 'terms',

        loadComponent: () =>
          import('./pages/terms/terms.component')
            .then(m => m.TermsComponent)

      },
      {
        path: '**',
        loadComponent: () =>
        import('./pages/not-found/not-found.component')
        .then(
        component => component.NotFoundComponent
        )
       }
    ]

  },


  {
    path: '**',

    redirectTo: ''

  }


];