import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import ProductCard from '../components/ProductCard';
import { ProductCardSkeleton } from '../components/Skeletons';
import HeroSlider from '../components/HeroSlider';
import Icon from '../components/Icon';
import { BODY_PARTS } from '../utils/bodyParts';
import { useShopInfo, telHref } from '../utils/shopInfo';
import { usePageMeta } from '../utils/seo';
import { useCategories, useSports, sportName } from '../utils/catalog';
import { toPersianNumber } from '../hooks/useLanguage';
import useReveal from '../hooks/useReveal';

const imageOf = (product) => product?.primary_image?.thumbnail || product?.primary_image?.image;

export default function Home() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const [products, setProducts] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [loading, setLoading] = useState(true);
  const categories = useCategories();
  const sports = useSports();
  const rootRef = useRef(null);
  const shop = useShopInfo();
  const phoneHref = shop.store_phone ? telHref(shop.store_phone) : 'tel:+982112345678';

  usePageMeta({
    title: t('home.metaTitle', 'زانوبند، مچ‌بند و بندهای طبی و ورزشی'),
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

  // Fade-and-rise for [data-reveal] blocks as they enter the viewport.
  useReveal(rootRef, [loading, sports.length, categories.length]);

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
    subtitle: t('products.productsCount', { count: num(c.product_count) }),
    image: c.thumbnail || c.image || imageOf(byCategoryName[c.name]),
    showOnHome: !!c.show_on_home,
  }));

  const sportTiles = sports
    .filter((s) => s.product_count > 0)
    .map((s) => ({
      key: s.slug,
      to: `/products?sport=${s.slug}`,
      title: sportName(s, lang),
      subtitle: t('products.productsCount', { count: num(s.product_count) }),
      image: s.cover_thumbnail || s.cover_image,
    }));

  // The ticker repeats short sport lists so one copy is always wider than the screen.
  const tickerItems = sportTiles.length
    ? Array.from({ length: Math.ceil(8 / sportTiles.length) }, () => sportTiles).flat()
    : [];

  const guides = [
    {
      key: 'knee',
      title: t('home.guideKneeTitle', 'راهنمای زانودرد'),
      text: t('home.guideKneeText', 'علت‌ها، نشانه‌ها و زانوبند مناسب برای هر مرحله.'),
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

  // Slogan slides: brand messages, not product categories (those live in the circles below).
  const slides = [
    {
      key: 'move',
      theme: 'photo',
      image: `${import.meta.env.BASE_URL}images/home/hero.webp`,
      srcSet: `${import.meta.env.BASE_URL}images/home/hero-800.webp 800w, ${import.meta.env.BASE_URL}images/home/hero.webp 1600w`,
      eyebrow: t('home.slide1Eyebrow', 'هوپرزون'),
      title: t('home.slide1Title', 'بهتر حرکت کن. قوی‌تر برگرد.'),
      text: t('home.slide1Text', 'زانوبند، مچ‌بند و کمربند طبی مناسب هر عضو و هر ورزش.'),
      cta: { label: t('home.slide1Cta', 'مشاهده محصولات'), to: '/products', icon: 'store' },
    },
    {
      key: 'comeback',
      theme: 'navy',
      eyebrow: t('home.slide2Eyebrow', 'کنار تو، از آسیب تا بازگشت'),
      title: t('home.slide2Title', 'آسیب، پایان بازی نیست.'),
      text: t('home.slide2Text', 'با محافظ درست، با خیال راحت به میدان برگرد.'),
      cta: { label: t('home.slide2Cta', 'مشاوره رایگان انتخاب اندازه'), href: phoneHref, icon: 'phone' },
    },
    {
      key: 'everyday',
      theme: 'teal',
      eyebrow: t('home.slide3Eyebrow', 'برای همه سنین'),
      title: t('home.slide3Title', 'هر روز، بدون درد.'),
      text: t('home.slide3Text', 'از تمرین حرفه‌ای تا پیاده‌روی روزانه، همراه تو هستیم.'),
      cta: { label: t('home.slide3Cta', 'خرید بر اساس ورزش'), href: '#sports' },
    },
  ];

  // Highlighted categories (chosen in the admin portal); every category if none is chosen yet.
  const highlighted = categoryTiles.filter((c) => c.showOnHome);
  const circles = highlighted.length ? highlighted : categoryTiles;

  return (
    <div className="home" ref={rootRef}>
      <section className="home2-hero">
        <div className="container">
          <HeroSlider slides={slides} />

          {circles.length > 0 && (
            <nav className="home-circles" aria-label={t('home.circlesLabel', 'دسته‌بندی‌های ویژه')}>
              {circles.map((c) => (
                <Link key={c.key} to={c.to} className="home-circle">
                  <span className="home-circle-img">
                    {c.image ? <img src={c.image} alt="" loading="lazy" /> : <Icon name="box" size={30} strokeWidth={1.5} />}
                  </span>
                  <span className="home-circle-label">{c.title}</span>
                </Link>
              ))}
              <Link to="/categories" className="home-circle is-all">
                <span className="home-circle-img"><Icon name="menu" size={28} /></span>
                <span className="home-circle-label">{t('home.viewAllCategories', 'همه دسته‌ها')}</span>
              </Link>
            </nav>
          )}
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
        <div className="sport-ticker" aria-label={t('home.tickerLabel', 'ورزش‌ها')}>
          {/* Two copies so the loop is seamless; the second is hidden from screen readers. */}
          {[0, 1].map((copy) => (
            <ul key={copy} className="sport-ticker-track" aria-hidden={copy === 1 || undefined}>
              {tickerItems.map((s, i) => (
                <li key={`${s.key}-${i}`}>
                  <Link to={s.to} tabIndex={copy === 1 || i >= sportTiles.length ? -1 : undefined}>{s.title}</Link>
                  <span className="sport-ticker-star" aria-hidden="true">✦</span>
                </li>
              ))}
              <li>
                <span>{t('home.tickerSlogan', 'بی‌وقفه ادامه بده')}</span>
                <span className="sport-ticker-star" aria-hidden="true">✦</span>
              </li>
            </ul>
          ))}
        </div>
      )}

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
              <h2>{t('home.adviceTitle', 'در انتخاب اندازه یا مدل مردد هستید؟')}</h2>
              <p>{t('home.adviceText', 'کارشناسان ما کمک می‌کنند محصولی را انتخاب کنید که دقیقاً به کار شما بیاید.')}</p>
            </div>
            <a href={phoneHref} className="btn btn-secondary btn-lg">
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
            {t('home.aboutText', 'بندهای طبی و پوشاک فشاری هوپرزون با پارچه‌های قابل تنفس و فشار یکنواخت، گردش خون را بهتر می‌کنند و از مفصل حمایت می‌کنند؛ نتیجه، درد کمتر، بهبودی سریع‌تر و حرکت با خیال راحت است. برای شروع، عضو بدن یا نوع محصول مورد نظرتان را انتخاب کنید.')}
          </p>
        </div>
      </section>
    </div>
  );
}
