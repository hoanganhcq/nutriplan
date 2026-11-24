import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { currentSession, levels, request } from '../../services/api.js';
import useRequest from '../../services/useRequest.js';

export default function DiaryPage() {
  const [entries, setEntries] = useState([]);
  const [session] = useState(currentSession);
  const action = useRequest();

  useEffect(() => {
    if (!session) return;
    action.run(async () => {
      const meals = [];
      let cursor = 0;
      do {
        const { data, meta } = await request(`/meals?status=all&limit=100&cursor=${cursor}`);
        meals.push(...data);
        cursor = meta.nextCursor;
      } while (cursor != null);
      setEntries(meals.reverse());
    });
  }, [session]);

  return <section className="meal-flow">
    <h1>Nhật ký</h1>
    {!session && <p>Tạo phiên ở <Link to="/gia-dinh">Gia đình</Link> để xem bữa ăn.</p>}
    {action.error && <p role="alert">{action.error}</p>}
    {action.busy && <p role="status">Đang tải nhật ký…</p>}
    {session && !action.busy && !action.error && !entries.length && <p>Chưa có bữa ăn nào.</p>}
    {entries.map((meal) => <article className="meal-panel" key={meal.mealId}>
      <h2>{meal.itemNames.join(', ') || 'Bữa chưa có món'}</h2>
      <p>{meal.eatenAt.slice(0, 10)} · {meal.status === 'confirmed' ? 'Đã xác nhận' : 'Bản nháp'}</p>
      {meal.levels.map((item) => <p key={item.memberId}>{levels[item.level] || item.level}</p>)}
      <Link to={`/chup-bua-an?draft=${meal.mealId}`}>{meal.status === 'confirmed' ? 'Xem bữa ăn' : 'Mở bản nháp'}</Link>
    </article>)}
  </section>;
}
