from decimal import Decimal

from django.core.management.base import BaseCommand

from products.models import Category, Product


class Command(BaseCommand):
    help = 'Seed database with sample sport injury equipment products'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')

        categories_data = [
            {'name': 'Knee Braces', 'slug': 'knee-braces', 'description': 'Support and stabilization for knee injuries'},
            {'name': 'Ankle Supports', 'slug': 'ankle-supports', 'description': 'Protection and recovery for ankle injuries'},
            {'name': 'Back Supports', 'slug': 'back-supports', 'description': 'Lumbar and spinal support products'},
            {'name': 'Shoulder Supports', 'slug': 'shoulder-supports', 'description': 'Rotator cuff and shoulder stabilization'},
            {'name': 'Wrist & Elbow', 'slug': 'wrist-elbow', 'description': 'Support for wrist and elbow conditions'},
            {'name': 'Compression Wear', 'slug': 'compression-wear', 'description': 'Compression sleeves and supports'},
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            categories[cat_data['slug']] = category
            if created:
                self.stdout.write(f'  Created category: {category.name}')

        products_data = [
            {
                'name': 'Premium Knee Stabilizer',
                'slug': 'premium-knee-stabilizer',
                'category': 'knee-braces',
                'description': 'Professional-grade knee brace designed for maximum stabilization during recovery. Features adjustable straps and breathable material for all-day comfort.',
                'price': Decimal('89.99'),
                'stock': 50,
                'injury_type': 'knee',
                'brand': 'HooperZone',
                'size': 'L',
                'material': 'Neoprene, Nylon',
            },
            {
                'name': 'Performance Knee Sleeve',
                'slug': 'performance-knee-sleeve',
                'category': 'knee-braces',
                'description': 'Lightweight compression sleeve for mild support and improved circulation during activity.',
                'price': Decimal('34.99'),
                'discount_price': Decimal('29.99'),
                'stock': 100,
                'injury_type': 'knee',
                'brand': 'HooperZone',
                'size': 'M',
                'material': 'Nylon, Spandex',
            },
            {
                'name': 'Ankle Stabilizer Brace',
                'slug': 'ankle-stabilizer-brace',
                'category': 'ankle-supports',
                'description': 'Provides firm support for ankle sprains and prevents re-injury during sports activities.',
                'price': Decimal('49.99'),
                'stock': 75,
                'injury_type': 'ankle',
                'brand': 'HooperZone',
                'size': 'M',
                'material': 'Neoprene',
            },
            {
                'name': 'Compression Ankle Sleeve',
                'slug': 'compression-ankle-sleeve',
                'category': 'ankle-supports',
                'description': 'Seamless compression sleeve for mild support and improved recovery.',
                'price': Decimal('24.99'),
                'stock': 120,
                'injury_type': 'ankle',
                'brand': 'HooperZone',
                'size': 'One Size',
                'material': 'Nylon, Lycra',
            },
            {
                'name': 'Lumbar Sports Support',
                'slug': 'lumbar-sports-support',
                'category': 'back-supports',
                'description': 'Ergonomic back support designed for athletes. Provides lumbar stabilization during heavy lifting and sports.',
                'price': Decimal('69.99'),
                'stock': 40,
                'injury_type': 'back',
                'brand': 'HooperZone',
                'size': 'L',
                'material': 'Mesh, Elastic',
            },
            {
                'name': 'Shoulder Support Brace',
                'slug': 'shoulder-support-brace',
                'category': 'shoulder-supports',
                'description': 'Adjustable shoulder brace for rotator cuff support and injury prevention.',
                'price': Decimal('59.99'),
                'stock': 60,
                'injury_type': 'shoulder',
                'brand': 'HooperZone',
                'size': 'M',
                'material': 'Neoprene',
            },
            {
                'name': 'Tennis Elbow Support',
                'slug': 'tennis-elbow-support',
                'category': 'wrist-elbow',
                'description': 'Targeted compression for tennis elbow and golfer\'s elbow relief.',
                'price': Decimal('29.99'),
                'stock': 80,
                'injury_type': 'elbow',
                'brand': 'HooperZone',
                'size': 'One Size',
                'material': 'Nylon, Rubber',
            },
            {
                'name': 'Wrist Stabilizer',
                'slug': 'wrist-stabilizer',
                'category': 'wrist-elbow',
                'description': 'Rigid support for wrist sprains and carpal tunnel relief.',
                'price': Decimal('39.99'),
                'stock': 65,
                'injury_type': 'wrist',
                'brand': 'HooperZone',
                'size': 'M',
                'material': 'Neoprene, Aluminum',
            },
            {
                'name': 'Compression Calf Sleeve',
                'slug': 'compression-calf-sleeve',
                'category': 'compression-wear',
                'description': 'Graduated compression for improved circulation and reduced muscle fatigue.',
                'price': Decimal('32.99'),
                'stock': 90,
                'injury_type': 'general',
                'brand': 'HooperZone',
                'size': 'M',
                'material': 'Nylon, Spandex',
            },
            {
                'name': 'Recovery Foam Roller',
                'slug': 'recovery-foam-roller',
                'category': 'compression-wear',
                'description': 'High-density foam roller for myofascial release and muscle recovery.',
                'price': Decimal('44.99'),
                'stock': 45,
                'injury_type': 'general',
                'brand': 'HooperZone',
                'size': 'Standard',
                'material': 'EVA Foam',
            },
        ]

        for prod_data in products_data:
            category_slug = prod_data.pop('category')
            product, created = Product.objects.get_or_create(
                slug=prod_data['slug'],
                defaults={**prod_data, 'category': categories[category_slug]}
            )
            if created:
                self.stdout.write(f'  Created product: {product.name}')

        # Mark some products as featured
        featured_slugs = ['premium-knee-stabilizer', 'lumbar-sports-support', 'shoulder-support-brace']
        Product.objects.filter(slug__in=featured_slugs).update(is_featured=True)

        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
