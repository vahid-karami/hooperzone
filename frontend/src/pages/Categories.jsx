import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Breadcrumbs from '../components/Breadcrumbs';
import Icon from '../components/Icon';
import { Skeleton } from '../components/Skeletons';
import { BODY_PARTS } from '../utils/bodyParts';
import { useCategories, useSports, sportName } from '../utils/catalog';
import { toPersianNumber } from '../hooks/useLanguage';
import { usePageMeta } from '../utils/seo';

export default function Categories() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const categories = useCategories();
  const sports = useSports();
  const loading = categories.length === 0;

  const title = t('categories.title', 'دسته‌بندی محصولات');
  usePageMeta({ title, description: t('categories.description') });

  const localizedName = (c) => (lang === 'fa' && c.name_fa) || c.name;
  const localizedDesc = (c) => (lang === 'fa' && c.description_fa) || c.description;

  return (
    <div className="categories-page">
      <div className="container">
        <Breadcrumbs items={[{ to: '/', label: t('common.home') }, { label: title }]} />

        <header className="listing-banner">
          <div className="listing-banner-copy">
            <h1>{title}</h1>
            <p>{t('categories.intro', 'بند طبی مناسب خود را بر اساس نوع محصول، عضو بدن یا ورزش پیدا کنید.')}</p>
          </div>
        </header>

        <section className="category-section" aria-labelledby="types-title">
          <h2 id="types-title" className="section-title">{t('home.shopByType', 'خرید بر اساس نوع محصول')}</h2>
          <div className="category-grid">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="category-card" aria-hidden="true">
                    <Skeleton className="category-card-img" />
                    <div className="category-card-body">
                      <Skeleton style={{ width: '60%', height: '1.3rem' }} />
                      <Skeleton style={{ width: '90%', height: '0.9rem' }} />
                    </div>
                  </div>
                ))
              : categories.map((c) => (
                  <Link key={c.id} to={`/products?category=${c.slug}`} className="category-card">
                    <div className="category-card-img">
                      {c.image ? <img src={c.image} alt="" loading="lazy" /> : <Icon name="box" size={48} strokeWidth={1.2} />}
                    </div>
                    <div className="category-card-body">
                      <h3>{localizedName(c)}</h3>
                      {localizedDesc(c) && <p>{localizedDesc(c)}</p>}
                      <div className="category-card-foot">
                        <span>{t('products.productsCount', { count: num(c.product_count) })}</span>
                        <span className="link-arrow">
                          {t('categories.viewProducts', 'مشاهده محصولات')} <Icon name="arrowLeft" size={16} />
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
          </div>
        </section>

        <section className="category-section" aria-labelledby="parts-title">
          <h2 id="parts-title" className="section-title">{t('home.shopByBodyPart')}</h2>
          <div className="part-grid">
            {BODY_PARTS.map((p) => (
              <Link key={p.key} to={`/products?injury_type=${p.key}`} className="part-tile">
                <strong>{lang === 'fa' ? p.fa : p.en}</strong>
                <span>{lang === 'fa' ? p.blurbFa : p.blurbEn}</span>
                <Icon name="chevronLeft" size={18} className="flip-ltr" />
              </Link>
            ))}
          </div>
        </section>

        {sports.length > 0 && (
          <section className="category-section" aria-labelledby="sports-title">
            <h2 id="sports-title" className="section-title">{t('home.shopBySport', 'خرید بر اساس ورزش')}</h2>
            <div className="sport-grid">
              {sports.map((s) => (
                <Link key={s.slug} to={`/products?sport=${s.slug}`} className="sport-tile">
                  <div className="sport-tile-img">
                    {s.cover_image ? <img src={s.cover_image} alt="" loading="lazy" /> : <Icon name="box" size={36} strokeWidth={1.2} />}
                  </div>
                  <strong>{sportName(s, lang)}</strong>
                  <span>{t('products.productsCount', { count: num(s.product_count) })}</span>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
