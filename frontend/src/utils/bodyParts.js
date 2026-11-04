// Body areas the shop is organised by (matches Product.INJURY_TYPE_CHOICES).
export const BODY_PARTS = [
  { key: 'knee', fa: 'زانو', en: 'Knee', blurbFa: 'زانوبند ساده، کشی و مفصل‌دار', blurbEn: 'Braces, sleeves & straps' },
  { key: 'ankle', fa: 'مچ پا', en: 'Ankle', blurbFa: 'قوزک‌بند و تثبیت‌کننده', blurbEn: 'Stabilizers & sleeves' },
  { key: 'back', fa: 'کمر', en: 'Back', blurbFa: 'کمربند طبی و کرست کمر', blurbEn: 'Lumbar supports' },
  { key: 'shoulder', fa: 'شانه', en: 'Shoulder', blurbFa: 'شانه‌بند و قفسه‌بند', blurbEn: 'Shoulder braces' },
  { key: 'elbow', fa: 'آرنج', en: 'Elbow', blurbFa: 'آرنج‌بند تنیس و گلف', blurbEn: 'Tennis elbow supports' },
  { key: 'wrist', fa: 'مچ دست', en: 'Wrist', blurbFa: 'مچ‌بند و اسپلینت', blurbEn: 'Wrist stabilizers' },
  { key: 'general', fa: 'بهبودی و پوشاک فشاری', en: 'Recovery', blurbFa: 'ساق‌بند فشاری و وسایل بهبودی', blurbEn: 'Compression & recovery' },
];

export const bodyPartLabel = (key, lang = 'fa') => {
  const part = BODY_PARTS.find((p) => p.key === key);
  if (!part) return key;
  return lang === 'fa' ? part.fa : part.en;
};

export const localized = (obj, field, lang) =>
  (lang === 'fa' ? obj?.[`${field}_fa`] : null) || obj?.[`${field}_localized`] || obj?.[field] || '';
