import { Outlet } from 'react-router-dom';
import NavBar from './NavBar.jsx';

export default function AppLayout() {
  return (
    <>
      <header>
        <div className="layout__header-inner">
          <span className="layout__logo">NutriPlan</span>
          <NavBar />
        </div>
      </header>
      <main className="layout__main">
        <Outlet />
      </main>
    </>
  );
}
