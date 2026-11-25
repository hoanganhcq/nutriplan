import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { currentSession, levels, nutrients, request } from '../../services/api.js';
import useRequest from '../../services/useRequest.js';
import Icon from '../../components/Icon.jsx';

function DishForm({ dishes, grams, button, onSubmit }) {
  function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    onSubmit({ dishId: Number(data.get('dish')), grams: Number(data.get('grams')) });
  }

  return <form className="meal-row" onSubmit={submit}>
    <label>Món
      <select name="dish" required defaultValue={dishes.length === 1 ? dishes[0].dishId : ''}>
        <option value="">Chọn món</option>
        {dishes.map((dish) => <option key={dish.dishId} value={dish.dishId}>{dish.name}</option>)}
      </select>
    </label>
    <label>Khối lượng (g)<input name="grams" type="number" required min="0.01" max="10000" step="0.01" defaultValue={grams} /></label>
    <button type="submit">{button}</button>
  </form>;
}

async function loadDishes() {
  const dishes = [];
  let cursor = 0;
  do {
    const result = await request(`/dishes?limit=100&cursor=${cursor}`);
    dishes.push(...result.data);
    cursor = result.meta.nextCursor;
  } while (cursor != null);
  return dishes;
}

export default function CapturePage() {
  const [params, setParams] = useSearchParams();
  const draftId = params.get('draft');
  const [session] = useState(currentSession);
  const [members, setMembers] = useState([]);
  const [memberId, setMemberId] = useState('');
  const [dishes, setDishes] = useState([]);
  const [mealType, setMealType] = useState('lunch');
  const [meal, setMeal] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [recognitionEmpty, setRecognitionEmpty] = useState(false);
  const [assessment, setAssessment] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const action = useRequest();

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!session) return;
    if (draftId && String(meal?.mealId) === draftId) return;
    action.run(async () => {
      const [profiles, catalog, draft] = await Promise.all([
        request(`/members?householdId=${session.householdId}`),
        loadDishes(),
        draftId ? request(`/meals/${draftId}`) : null,
      ]);
      setMembers(profiles.data);
      setDishes(catalog);
      setMemberId(draft?.data.memberIds[0] || profiles.data[0]?.memberId || '');
      setMeal(draft?.data ?? null);
      setSuggestions([]);
      setRecognitionEmpty(false);
      setAssessment(null);
      setExplanation(null);
    });
  }, [session, draftId]);

  function updateMeal(next) {
    setMeal(next);
    setAssessment(null);
    setExplanation(null);
    if (!draftId) setParams({ draft: next.mealId }, { replace: true });
  }

  function upload(event) {
    event.preventDefault();
    const body = new FormData(event.currentTarget);
    body.set('householdId', session.householdId);
    body.set('memberIds', JSON.stringify([Number(memberId)]));
    body.set('mealType', mealType);
    action.run(async () => {
      const result = await request('/meals/analyze', { method: 'POST', body });
      updateMeal(result.data);
      setSuggestions((result.data.recognition || []).map((item, index) => ({ ...item, index })));
      setRecognitionEmpty(!result.data.recognition?.length && !result.data.items.length);
      setDishes(await loadDishes());
    });
  }

  function addDish(item, suggestionIndex) {
    action.run(async () => {
      const result = meal
        ? await request(`/meals/${meal.mealId}/items`, { method: 'POST', body: { ...item, confirmWeight: true } })
        : await request('/meals', { method: 'POST', body: {
          householdId: session.householdId, mealType, memberIds: [Number(memberId)], items: [item],
        } });
      updateMeal(result.data);
      if (suggestionIndex !== undefined) {
        setSuggestions((previous) => previous.filter((suggestion) => suggestion.index !== suggestionIndex));
      }
    });
  }

  function editItem(itemId, method, body) {
    action.run(async () => {
      const result = await request(`/meals/${meal.mealId}/items/${itemId}`, { method, body });
      updateMeal(result.data);
    });
  }

  function evaluate() {
    action.run(async () => {
      setExplanation(null);
      const result = await request(`/meals/${meal.mealId}/assessments`, {
        method: 'POST', body: { memberIds: [Number(memberId)] },
      });
      setAssessment(result.data.assessments[0]);
    });
  }

  function explain() {
    action.run(async () => {
      const result = await request(`/assessments/${assessment.assessmentId}/explain`, {
        method: 'POST', body: { style: 'simple', maxWords: 120 },
      });
      setExplanation(result.data);
    });
  }

  function confirm() {
    action.run(async () => {
      await request(`/meals/${meal.mealId}/confirm`, {
        method: 'POST', body: { eatenBy: [Number(memberId)] },
      });
      setMeal({ ...meal, status: 'confirmed' });
    });
  }

  if (!session) return <><h1>Chụp bữa ăn</h1><p>Tạo phiên tại <Link to="/gia-dinh">Gia đình</Link> để bắt đầu.</p></>;
  const confirmed = meal?.status === 'confirmed';
  const hasEstimates = meal?.items.some((item) => item.isEstimate);
  const step = assessment || confirmed ? 2 : meal ? 1 : 0;

  return <section className="page capture-page meal-flow">
    <div className="page-top">
      <div><h1>Chụp bữa ăn</h1><p>Tải ảnh, xác nhận các món và xem đánh giá theo hồ sơ.</p></div>
    </div>
    <ol className="stepper">{['Chụp ảnh', 'Xác nhận món', 'Đánh giá'].map((label, index) =>
      <li key={label} className={index <= step ? 'active' : ''} aria-current={index === step ? 'step' : undefined}>
        <span>{index + 1}</span>{label}
      </li>)}
    </ol>
    {action.error && <p className="meal-error" role="alert">{action.error}</p>}
    {action.busy && <p role="status">Đang xử lý…</p>}
    {!action.busy && !members.length && <p>Hãy thêm thành viên ở <Link to="/gia-dinh">Gia đình</Link>.</p>}
    <fieldset className="meal-flow__controls" disabled={action.busy || !members.length || confirmed}>
      <div className="capture-grid">
      <section className="panel meal-panel">
        <h2>{meal ? 'Thông tin bữa ăn' : 'Tải ảnh bữa ăn'}</h2>
        <label>Thành viên
          <select value={memberId} disabled={Boolean(meal)} onChange={(event) => setMemberId(event.target.value)}>
            {members.map((person) => <option key={person.memberId} value={person.memberId}>{person.name}</option>)}
          </select>
        </label>
        {!meal && <label>Loại bữa
          <select value={mealType} onChange={(event) => setMealType(event.target.value)}>
            <option value="breakfast">Bữa sáng</option><option value="lunch">Bữa trưa</option>
            <option value="dinner">Bữa tối</option><option value="snack">Bữa phụ</option>
          </select>
        </label>}
        {!meal && !draftId && <form onSubmit={upload} className="stack-form">
          <label className="upload-zone">
            <input name="images" type="file" accept="image/jpeg,image/png,image/webp" required
              onChange={(event) => { setFile(event.target.files[0] || null); }} />
            <span className="upload-icon"><Icon name="camera" size={32} /></span>
            <b>{file?.name || 'Chọn ảnh bữa ăn'}</b>
            <small>JPEG, PNG hoặc WebP · Tối đa 8 MB</small>
          </label>
          <button className="button button--primary" type="submit" disabled={!file}>Nhận diện món ăn</button>
        </form>}
      </section>
      {(!meal || file) && <div className="preview-panel panel">
        {file && preview
          ? <img src={preview} alt="Ảnh bữa ăn đã chọn" />
          : <div className="preview-empty"><Icon name="plate" size={68} /><p>Ảnh của bạn sẽ hiển thị ở đây</p></div>}
      </div>}
      </div>
      {recognitionEmpty && <p>Ảnh chưa có món nhận diện được. Bạn có thể thêm từ danh mục.</p>}
      {suggestions.length > 0 && <section className="meal-panel">
        <h2>Gợi ý từ ảnh</h2>
        <p>Kiểm tra các vùng trùng nhau, chọn đúng món và xác nhận gram trước khi thêm.</p>
        {suggestions.map((item) => <article key={item.index}>
          <h3>{item.name}</h3>
          {item.grams != null && <p>Ước lượng từ ảnh {Math.round(item.grams)} g</p>}
          {item.dishes.length > 0
            ? <DishForm dishes={item.dishes} grams={item.grams?.toFixed(2)} button="Xác nhận món và gram"
                onSubmit={(dish) => addDish(dish, item.index)} />
            : <p>Chưa có món tương ứng trong KB. Có thể tìm trong danh mục bên dưới.</p>}
          <button type="button" onClick={() => setSuggestions(suggestions.filter((suggestion) => suggestion.index !== item.index))}>
            Bỏ gợi ý
          </button>
        </article>)}
      </section>}
      {!confirmed && (!draftId || meal) && <section className="meal-panel">
        <h2>Thêm món từ danh mục</h2>
        {dishes.length > 0
          ? <DishForm dishes={dishes} button="Thêm món" onSubmit={addDish} />
          : <p>Danh mục dinh dưỡng hiện chưa có món.</p>}
      </section>}
      {meal && <section className="meal-panel">
        <h2>{confirmed ? 'Bữa ăn đã lưu' : 'Bữa ăn nháp'}</h2>
        {meal.items.map((item) => <article key={item.itemId}>
          <h3>{item.name}</h3>
          <form key={`${item.itemId}-${item.grams}-${item.isEstimate}`} className="meal-row" onSubmit={(event) => {
            event.preventDefault();
            editItem(item.itemId, 'PATCH', { grams: Number(new FormData(event.currentTarget).get('grams')) });
          }}>
            <label>Gram của {item.name}<input type="number" name="grams" min="0.01" max="10000" step="0.01" required defaultValue={item.grams} /></label>
            {!confirmed && <>
              <button type="submit">{item.isEstimate ? 'Xác nhận gram' : 'Cập nhật gram'}</button>
              <button type="button" onClick={() => editItem(item.itemId, 'DELETE')}>Bỏ món</button>
            </>}
          </form>
        </article>)}
        <h3>Tổng dinh dưỡng</h3>
        <dl className="meal-totals">{Object.entries(nutrients).map(([key, name]) => <div key={key}>
          <dt>{name}</dt><dd>{meal.totals[key] == null ? 'Thiếu dữ liệu' : `${meal.totals[key]} ${key === 'kcal' ? 'kcal' : 'g'}`}</dd>
        </div>)}</dl>
        {!confirmed && <button type="button" onClick={evaluate} disabled={!meal.items.length || hasEstimates || Boolean(suggestions.length)}>
          Đánh giá theo hồ sơ
        </button>}
        {assessment && <div>
          <h3>{levels[assessment.level] || assessment.level}</h3>
          {!explanation && <button type="button" onClick={explain}>Xem giải thích</button>}
          {explanation && <><p>{explanation.explanation}</p><p>{explanation.disclaimer}</p></>}
          {!confirmed && (assessment.level === 'INSUFFICIENT_DATA'
            ? <p>Bữa ăn được giữ ở bản nháp trong nhật ký.</p>
            : <button type="button" onClick={confirm}>Xác nhận và lưu nhật ký</button>)}
        </div>}
      </section>}
    </fieldset>
    {meal && <Link className="button button--outline" to="/nhat-ky">Mở nhật ký</Link>}
  </section>;
}
