import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BODY_PARTS } from '../utils/bodyParts';
import Icon from './Icon';
import Logo from './Logo';

export default function Footer() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const { pathname } = useLocation();
  // Solar Hijri year for Persian (e.g. ۱۴۰۵), Gregorian otherwise.
  const year = new Intl.DateTimeFormat(lang === 'fa' ? 'fa-IR' : 'en-US', { year: 'numeric' }).format(new Date());

  // The admin portal is a work area; no shop footer there.
  if (pathname.startsWith('/admin-portal')) return null;

  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div className="footer-brand">
          <Logo />
          <p>{t('footer.about', 'هوپرزون فروشگاه تخصصی ساپورت‌ها و بریس‌های ورزشی و طبی است؛ برای پیشگیری از آسیب، همراهی در دوران درمان و بازگشت مطمئن به فعالیت.')}</p>
          <a className="footer-phone" href="tel:+982112345678">
            <Icon name="phone" size={20} />
            <span dir="ltr">۰۲۱-۱۲۳۴۵۶۷۸</span>
          </a>
          <p className="footer-hours">{t('footer.hours', 'شنبه تا پنج‌شنبه، ۹ تا ۱۸')}</p>
        </div>

        <div className="footer-col">
          <h4>{t('home.shopByBodyPart')}</h4>
          <ul>
            {BODY_PARTS.slice(0, 6).map((p) => (
              <li key={p.key}>
                <Link to={`/products?injury_type=${p.key}`}>{lang === 'fa' ? p.fa : p.en}</Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="footer-col">
          <h4>{t('footer.customerService', 'خدمات مشتریان')}</h4>
          <ul>
            <li><Link to="/orders">{t('footer.trackOrder', 'پیگیری سفارش')}</Link></li>
            <li><Link to="/profile">{t('header.myAccount')}</Link></li>
            <li><Link to="/favorites">{t('header.myFavorites')}</Link></li>
            <li><Link to="/cart">{t('common.cart')}</Link></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>{t('footer.whyUs', 'چرا هوپرزون')}</h4>
          <ul className="footer-checks">
            <li><Icon name="check" size={16} /> {t('footer.genuine', 'ضمانت اصالت کالا')}</li>
            <li><Icon name="check" size={16} /> {t('footer.returns', '۷ روز ضمانت بازگشت')}</li>
            <li><Icon name="check" size={16} /> {t('footer.securePay', 'پرداخت امن زرین‌پال و آیدی‌پی')}</li>
            <li><Icon name="check" size={16} /> {t('footer.advice', 'مشاوره انتخاب سایز')}</li>
          </ul>
        </div>

        <div className="footer-col footer-newsletter">
          <h4>{t('footer.newsletter', 'خبرنامه')}</h4>
          <p>{t('footer.newsletterDesc', 'از تخفیف‌ها و راهنماهای تازه باخبر شوید.')}</p>
          <form className="newsletter-form" onSubmit={(e) => e.preventDefault()}>
            <input type="email" placeholder={t('footer.emailPlaceholder', 'ایمیل شما')} aria-label={t('footer.emailPlaceholder', 'ایمیل شما')} dir="ltr" />
            <button type="submit" className="btn btn-primary btn-sm">{t('footer.subscribe', 'عضویت')}</button>
          </form>
        </div>
      </div>

      <div className="footer-bottom">
        <div className="container footer-bottom-inner">
          <p>© {year} {t('footer.copyright', 'هوپرزون. تمامی حقوق محفوظ است.')}</p>
          <div className="payment-badges" aria-label={t('footer.paymentMethods', 'روش‌های پرداخت')}>
            <span>شتاب</span>
            <span>زرین‌پال</span>
            <span>آیدی‌پی</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
