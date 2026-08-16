import { Service } from '../models/service.model';



export const SERVICES: Service[] = [

  {
    title: 'Website Design',

    slug: 'website-design',

    category: 'Design',

    description:
      'Custom, responsive website design built to represent your brand and convert visitors into customers.',

    details:
      'WD Web Solutions designs modern, mobile-first websites tailored to your business. From branding to layout, every site is built for performance, accessibility, and results.',

    icon:
      'palette',

    image:
      '/assets/images/services/website-design.jpg'

  },


  {
    title: 'Web Application Development',

    slug: 'web-app-development',

    category: 'Development',

    description:
      'Custom web applications and internal tools built with modern frameworks like Angular and FastAPI.',

    details:
      'We build custom web applications, client portals, and internal tools designed around your workflow, using modern frameworks for a fast, secure, and maintainable product.',

    icon:
      'laptop-code',

    image:
      '/assets/images/services/web-app-development.jpg'

  },


  {
    title:
      'E-Commerce Solutions',

    slug:
      'ecommerce-solutions',

    category:
      'E-Commerce',

    description:
      'Online stores designed to sell, with secure checkout, inventory tools, and a smooth customer experience.',

    details:
      'WD Web Solutions builds e-commerce storefronts that make it easy for customers to browse, buy, and come back — with secure payments and tools to manage inventory and orders.',

    icon:
      'cart-shopping',

    image:
      '/assets/images/services/ecommerce-solutions.jpg'

  },


  {
    title:
      'Website Maintenance & Support',

    slug:
      'website-maintenance-support',

    category:
      'Support',

    description:
      'Ongoing maintenance, updates, and support to keep your website secure, fast, and up to date.',

    details:
      'From security updates to content changes and performance monitoring, our maintenance plans keep your website running smoothly so you can focus on your business.',

    icon:
      'wrench',

    image:
      '/assets/images/services/website-maintenance-support.jpg'

  }

];
