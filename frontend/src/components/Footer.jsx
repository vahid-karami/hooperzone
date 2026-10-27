import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BODY_PARTS } from '../utils/bodyParts';
import { telHref, useShopInfo } from '../utils/shopInfo';
import { toPersianNumber } from '../hooks/useLanguage';
import Icon from './Icon';
import Logo from './Logo';

export default function Footer() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const { pathname } = useLocation();
  const shop = useShopInfo();
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
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
          {shop.store_phone && (
            <a className="footer-phone" href={telHref(shop.store_phone)}>
              <Icon name="phone" size={20} />
              <span dir="ltr">{num(shop.store_phone)}</span>
            </a>
          )}
          <p className="footer-hours">{shop.working_hours || t('footer.hours', 'شنبه تا پنج‌شنبه، ۹ تا ۱۸')}</p>
          {shop.store_email && <a className="footer-mail" href={`mailto:${shop.store_email}`} dir="ltr">{shop.store_email}</a>}
          {(shop.instagram || shop.telegram) && (
            <div className="footer-social">
              {shop.instagram && (
                <a href={`https://instagram.com/${shop.instagram}`} target="_blank" rel="noreferrer" aria-label="Instagram"><Icon name="instagram" size={20} /></a>
              )}
              {shop.telegram && (
                <a href={`https://t.me/${shop.telegram}`} target="_blank" rel="noreferrer" aria-label="Telegram"><Icon name="send" size={20} /></a>
              )}
            </div>
          )}
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
            <li><Icon name="check" size={16} /> {t('footer.securePay', 'پرداخت امن از درگاه زرین‌پال')}</li>
            <li><Icon name="check" size={16} /> {t('footer.advice', 'مشاوره انتخاب سایز')}</li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>{t('footer.info', 'اطلاعات')}</h4>
          <ul>
            {['about', 'contact', 'faq', 'shipping', 'returns', 'terms', 'privacy'].map((page) => (
              <li key={page}><Link to={`/${page}`}>{t(`info.nav.${page}`)}</Link></li>
            ))}
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <div className="container footer-bottom-inner">
          <p>© {year} {t('footer.copyright', 'هوپرزون. تمامی حقوق محفوظ است.')}</p>
          {(shop.enamad_html || shop.samandehi_html) && (
            // Badge code is pasted by staff from enamad.ir / samandehi.ir in the admin portal.
            <div className="trust-badges">
              {shop.enamad_html && <div dangerouslySetInnerHTML={{ __html: shop.enamad_html }} />}
              {shop.samandehi_html && <div dangerouslySetInnerHTML={{ __html: shop.samandehi_html }} />}
            </div>
          )}
          <div className="payment-badges" aria-label={t('footer.paymentMethods', 'روش‌های پرداخت')}>
            <span>{t('footer.shetab', 'شتاب')}</span>
            <span>{t('footer.zarinpal', 'زرین‌پال')}</span>
            <span>{t('footer.secureGateway', 'درگاه امن بانکی')}</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
