import { NavLink } from 'react-router-dom';
import Icon from '../components/Icon.jsx';

const items = [
  { to: '/', label: 'Trang chủ', icon: 'home' },
  { to: '/chup-bua-an', label: 'Chụp bữa ăn', icon: 'camera' },
  { to: '/thuc-don', label: 'Thực đơn', icon: 'menu' },
  { to: '/nhat-ky', label: 'Nhật ký', icon: 'diary' },
  { to: '/gia-dinh', label: 'Gia đình', icon: 'family' },
  { to: '/cai-dat', label: 'Cài đặt', icon: 'settings' },
];

export default function NavBar({ mobile = false }) {
  return <div className="nav">{items.filter((item) => !mobile || item.to !== '/cai-dat').map(({ to, label, icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav__link${isActive ? ' active' : ''}`}><Icon name={icon} /><span>{label}</span></NavLink>)}</div>;
}
