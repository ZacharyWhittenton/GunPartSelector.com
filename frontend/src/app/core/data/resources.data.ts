import { Resource } from '../models/resource.model';

export const RESOURCES: Resource[] = [
  {
    title: 'Choosing a Caliber',
    category: 'Buying Guide',
    description:
      'A rundown of the most common AR-15 platform calibers — 5.56 NATO, .223 Wylde, .300 Blackout, and 6.5 Grendel — and how to pick one for your build.',
    slug: 'choosing-a-caliber',
    icon: 'bullseye'
  },
  {
    title: 'Mil-Spec vs. Commercial Buffer Tubes',
    category: 'Compatibility',
    description:
      'Why buffer tube diameter matters, how to tell the two apart, and why it has to match your stock or brace.',
    slug: 'mil-spec-vs-commercial-buffer-tubes',
    icon: 'ruler'
  },
  {
    title: 'Gas System Length, Explained',
    category: 'Compatibility',
    description:
      'Pistol, carbine, mid-length, and rifle gas systems: how barrel length drives the choice, and why your handguard has to clear it.',
    slug: 'gas-system-length-explained',
    icon: 'gauge'
  },
  {
    title: 'Handguard Mounting Interfaces',
    category: 'Compatibility',
    description:
      'Mil-spec barrel nuts vs. proprietary handguard systems, and what to check before you buy a free-float handguard.',
    slug: 'handguard-mounting-interfaces',
    icon: 'screwdriver-wrench'
  },
  {
    title: 'Muzzle Thread Patterns',
    category: 'Buying Guide',
    description:
      '1/2x28 vs. 5/8x24 and how your caliber decides which muzzle devices will actually fit.',
    slug: 'muzzle-thread-patterns',
    icon: 'crosshairs'
  },
  {
    title: 'Reading a Build’s Compatibility Warnings',
    category: 'Using GunPartSelector',
    description:
      'What our compatibility checker flags, the difference between an error and a warning, and how to resolve a mismatch.',
    slug: 'reading-compatibility-warnings',
    icon: 'triangle-exclamation'
  }
];
