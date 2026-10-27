import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Breadcrumbs from '../../components/Breadcrumbs';
import Icon from '../../components/Icon';
import Price from '../../components/Price';
import { toPersianNumber } from '../../hooks/useLanguage';
import { telHref, useShopInfo } from '../../utils/shopInfo';
import { usePageMeta } from '../../utils/seo';

export const INFO_PAGES = ['about', 'contact', 'faq', 'shipping', 'returns', 'terms', 'privacy'];

function Sections({ page }) {
  const { t } = useTranslation();
  const sections = t(`info.${page}.sections`, { returnObjects: true });
  if (!Array.isArray(sections)) return null;
  return sections.map((s) => (
    <section key={s.h} className="info-section">
      <h2>{s.h}</h2>
      {s.p.length > 1 ? (
        <ul>{s.p.map((line) => <li key={line}>{line}</li>)}</ul>
      ) : (
        <p>{s.p[0]}</p>
      )}
    </section>
  ));
}

function Contact({ shop, num }) {
  const { t } = useTranslation();
  const rows = [
    shop.store_phone && { icon: 'phone', label: t('info.contact.phone'), value: <a href={telHref(shop.store_phone)} dir="ltr">{num(shop.store_phone)}</a> },
    shop.whatsapp && { icon: 'send', label: 'WhatsApp', value: <a href={`https://wa.me/${String(shop.whatsapp).replace(/\D/g, '').replace(/^0/, '98')}`} target="_blank" rel="noreferrer" dir="ltr">{num(shop.whatsapp)}</a> },
    shop.store_email && { icon: 'mail', label: t('info.contact.email'), value: <a href={`mailto:${shop.store_email}`} dir="ltr">{shop.store_email}</a> },
    shop.store_address && { icon: 'location', label: t('info.contact.address'), value: <address>{shop.store_address}</address> },
    { icon: 'clock', label: t('info.contact.hours'), value: shop.working_hours || t('info.contact.defaultHours') },
    shop.instagram && { icon: 'instagram', label: 'Instagram', value: <a href={`https://instagram.com/${shop.instagram}`} target="_blank" rel="noreferrer" dir="ltr">@{shop.instagram}</a> },
    shop.telegram && { icon: 'send', label: 'Telegram', value: <a href={`https://t.me/${shop.telegram}`} target="_blank" rel="noreferrer" dir="ltr">@{shop.telegram}</a> },
  ].filter(Boolean);

  return (
    <>
      <ul className="contact-cards">
        {rows.map((r) => (
          <li key={r.label}>
            <span className="contact-icon"><Icon name={r.icon} size={22} /></span>
            <span className="contact-label">{r.label}</span>
            <span className="contact-value">{r.value}</span>
          </li>
        ))}
      </ul>
      <p className="info-note">{t('info.contact.orderHelp')}</p>
    </>
  );
}

function Shipping({ shop, lang, num }) {
  const { t } = useTranslation();
  const methods = shop.shipping_methods || [];
  return (
    <>
      {methods.length > 0 && (
        <div className="table-wrap info-table-wrap">
          <table className="info-table">
            <thead>
              <tr><th>{t('info.shipping.tableMethod')}</th><th>{t('info.shipping.tableTime')}</th><th>{t('info.shipping.tableFee')}</th></tr>
            </thead>
            <tbody>
              {methods.map((m) => (
                <tr key={m.code}>
                  <td>{lang === 'fa' ? m.label_fa : m.label_en}</td>
                  <td>{t('checkout.deliveryDays', { days: num(String(m.days).replace('-', lang === 'fa' ? ' تا ' : '–')) })}</td>
                  <td><Price amount={m.fee} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Sections page="shipping" />
    </>
  );
}

function Faq() {
  const { t } = useTranslation();
  const items = t('info.faq.items', { returnObjects: true });
  if (!Array.isArray(items)) return null;
  return (
    <div className="faq-list">
      {items.map((item) => (
        <details key={item.q} className="faq-item">
          <summary>
            {item.q}
            <Icon name="chevronDown" size={18} />
          </summary>
          <p>{item.a}</p>
        </details>
      ))}
    </div>
  );
}

export default function InfoPage({ page }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const shop = useShopInfo();
  const title = t(`info.${page}.title`);

  usePageMeta({ title, description: t(`info.${page}.lead`) });

  const body = {
    contact: <Contact shop={shop} num={num} />,
    shipping: <Shipping shop={shop} lang={lang} num={num} />,
    faq: <Faq />,
  }[page] || <Sections page={page} />;

  return (
    <div className="info-page">
      <div className="container">
        <Breadcrumbs items={[{ to: '/', label: t('common.home') }, { label: title }]} />
        <div className="info-layout">
          <aside className="info-nav">
            <h2 className="info-nav-title">{t('info.navTitle')}</h2>
            <nav aria-label={t('info.navTitle')}>
              {INFO_PAGES.map((p) => (
                <NavLink key={p} to={`/${p}`} className={({ isActive }) => `info-link ${isActive ? 'active' : ''}`}>
                  {t(`info.nav.${p}`)}
                </NavLink>
              ))}
            </nav>
          </aside>
          <article className="info-content">
            <h1 className="display-title">{title}</h1>
            <p className="info-lead">{t(`info.${page}.lead`)}</p>
            {body}
            {['terms', 'privacy', 'returns'].includes(page) && <p className="info-updated">{t('info.updated')}</p>}
          </article>
        </div>
      </div>
    </div>
  );
}
