import { useTranslation } from 'react-i18next';
import Icon from './Icon';

const PERKS = [
  { icon: 'shield', key: 'authentic', fa: 'اصالت کالا تضمین‌شده' },
  { icon: 'truck', key: 'shipping', fa: 'ارسال سریع به سراسر کشور' },
  { icon: 'headset', key: 'support', fa: 'مشاوره تخصصی انتخاب سایز و مدل' },
];

// Shared shell for login/register: form on the start side, photo panel on the end side.
export default function AuthLayout({ title, subtitle, children, footer }) {
  const { t } = useTranslation();

  return (
    <div className="auth-split">
      <section className="auth-pane">
        <div className="auth-pane-inner">
          <header className="auth-head">
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
          </header>
          {children}
          {footer && <p className="auth-switch">{footer}</p>}
        </div>
      </section>

      <aside className="auth-visual" aria-hidden="true">
        <img src={`${import.meta.env.BASE_URL}images/auth/login.jpg`} alt="" loading="eager" decoding="async" />
        <div className="auth-visual-copy">
          <p className="auth-visual-title">{t('auth.visualTitle', 'حمایت از هر حرکت')}</p>
          <ul>
            {PERKS.map((perk) => (
              <li key={perk.key}>
                <Icon name={perk.icon} size={20} />
                <span>{t(`auth.perk.${perk.key}`, perk.fa)}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}
