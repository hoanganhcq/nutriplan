import { Route, Routes } from 'react-router-dom';
import AppLayout from './layouts/AppLayout.jsx';
import HomePage from './features/home/HomePage.jsx';
import CapturePage from './features/meal_capture/CapturePage.jsx';
import MenuPage from './features/menu_planning/MenuPage.jsx';
import DiaryPage from './features/meal_diary/DiaryPage.jsx';
import FamilyPage from './features/family_profiles/FamilyPage.jsx';
import ComponentsDemo from './features/dev/ComponentsDemo.jsx';

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="chup-bua-an" element={<CapturePage />} />
        <Route path="thuc-don" element={<MenuPage />} />
        <Route path="nhat-ky" element={<DiaryPage />} />
        <Route path="gia-dinh" element={<FamilyPage />} />
        <Route path="demo" element={<ComponentsDemo />} />
      </Route>
    </Routes>
  );
}
