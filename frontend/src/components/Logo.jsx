import { Link } from 'react-router-dom';

// HooperZone logo ("HZ" mark + HOOPER ZONE). Navy on transparent; logo-white.png is for dark backgrounds.
export default function Logo({ onClick }) {
  return (
    <Link to="/" className="brand" aria-label="هوپرزون - صفحه اصلی" onClick={onClick}>
      <img
        className="brand-logo"
        src={`${import.meta.env.BASE_URL}images/brand/logo.png`}
        alt="HooperZone"
        width="685"
        height="197"
        decoding="async"
      />
    </Link>
  );
}
