import { Link, Outlet } from 'react-router-dom';
import NavBar from './NavBar.jsx';
import { useSession } from '../hooks/sessionContext.js';
import { service } from '../services/nutriplan.js';
import Icon from '../components/Icon.jsx';

export default function AppLayout() {
  const { session, setSession } = useSession();
  const initials = session?.name.trim().split(/\s+/).slice(-2).map((part) => part[0]).join('').toUpperCase();
  async function logout() { await service.logout(); setSession(null); }
  return <div className="app-shell"><a className="skip-link" href="#main-content">Đến nội dung chính</a><header className="app-header"><div className="app-header__inner"><Link className="brand" to="/"><span className="brand__mark"><Icon name="logo" size={22} /></span> NutriPlan</Link><NavBar /><div className="header-user"><Link to="/cai-dat" className="mobile-settings" aria-label="Cài đặt"><Icon name="settings" /></Link><span className="avatar avatar--small" aria-hidden="true">{initials}</span><span>{session?.name}</span><button type="button" onClick={logout} className="text-button logout-button" aria-label="Đăng xuất"><Icon name="logout" /><span>Đăng xuất</span></button></div></div></header><main id="main-content" className="layout__main"><Outlet /></main><nav className="mobile-nav" aria-label="Điều hướng di động"><NavBar mobile /></nav></div>;
}
