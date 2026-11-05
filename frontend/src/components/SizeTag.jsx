import { useTranslation } from 'react-i18next';

// "سایز: M" next to a cart or order line. Renders nothing for size-less products.
export default function SizeTag({ label }) {
  const { t } = useTranslation();
  if (!label) return null;
  return (
    <span className="size-tag">
      {t('product.size')}: <bdi>{label}</bdi>
    </span>
  );
}
