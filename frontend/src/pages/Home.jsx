import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import ProductCard from '../components/ProductCard';
import { ProductCardSkeleton } from '../components/Skeletons';
import Price from '../components/Price';
import Icon from '../components/Icon';
import { BODY_PARTS, localized } from '../utils/bodyParts';
import { usePageMeta } from '../utils/seo';
import { useCategories, useSports, sportName } from '../utils/catalog';

const imageOf = (product) => product?.primary_image?.thumbnail || product?.primary_image?.image;

export default function Home() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const [products, setProducts] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [loading, setLoading] = useState(true);
  const categories = useCategories();
  const sports = useSports();
  const rootRef = useRef(null);

  usePageMeta({
    title: t('home.metaTitle', 'ساپورت‌ها و بریس‌های ورزشی و طبی'),
    description: t('home.metaDescription', 'زانوبند، قوزک‌بند، کمربند طبی و پوشاک فشاری برای پیشگیری، درمان و عملکرد بهتر.'),
  });

  useEffect(() => {
    Promise.all([apiClient.get(ENDPOINTS.products), apiClient.get(ENDPOINTS.featuredProducts)])
      .then(([allRes, featuredRes]) => {
        setProducts(allRes.data.results || allRes.data);
        setFeatured(featuredRes.data.results || featuredRes.data);
      })
      .catch((error) => console.error('Failed to load home page data:', error))
      .finally(() => setLoading(false));
  }, []);

  // Fade-and-rise for [data-reveal] blocks as they enter the viewport (skipped for reduced motion).
  useEffect(() => {
    const root = rootRef.current;
    if (!root || loading) return undefined;
    const items = root.querySelectorAll('[data-reveal]');
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      items.forEach((el) => el.classList.add('in'));
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      }),
      { rootMargin: '0px 0px -8% 0px' },
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [loading, sports.length, categories.length]);

  // First product image per body part / category, used as the tile photo.
  const byInjury = useMemo(() => {
    const map = {};
    products.forEach((p) => {
      if (!map[p.injury_type] && imageOf(p)) map[p.injury_type] = p;
    });
    return map;
  }, [products]);

  const bodyParts = BODY_PARTS.filter((p) => byInjury[p.key]);

  const byCategoryName = useMemo(() => {
    const map = {};
    products.forEach((p) => {
      if (!map[p.category_name] && imageOf(p)) map[p.category_name] = p;
    });
    return map;
  }, [products]);

  const categoryTiles = categories.map((c) => ({
    key: c.slug,
    to: `/products?category=${c.slug}`,
    title: (lang === 'fa' && c.name_fa) || c.name,
    subtitle: t('products.productsCount', { count: c.product_count }),
    image: c.image || imageOf(byCategoryName[c.name]),
  }));

  const sportTiles = sports
    .filter((s) => s.product_count > 0)
    .map((s) => ({
      key: s.slug,
      to: `/products?sport=${s.slug}`,
      title: sportName(s, lang),
      subtitle: t('products.productsCount', { count: s.product_count }),
      image: s.cover_image,
    }));

  const guides = [
    {
      key: 'knee',
      title: t('home.guideKneeTitle', 'راهنمای زانودرد'),
      text: t('home.guideKneeText', 'علت‌ها، علائم و ساپورت مناسب برای هر مرحله.'),
      to: '/products?injury_type=knee',
      image: imageOf(byInjury.knee),
    },
    {
      key: 'back',
      title: t('home.guideBackTitle', 'رهایی از کمردرد'),
      text: t('home.guideBackText', 'پشتیبانی از ستون فقرات در کار، رانندگی و ورزش.'),
      to: '/products?injury_type=back',
      image: imageOf(byInjury.back),
    },
    {
      key: 'ankle',
      title: t('home.guideAnkleTitle', 'پیچ‌خوردگی مچ پا'),
      text: t('home.guideAnkleText', 'از ثابت‌سازی اولیه تا بازگشت کامل به تمرین.'),
      to: '/products?injury_type=ankle',
      image: imageOf(byInjury.ankle),
    },
  ].filter((g) => g.image);

  const topSellers = (featured.length ? featured : products).slice(0, 4);

  const spotlight = topSellers[0];
  const spotlightName = spotlight && localized(spotlight, 'name', lang);

  return (
    <div className="home" ref={rootRef}>
      <section className="home2-hero">
        <div className="container home2-hero-grid">
          <div className="home2-hero-copy">
            <h1>{t('home.heroTitle', 'با خیال راحت به میدان برگرد')}</h1>
            <p>{t('home.heroText', 'ساپورت و بریس مناسب هر عضو و هر ورزش، همراه با مشاوره تخصصی انتخاب سایز.')}</p>
            <div className="home2-hero-actions">
              <a href="#sports" className="btn btn-primary btn-lg">{t('home.heroCta', 'خرید بر اساس ورزش')}</a>
              <a href="tel:+982112345678" className="btn btn-outline btn-lg">
                <Icon name="phone" size={18} /> {t('home.heroCta2', 'مشاوره رایگان')}
              </a>
            </div>
          </div>

          <div className="home2-hero-visual">
            <img src={`${import.meta.env.BASE_URL}images/home/hero.jpg`} alt="" fetchPriority="high" decoding="async" />
            {spotlight && (
              <Link to={`/products/${spotlight.slug}`} className="home2-spotlight">
                {imageOf(spotlight) && <img src={imageOf(spotlight)} alt="" decoding="async" />}
                <span className="home2-spotlight-text">
                  <small>{t('home.topSellers', 'پرفروش‌ترین‌ها')}</small>
                  <strong>{spotlightName}</strong>
                  <Price amount={spotlight.effective_price ?? spotlight.price} />
                </span>
              </Link>
            )}
          </div>
        </div>

        {bodyParts.length > 0 && (
          <div className="container">
            <nav className="home2-parts" aria-label={t('home.shopByBodyPart')}>
              <span className="home2-parts-label">{t('home.partsLabel', 'کدام عضو آسیب دیده؟')}</span>
              <div className="home2-parts-list">
                {bodyParts.map((p) => (
                  <Link key={p.key} to={`/products?injury_type=${p.key}`} className="home2-pill">
                    {lang === 'fa' ? p.fa : p.en}
                  </Link>
                ))}
              </div>
            </nav>
          </div>
        )}
      </section>

      {sportTiles.length > 0 && (
        <section className="band" id="sports">
          <div className="container">
            <header className="home2-head" data-reveal>
              <h2 className="section-title">{t('home.shopBySport', 'خرید بر اساس ورزش')}</h2>
              <p>{t('home.sportsText', 'ورزش خود را انتخاب کنید تا فقط محصولات مناسب آن را ببینید.')}</p>
            </header>
            <div className="home2-sports">
              {sportTiles.map((s) => (
                <Link key={s.key} to={s.to} className="home2-sport" data-reveal>
                  {s.image && <img src={s.image} alt="" loading="lazy" />}
                  <span className="home2-sport-label">
                    <strong>{s.title}</strong>
                    <small>{s.subtitle}</small>
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="band band-sky">
        <div className="container">
          <header className="home2-head home2-head-row" data-reveal>
            <h2 className="section-title">{t('home.topSellers', 'پرفروش‌ترین‌ها')}</h2>
            <Link to="/products" className="link-arrow">
              {t('home.viewAllProducts', 'همه محصولات')} <Icon name="arrowLeft" size={16} />
            </Link>
          </header>
          <div className="product-grid">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <ProductCardSkeleton key={i} />)
              : topSellers.map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        </div>
      </section>

      {categoryTiles.length > 0 && (
        <section className="band">
          <div className="container">
            <header className="home2-head home2-head-row" data-reveal>
              <h2 className="section-title">{t('home.shopByType', 'خرید بر اساس نوع محصول')}</h2>
              <Link to="/categories" className="link-arrow">
                {t('home.viewAllCategories', 'همه دسته‌ها')} <Icon name="arrowLeft" size={16} />
              </Link>
            </header>
            <div className="home2-types">
              {categoryTiles.map((c) => (
                <Link key={c.key} to={c.to} className="home2-type" data-reveal>
                  <span className="home2-type-img">
                    {c.image ? <img src={c.image} alt="" loading="lazy" /> : <Icon name="box" size={32} strokeWidth={1.4} />}
                  </span>
                  <strong>{c.title}</strong>
                  <small>{c.subtitle}</small>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {guides.length > 0 && (
        <section className="band band-sky">
          <div className="container">
            <header className="home2-head" data-reveal>
              <h2 className="section-title">{t('home.howWeHelp', 'هوپرزون چگونه کمک می‌کند')}</h2>
              <p>{t('home.howWeHelpText', 'از درد مزمن مفاصل تا آسیب‌های ورزشی؛ راه‌هایی را ببینید که به شما کمک می‌کنند فعال بمانید.')}</p>
            </header>
            <div className="home2-guides">
              {guides.map((g, i) => (
                <Link key={g.key} to={g.to} className={`home2-guide ${i === 0 ? 'is-lead' : ''}`} data-reveal>
                  <img src={g.image} alt="" loading="lazy" />
                  <span>
                    <strong>{g.title}</strong>
                    <small>{g.text}</small>
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="band band-tight">
        <div className="container">
          <div className="advice-banner" data-reveal>
            <div>
              <h2>{t('home.adviceTitle', 'در انتخاب سایز یا مدل مردد هستید؟')}</h2>
              <p>{t('home.adviceText', 'کارشناسان ما کمک می‌کنند ساپورتی را انتخاب کنید که دقیقاً به نیاز شما پاسخ می‌دهد.')}</p>
            </div>
            <a href="tel:+982112345678" className="btn btn-secondary btn-lg">
              <Icon name="phone" size={18} /> {t('home.adviceCta', 'تماس با کارشناس')}
            </a>
          </div>
        </div>
      </section>

      <section className="trust-bar">
        <div className="container trust-grid">
          {[
            { icon: 'truck', title: t('home.trustShipTitle', 'ارسال سریع'), text: t('home.trustShipText', 'ارسال به سراسر کشور با پست و تیپاکس') },
            { icon: 'card', title: t('home.trustPayTitle', 'پرداخت امن'), text: t('home.trustPayText', 'درگاه زرین‌پال و آیدی‌پی') },
            { icon: 'returns', title: t('home.trustReturnTitle', 'بازگشت آسان'), text: t('home.trustReturnText', '۷ روز ضمانت بازگشت کالا') },
            { icon: 'headset', title: t('home.trustSupportTitle', 'پشتیبانی تخصصی'), text: t('home.trustSupportText', 'مشاوره پیش و پس از خرید') },
          ].map((item) => (
            <div key={item.icon} className="trust-item">
              <Icon name={item.icon} size={28} strokeWidth={1.6} />
              <div>
                <strong>{item.title}</strong>
                <span>{item.text}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="band seo-block">
        <div className="container narrow">
          <h2 className="section-title">{t('home.aboutTitle', 'هوپرزون')}</h2>
          <p>
            {t('home.aboutText', 'ساپورت‌ها و پوشاک فشاری هوپرزون با پارچه‌های تنفس‌پذیر و فشار هدفمند، گردش خون را بهبود می‌دهند و به ثبات مفصل کمک می‌کنند؛ نتیجه، درد کمتر، ریکاوری سریع‌تر و اعتماد به نفس بیشتر در حرکت است. برای شروع، عضو بدن یا نوع محصول مورد نظرتان را انتخاب کنید.')}
          </p>
        </div>
      </section>
    </div>
  );
}
