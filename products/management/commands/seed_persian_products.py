from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Category, Product, ProductImage

from ._sizes import STANDARD_SIZES, set_demo_sizes


class Command(BaseCommand):
    help = 'Seed database with Persian (Farsi) products and categories for Iranian market testing'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Creating Persian products and categories...'))

        # name/description are English; name_fa/description_fa are Persian.
        categories_data = [
            {
                'name': 'Knee Braces & Supports',
                'name_fa': 'زانوبند',
                'slug': 'knee-braces',
                'description': 'Braces, sleeves and straps for sports injuries and everyday knee pain.',
                'description_fa': 'زانوبند ساده، کشی و مفصل‌دار برای آسیب‌های ورزشی و دردهای روزمره زانو',
            },
            {
                'name': 'Ankle Supports',
                'name_fa': 'قوزک‌بند',
                'slug': 'ankle-supports',
                'description': 'Ankle stabilizers and compression sleeves for prevention and recovery.',
                'description_fa': 'قوزک‌بند ساده و کشی برای پیشگیری از پیچ‌خوردگی و بهبود آسیب',
            },
            {
                'name': 'Back Supports',
                'name_fa': 'کمربند طبی',
                'slug': 'back-supports',
                'description': 'Lumbar braces and belts for athletes and everyday back pain.',
                'description_fa': 'کمربند طبی و کرست کمر برای ورزشکاران و کاهش کمردرد',
            },
            {
                'name': 'Shoulder Supports',
                'name_fa': 'شانه‌بند',
                'slug': 'shoulder-supports',
                'description': 'Shoulder braces and stabilizers for injury prevention and rehab.',
                'description_fa': 'شانه‌بند و تثبیت‌کننده برای پیشگیری از آسیب و دوره توانبخشی',
            },
            {
                'name': 'Wrist & Elbow Supports',
                'name_fa': 'مچ‌بند و آرنج‌بند',
                'slug': 'wrist-elbow',
                'description': 'Wrist splints and elbow supports for racket sports and daily strain.',
                'description_fa': 'مچ‌بند و آرنج‌بند برای ورزش‌های راکتی، بدنسازی و فشارهای روزمره',
            },
            {
                'name': 'Compression & Recovery',
                'name_fa': 'پوشاک فشاری و بهبودی',
                'slug': 'compression-wear',
                'description': 'Compression sleeves and recovery tools that boost circulation.',
                'description_fa': 'ساق‌بند فشاری و وسایل بهبودی برای بهبود گردش خون و کاهش گرفتگی عضلات',
            },
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'name_fa': cat_data['name_fa'],
                    'description': cat_data['description'],
                    'description_fa': cat_data['description_fa'],
                    'is_active': True,
                }
            )
            if not created:
                category.name = cat_data['name']
                category.name_fa = cat_data['name_fa']
                category.description = cat_data['description']
                category.description_fa = cat_data['description_fa']
                category.is_active = True
                category.save()
            categories[cat_data['slug']] = category
            self.stdout.write(f'  {"Created" if created else "Updated"} category: {category.name}')

        products_data = [
            {
                'name': 'زانوبند مفصل‌دار حرفه‌ای سپر مدیکال',
                'name_fa': 'زانوبند مفصل‌دار حرفه‌ای سپر مدیکال',
                'slug': 'premium-knee-brace',
                'category': 'knee-braces',
                'description': 'زانوبند مفصل‌دار حرفه‌ای با طراحی حمایت کامل با باندهای قابل تنظیم و جنس نفوذپذیر.',
                'description_fa': 'زانوبند مفصل‌دار حرفه‌ای سپر مدیکال با طراحی حمایت کامل، دارای باندهای قابل تنظیم و جنس نفوذپذیر برای راحتی تمام‌وقت.',
                'price': Decimal('890000'),
                'price_irr': 89000000,
                'cost': Decimal('450000'),
                'cost_irr': 45000000,
                'stock': 50,
                'injury_type': 'knee',
                'brand': 'HooperZone',
                'sizes': STANDARD_SIZES,
                'material': 'نئوپرین، نایلون',
            },
            {
                'name': 'زانوبند کشی ورزشی',
                'name_fa': 'زانوبند کشی ورزشی',
                'slug': 'performance-knee-sleeve',
                'category': 'knee-braces',
                'description': 'بند کشی فشاری سبک وزن برای حمایت ملایم و بهبود گردش خون.',
                'description_fa': 'بند کشی فشاری سبک وزن برای حمایت ملایم زانو و بهبود گردش خون در طول فعالیت.',
                'price': Decimal('349000'),
                'price_irr': 34900000,
                'cost': Decimal('180000'),
                'cost_irr': 18000000,
                'discount_price': Decimal('299000'),
                'discount_price_irr': 29900000,
                'stock': 100,
                'injury_type': 'knee',
                'brand': 'HooperZone',
                'sizes': STANDARD_SIZES,
                'material': 'نایلون، اسپانکس',
                'is_featured': True,
            },
            {
                'name': 'استابیلایزر مچ پا حرفه‌ای',
                'name_fa': 'استابیلایزر مچ پا حرفه‌ای',
                'slug': 'premium-ankle-stabilizer',
                'category': 'ankle-supports',
                'description': 'حفاظت محکم در برابر چرخش مچ پا و جلوگیری از آسیب مجدد.',
                'description_fa': 'استابیلایزر مچ پا حرفه‌ای با قابلیت جلوگیری از چرخش ناخواسته و حمایت قوی در طول ورزش.',
                'price': Decimal('499000'),
                'price_irr': 49900000,
                'cost': Decimal('250000'),
                'cost_irr': 25000000,
                'stock': 75,
                'injury_type': 'ankle',
                'brand': 'HooperZone',
                'sizes': STANDARD_SIZES,
                'material': 'نئوپرین',
                'is_featured': True,
            },
            {
                'name': 'قوزک‌بند کشی',
                'name_fa': 'قوزک‌بند کشی',
                'slug': 'compression-ankle-sleeve',
                'category': 'ankle-supports',
                'description': 'بند کشی فشاری بدون درز برای حمایت ملایم و بهبود بهبودی.',
                'description_fa': 'قوزک‌بند کشی با طراحی بدون درز و فشار یکنواخت برای راحتی حداکثری.',
                'price': Decimal('249000'),
                'price_irr': 24900000,
                'cost': Decimal('120000'),
                'cost_irr': 12000000,
                'stock': 120,
                'injury_type': 'ankle',
                'brand': 'MediPro',
                'material': 'نایلون، لایکرا',
            },
            {
                'name': 'حمایت کمری ورزشی سپر مدیکال',
                'name_fa': 'حمایت کمری ورزشی سپر مدیکال',
                'slug': 'lumbar-sports-support',
                'category': 'back-supports',
                'description': 'حمایت کمری ارگونومیک برای ورزشکاران با حمایت لومبال.',
                'description_fa': 'حمایت کمری ورزشی ارگونومیک سپر مدیکال با فناوری حمایت لومبال و جنس تنفس‌پذیر.',
                'price': Decimal('699000'),
                'price_irr': 69900000,
                'cost': Decimal('350000'),
                'cost_irr': 35000000,
                'stock': 40,
                'injury_type': 'back',
                'brand': 'HooperZone',
                'sizes': STANDARD_SIZES,
                'material': 'شبکه، الاستیک',
                'is_featured': True,
            },
            {
                'name': 'شانه‌بند قابل تنظیم',
                'name_fa': 'شانه‌بند قابل تنظیم',
                'slug': 'adjustable-shoulder-brace',
                'category': 'shoulder-supports',
                'description': 'شانه‌بند با تنظیم فشار برای حمایت چرخشی.',
                'description_fa': 'شانه‌بند قابل تنظیم سپر مدیکال با فناوری حمایت چرخنده و باندهای تنظیم‌شونده.',
                'price': Decimal('599000'),
                'price_irr': 59900000,
                'cost': Decimal('300000'),
                'cost_irr': 30000000,
                'stock': 60,
                'injury_type': 'shoulder',
                'brand': 'HooperZone',
                'sizes': STANDARD_SIZES,
                'material': 'نئوپرین',
            },
            {
                'name': 'حمایت آرنج تنیس',
                'name_fa': 'حمایت آرنج تنیس',
                'slug': 'tennis-elbow-support',
                'category': 'wrist-elbow',
                'description': 'فشار هدفمند برای آرنج تنیس و درد آرنج گلفر.',
                'description_fa': 'حمایت آرنج تنیس با فشار متمرکز بر نقطه آسیب‌دیده برای کاهش درد.',
                'price': Decimal('299000'),
                'price_irr': 29900000,
                'cost': Decimal('150000'),
                'cost_irr': 15000000,
                'stock': 80,
                'injury_type': 'elbow',
                'brand': 'MediPro',
                'material': 'نایلون، رابر',
            },
            {
                'name': 'تثبیت‌کننده مچ دست',
                'name_fa': 'تثبیت‌کننده مچ دست',
                'slug': 'wrist-stabilizer',
                'category': 'wrist-elbow',
                'description': 'حمایت سفت برای مچ دست و درد تونل کارپال.',
                'description_fa': 'تثبیت‌کننده مچ دست حرفه‌ای با ساختار سفت و جنس مناسب برای بهبودی سریع.',
                'price': Decimal('399000'),
                'price_irr': 39900000,
                'cost': Decimal('200000'),
                'cost_irr': 20000000,
                'stock': 65,
                'injury_type': 'wrist',
                'brand': 'HooperZone',
                'sizes': STANDARD_SIZES,
                'material': 'نئوپرین، آلومینیوم',
                'is_featured': True,
            },
            {
                'name': 'ساق‌بند فشاری',
                'name_fa': 'ساق‌بند فشاری',
                'slug': 'compression-calf-sleeve',
                'category': 'compression-wear',
                'description': 'فشار یاریگر برای بهبود گردش خون و کاهش خستگی عضلانی.',
                'description_fa': 'بند کشی فشاری تدریجی ساق پا برای بهبود گردش خون و کاهش خستگی عضلانی در طول ورزش.',
                'price': Decimal('329000'),
                'price_irr': 32900000,
                'cost': Decimal('170000'),
                'cost_irr': 17000000,
                'stock': 90,
                'injury_type': 'general',
                'brand': 'MediPro',
                'sizes': STANDARD_SIZES,
                'material': 'نایلون، اسپانکس',
            },
            {
                'name': 'رولر فوم بهبودی',
                'name_fa': 'رولر فوم بهبودی',
                'slug': 'recovery-foam-roller',
                'category': 'compression-wear',
                'description': 'رولر فوم چگال برای رهایی میوفاسچیال و بهبود عضلانی.',
                'description_fa': 'رولر فوم بهبودی حرفه‌ای با چگالی بالا برای رهایی میوفاسچیال و ارتقای بهبودی عضلانی.',
                'price': Decimal('449000'),
                'price_irr': 44900000,
                'cost': Decimal('220000'),
                'cost_irr': 22000000,
                'stock': 45,
                'injury_type': 'general',
                'brand': 'HooperZone',
                'material': 'اورا فوم',
            },
            {
                'name': 'کمره سینه‌ای ورزشی',
                'name_fa': 'کمره سینه‌ای ورزشی',
                'slug': 'sports-chest-brace',
                'category': 'shoulder-supports',
                'description': 'حمایت سینه‌ای برای ورزش‌های بالینی و پیشگیری از آسیب.',
                'description_fa': 'کمره سینه‌ای ورزشی مدرن با طراحی کم‌وزن و گنانسیون افقی برای حداکثر تنفس.',
                'price': Decimal('749000'),
                'price_irr': 74900000,
                'cost': Decimal('380000'),
                'cost_irr': 38000000,
                'stock': 35,
                'injury_type': 'shoulder',
                'brand': 'MediPro',
                'sizes': STANDARD_SIZES,
                'material': 'فایبرر، الاستیک',
                'discount_price': Decimal('649000'),
                'discount_price_irr': 64900000,
            },
            {
                'name': 'استابیلایزر کامل مچ پا',
                'name_fa': 'استابیلایزر کامل مچ پا',
                'slug': 'full-ankle-stabilizer',
                'category': 'ankle-supports',
                'description': 'استابیلایزر کامل مچ پا با قابلیت جلوگیری از چرخش و کشیدگی.',
                'description_fa': 'استابیلایزر کامل مچ پا با فناوری قفل‌گذاری و حمایت سه‌بعدی برای جلوگیری از آسیب مجدد.',
                'price': Decimal('399000'),
                'price_irr': 39900000,
                'cost': Decimal('200000'),
                'cost_irr': 20000000,
                'stock': 55,
                'injury_type': 'ankle',
                'brand': 'HooperZone',
                'sizes': STANDARD_SIZES,
                'material': 'نئوپرین، تایل',
            },
        ]

        for prod_data in products_data:
            category_slug = prod_data.pop('category')
            sizes = prod_data.pop('sizes', [])
            product, created = Product.objects.get_or_create(
                slug=prod_data['slug'],
                defaults={**prod_data, 'category': categories[category_slug]}
            )
            if not created:
                for key, value in prod_data.items():
                    setattr(product, key, value)
                product.category = categories[category_slug]
                product.save()
            set_demo_sizes(product, sizes, prod_data.get('stock', 0))
            self.stdout.write(f'  {"Created" if created else "Updated"} product: {product.name}')

        self.stdout.write(self.style.SUCCESS('Persian seed data created successfully!'))
