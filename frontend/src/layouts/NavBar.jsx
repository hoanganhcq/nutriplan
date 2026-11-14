import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Trang chủ' },
  { to: '/chup-bua-an', label: 'Chụp bữa ăn' },
  { to: '/thuc-don', label: 'Thực đơn' },
  { to: '/nhat-ky', label: 'Nhật ký' },
  { to: '/gia-dinh', label: 'Gia đình' },
];

export default function NavBar() {
  return (
    <nav className="nav" aria-label="Điều hướng chính">
      {NAV_ITEMS.map(({ to, label }) => (
        <NavLink key={to} to={to} end={to === '/'} className="nav__link">
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
