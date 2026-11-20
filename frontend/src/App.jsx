import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './layouts/AppLayout.jsx';
import HomePage from './features/home/HomePage.jsx';
import CapturePage from './features/meal_capture/CapturePage.jsx';
import MenuPage from './features/menu_planning/MenuPage.jsx';
import DiaryPage from './features/meal_diary/DiaryPage.jsx';
import FamilyPage from './features/family_profiles/FamilyPage.jsx';
import LoginPage from './features/auth/LoginPage.jsx';
import LandingPage from './features/auth/LandingPage.jsx';
import SettingsPage from './features/privacy/SettingsPage.jsx';
import ComponentsDemo from './features/dev/ComponentsDemo.jsx';
import { useSession } from './hooks/sessionContext.js';

function Protected() {
  const { session, loading, error } = useSession();
  if (loading) return <div className="state">Đang tải phiên demo…</div>;
  if (error) return <div className="state state--error" role="alert">{error}</div>;
  return session ? <AppLayout /> : <Navigate to="/welcome" replace />;
}

export default function App() {
  const { session } = useSession();
  return <Routes>
    <Route path="/welcome" element={session ? <Navigate to="/" replace /> : <LandingPage />} />
    <Route path="/dang-nhap" element={session ? <Navigate to="/" replace /> : <LoginPage />} />
    <Route element={<Protected />}>
      <Route index element={<HomePage />} />
      <Route path="chup-bua-an" element={<CapturePage />} />
      <Route path="thuc-don" element={<MenuPage />} />
      <Route path="nhat-ky" element={<DiaryPage />} />
      <Route path="gia-dinh" element={<FamilyPage />} />
      <Route path="gia-dinh/:memberId" element={<FamilyPage />} />
      <Route path="cai-dat" element={<SettingsPage />} />
      <Route path="demo" element={<ComponentsDemo />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}
