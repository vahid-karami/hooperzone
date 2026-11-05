from django.core.management.base import BaseCommand

from products.models import Product, SizeGuide, validate_size_guide_table

CM = "cm"

# Starter guides staff can pick or edit in the admin portal. Created once by name; never overwritten.
GUIDES = [
    {
        "name": "Knee supports",
        "categories": ["knee-braces"],
        "title_fa": "راهنمای سایز زانوبند",
        "title_en": "Knee support size guide",
        "how_to_measure_fa": (
            "ایستاده و با زانوی کمی خم، با متر خیاطی اندازه بگیرید.\n"
            "۱. دور ران را ۱۴ سانتی‌متر بالای وسط کشکک زانو.\n"
            "۲. دور ساق را ۱۲ سانتی‌متر پایین وسط کشکک.\n"
            "اگر بین دو سایز هستید، سایز کوچک‌تر حمایت محکم‌تری می‌دهد."
        ),
        "how_to_measure_en": (
            "Stand with the knee slightly bent and use a tape measure.\n"
            "1. Thigh: 14 cm above the middle of the kneecap.\n"
            "2. Calf: 12 cm below the middle of the kneecap.\n"
            "Between two sizes? The smaller one gives firmer support."
        ),
        "columns": [
            {"label_fa": "دور ران", "label_en": "Thigh", "unit": CM},
            {"label_fa": "دور ساق", "label_en": "Calf", "unit": CM},
        ],
        "rows": [
            {"size": "S", "values": ["38-43", "28-33"]},
            {"size": "M", "values": ["43-48", "33-38"]},
            {"size": "L", "values": ["48-53", "38-43"]},
            {"size": "XL", "values": ["53-58", "43-48"]},
        ],
    },
    {
        "name": "Ankle supports",
        "categories": ["ankle-supports"],
        "title_fa": "راهنمای سایز مچ‌بند پا",
        "title_en": "Ankle support size guide",
        "how_to_measure_fa": "دور مچ پا را درست بالای برجستگی استخوان قوزک اندازه بگیرید.",
        "how_to_measure_en": "Measure around the ankle just above the ankle bone.",
        "columns": [{"label_fa": "دور مچ پا", "label_en": "Ankle", "unit": CM}],
        "rows": [
            {"size": "S", "values": ["18-21"]},
            {"size": "M", "values": ["21-24"]},
            {"size": "L", "values": ["24-27"]},
            {"size": "XL", "values": ["27-30"]},
        ],
    },
    {
        "name": "Back supports",
        "categories": ["back-supports"],
        "title_fa": "راهنمای سایز کمربند طبی",
        "title_en": "Back support size guide",
        "how_to_measure_fa": "دور کمر را ایستاده و بدون لباس ضخیم، در امتداد ناف اندازه بگیرید.",
        "how_to_measure_en": "Measure around the waist at the navel, standing, without thick clothing.",
        "columns": [{"label_fa": "دور کمر", "label_en": "Waist", "unit": CM}],
        "rows": [
            {"size": "S", "values": ["70-85"]},
            {"size": "M", "values": ["85-100"]},
            {"size": "L", "values": ["100-115"]},
            {"size": "XL", "values": ["115-130"]},
        ],
    },
    {
        "name": "Shoulder supports",
        "categories": ["shoulder-supports"],
        "title_fa": "راهنمای سایز شانه‌بند",
        "title_en": "Shoulder support size guide",
        "how_to_measure_fa": "دور بازو را در پهن‌ترین قسمت، حدود ۱۰ سانتی‌متر پایین شانه اندازه بگیرید.",
        "how_to_measure_en": "Measure around the upper arm at its widest, about 10 cm below the shoulder.",
        "columns": [{"label_fa": "دور بازو", "label_en": "Upper arm", "unit": CM}],
        "rows": [
            {"size": "S", "values": ["24-28"]},
            {"size": "M", "values": ["28-32"]},
            {"size": "L", "values": ["32-36"]},
            {"size": "XL", "values": ["36-40"]},
        ],
    },
    {
        "name": "Wrist and elbow supports",
        "categories": ["wrist-elbow"],
        "title_fa": "راهنمای سایز مچ‌بند و آرنج‌بند",
        "title_en": "Wrist and elbow support size guide",
        "how_to_measure_fa": "مچ‌بند: دور مچ دست درست پایین کف دست.\nآرنج‌بند: دور ساعد ۵ سانتی‌متر پایین آرنج.",
        "how_to_measure_en": "Wrist: around the wrist just below the palm.\nElbow: around the forearm 5 cm below the elbow.",
        "columns": [
            {"label_fa": "دور مچ دست", "label_en": "Wrist", "unit": CM},
            {"label_fa": "دور ساعد", "label_en": "Forearm", "unit": CM},
        ],
        "rows": [
            {"size": "S", "values": ["13-15", "20-23"]},
            {"size": "M", "values": ["15-17", "23-26"]},
            {"size": "L", "values": ["17-19", "26-29"]},
            {"size": "XL", "values": ["19-21", "29-32"]},
        ],
    },
    {
        "name": "Compression wear",
        "categories": ["compression-wear"],
        "title_fa": "راهنمای سایز پوشاک فشاری",
        "title_en": "Compression wear size guide",
        "how_to_measure_fa": "دور ساق پا را در پهن‌ترین قسمت اندازه بگیرید.",
        "how_to_measure_en": "Measure around the calf at its widest point.",
        "columns": [{"label_fa": "دور ساق", "label_en": "Calf", "unit": CM}],
        "rows": [
            {"size": "S", "values": ["28-33"]},
            {"size": "M", "values": ["33-38"]},
            {"size": "L", "values": ["38-43"]},
            {"size": "XL", "values": ["43-48"]},
        ],
    },
]


class Command(BaseCommand):
    help = "Create the starter size guides (once). --attach links them to sized products that have none."

    def add_arguments(self, parser):
        parser.add_argument("--attach", action="store_true", help="Give matching products their category's guide")

    def handle(self, *args, attach=False, **kwargs):
        created = attached = 0
        for data in GUIDES:
            categories = data["categories"]
            fields = {k: v for k, v in data.items() if k not in ("name", "categories")}
            validate_size_guide_table(fields["columns"], fields["rows"])
            guide, was_created = SizeGuide.objects.get_or_create(name=data["name"], defaults=fields)
            created += was_created
            if attach:
                attached += Product.objects.filter(
                    category__slug__in=categories, size_guide__isnull=True, sizes__isnull=False
                ).distinct().update(size_guide=guide)
        self.stdout.write(f"Size guides: {created} created, {attached} products linked.")
