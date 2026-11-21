import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAction } from '../../hooks/useAction.js';
import { useResource } from '../../hooks/useResource.js';
import { localMealAnalysis } from '../../services/localMealAnalysis.js';
import './local-meal-analysis.css';

const nutrients = {
  energy_kcal: 'Năng lượng',
  protein_g: 'Protein',
  fat_g: 'Chất béo',
  sat_fat_g: 'Chất béo bão hòa',
  carb_g: 'Carbohydrate',
  sugar_g: 'Đường',
  added_sugar_g: 'Đường bổ sung',
  fiber_g: 'Chất xơ',
  sodium_mg: 'Natri',
  potassium_mg: 'Kali',
  phosphorus_mg: 'Phốt pho',
};
const numberFormat = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 });
const modelWarnings = {
  MAX_DETECTIONS_REACHED: 'Ảnh đã chạm giới hạn số vùng nhận diện.',
  INVALID_BOX_SKIPPED: 'Model đã bỏ qua một vùng nhận diện không hợp lệ.',
  INVALID_MASS_PREDICTION: 'Một số vùng thiếu gợi ý khối lượng.',
};

function Results({ result }) {
  const { nutrition, clinical_evidence: evidence } = result;
  return <>
    <section className="panel local-meal-section" aria-labelledby="nutrition-heading">
      <h2 id="nutrition-heading">Dinh dưỡng ước tính</h2>
      {nutrition.warnings.includes('MODEL_MASS_UNVALIDATED') &&
        <p className="helper">Tổng có sử dụng gram gợi ý từ ảnh. Giá trị thực tế có thể chênh lệch đáng kể.</p>}
      <dl className="local-meal-totals">
        {Object.entries(nutrients).map(([key, label]) => {
          const total = nutrition.totals[key];
          const { unit, known_items: known, total_items: count } = nutrition.completeness[key];
          return <div key={key}>
            <dt>{label}</dt>
            <dd>{total === null ? `Thiếu dữ liệu (${known}/${count} món)` : `${numberFormat.format(total)} ${unit}`}</dd>
          </div>;
        })}
      </dl>
    </section>
    <section className="panel local-meal-section" aria-labelledby="evidence-heading">
      <h2 id="evidence-heading">Tài liệu truy xuất cho hồ sơ mẫu</h2>
      <p>Hồ sơ giả lập gồm bệnh thận mạn và đái tháo đường típ 2. Nội dung KB chưa được thẩm định lâm sàng.</p>
      {result.missing_context.includes('recent_kidney_labs_for_individual_advice') &&
        <p className="helper">Hồ sơ mẫu thiếu kết quả xét nghiệm thận gần đây để tư vấn cá nhân.</p>}
      {evidence.length === 0 && <p>Chưa tìm thấy tài liệu áp dụng cho hồ sơ này.</p>}
      <ul className="local-meal-list">
        {evidence.map((document) => <li key={document.chunk_id}>
          <p>{document.text_vi}</p>
          <a href={document.source_url} target="_blank" rel="noreferrer">
            {document.source_id} · {document.locator}
          </a>
        </li>)}
      </ul>
    </section>
  </>;
}

export default function LocalMealAnalysisPage() {
  const catalog = useResource(localMealAnalysis.foods);
  const action = useAction();
  const nextId = useRef(0);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [prediction, setPrediction] = useState(null);
  const [rows, setRows] = useState([]);
  const [overlapReviewed, setOverlapReviewed] = useState(false);
  const [query, setQuery] = useState('Carbohydrate và natri');
  const [result, setResult] = useState(null);
  const foods = catalog.data || [];

  useEffect(() => {
    if (!file) return undefined;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function changeRows(nextRows) {
    setRows(nextRows);
    setOverlapReviewed(false);
    setResult(null);
  }

  function addRow(detection = null) {
    changeRows([...rows, {
      id: ++nextId.current,
      detection,
      food_id: '',
      grams: '',
      quantity_source: 'user_entered',
    }]);
  }

  function updateRow(id, changes) {
    changeRows(rows.map((row) => row.id === id ? { ...row, ...changes } : row));
  }

  async function recognize(event) {
    event.preventDefault();
    const nextPrediction = await action.run(() => localMealAnalysis.recognize(file));
    if (nextPrediction) {
      setPrediction(nextPrediction);
      changeRows(rows.filter((row) => !row.detection));
    }
  }

  async function assess(event) {
    event.preventDefault();
    setResult(null);
    const meal = {
      items: rows.map(({ detection, food_id, grams, quantity_source }) => ({
        detection_id: detection?.detection_id ?? null,
        food_id,
        grams: Number(grams),
        quantity_source,
      })),
      overlap_reviewed: overlapReviewed,
      query: query.trim(),
    };
    setResult(await action.run(() => localMealAnalysis.assess(meal)));
  }

  return <div className="page">
    <Link to="/chup-bua-an">← Chụp bữa ăn</Link>
    <div className="page-top"><div>
      <h1>Phân tích bữa ăn bằng VietFood</h1>
      <p>Chọn ảnh hoặc nhập món, xác nhận loại món và khối lượng để tính dinh dưỡng.</p>
    </div></div>
    {action.error && <div className="state state--error" role="alert">{action.error}</div>}
    <section className="panel local-meal-section" aria-labelledby="image-heading">
      <h2 id="image-heading">Nhận diện từ ảnh</h2>
      <form onSubmit={recognize} className="local-meal-form">
        <label>Ảnh JPEG, PNG hoặc WebP (tối đa 8 MB)
          <input type="file" accept="image/jpeg,image/png,image/webp" disabled={action.busy} onChange={(event) => {
            setFile(event.target.files[0] ?? null);
            setPrediction(null);
            changeRows(rows.filter((row) => !row.detection));
          }} />
        </label>
        <button className="button button--primary" disabled={action.busy || !file}>Nhận diện</button>
      </form>
      {file && preview && <img className="local-meal-preview" src={preview} alt="Ảnh bữa ăn đã chọn" />}
      {prediction && <>
        {prediction.detections.length === 0 && <p>Chưa nhận diện được món. Bạn có thể thêm món thủ công.</p>}
        {prediction.warnings.filter((code) => modelWarnings[code]).map((code) =>
          <p className="helper" key={code}>{modelWarnings[code]}</p>)}
        <ul className="local-meal-list">
          {prediction.detections.map((detection) => <li key={detection.detection_id}>
            <strong>{detection.name_vi}</strong>
            <p>Điểm nhận diện {numberFormat.format(detection.confidence)}{detection.suggested_mass_g &&
              ` · Gợi ý thử nghiệm ${numberFormat.format(detection.suggested_mass_g)} g`}</p>
            {detection.candidate_food_ids.length === 0 && <p className="helper">KB chưa có biến thể tương ứng đã xác minh.</p>}
            <button type="button" className="button button--secondary" disabled={action.busy || rows.length >= 25 ||
              rows.some((row) => row.detection?.detection_id === detection.detection_id)}
              onClick={() => addRow(detection)}>Chọn món trong danh mục</button>
          </li>)}
        </ul>
      </>}
    </section>
    <section className="panel local-meal-section" aria-labelledby="review-heading">
      <h2 id="review-heading">Xác nhận bữa ăn</h2>
      {catalog.loading && <p role="status">Đang tải danh mục món…</p>}
      {catalog.error && <p role="alert">{catalog.error} <button type="button" onClick={catalog.refresh}>Thử lại</button></p>}
      <form onSubmit={assess} className="local-meal-form">
        <fieldset disabled={action.busy}>
          {rows.map(({ id, detection, food_id, grams, quantity_source }) => {
            const candidates = detection?.candidate_food_ids ?? [];
            return <fieldset className="local-meal-item" key={id}>
              <legend>{detection?.name_vi ?? 'Món thêm thủ công'}</legend>
              <label>Món trong KB
                <select required value={food_id} onChange={(event) => updateRow(id, { food_id: event.target.value })}>
                  <option value="">Chọn biến thể đúng</option>
                  {candidates.length > 0 && <optgroup label="Ứng viên theo model">
                    {foods.filter((food) => candidates.includes(food.food_id)).map((food) =>
                      <option value={food.food_id} key={food.food_id}>{food.name_vi}</option>)}
                  </optgroup>}
                  <optgroup label={candidates.length ? 'Các món khác' : 'Danh mục KB'}>
                    {foods.filter((food) => !candidates.includes(food.food_id)).map((food) =>
                      <option value={food.food_id} key={food.food_id}>{food.name_vi}</option>)}
                  </optgroup>
                </select>
              </label>
              <label>Khối lượng phần ăn được (g)
                <input required type="number" min="0.01" max="10000" step="any" value={grams}
                  onChange={(event) => updateRow(id, { grams: event.target.value, quantity_source: 'user_entered' })} />
              </label>
              {detection?.suggested_mass_g > 0 && detection.suggested_mass_g <= 10000 &&
                <button type="button" className="button button--quiet"
                  onClick={() => updateRow(id, { grams: detection.suggested_mass_g, quantity_source: 'model_estimate' })}>
                  Dùng gram gợi ý từ ảnh
                </button>}
              {quantity_source === 'model_estimate' && <p className="helper">Khối lượng ước lượng từ ảnh, chưa được xác minh.</p>}
              <button type="button" className="button button--quiet"
                onClick={() => changeRows(rows.filter((row) => row.id !== id))}>Bỏ món</button>
            </fieldset>;
          })}
          <button type="button" className="button button--secondary" disabled={!foods.length || rows.length >= 25}
            onClick={() => addRow()}>Thêm món thủ công</button>
          <label className="local-meal-checkbox">
            <input required type="checkbox" checked={overlapReviewed} onChange={(event) => {
              setOverlapReviewed(event.target.checked);
              setResult(null);
            }} />
            Tôi đã kiểm tra và loại các phần bị tính trùng.
          </label>
          <label>Từ khóa tìm tài liệu cho hồ sơ mẫu
            <input required maxLength={300} value={query} onChange={(event) => {
              setQuery(event.target.value);
              setResult(null);
            }} />
          </label>
          <button className="button button--primary" disabled={!rows.length || !overlapReviewed || !query.trim()}>
            Tính dinh dưỡng và tìm tài liệu
          </button>
        </fieldset>
      </form>
    </section>
    {action.busy && <p role="status">Đang xử lý…</p>}
    {result && <Results result={result} />}
  </div>;
}
