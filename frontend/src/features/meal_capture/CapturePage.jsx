import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { DemoLabel, Notice, ResourceState } from '../../components/Feedback.jsx';
import Icon from '../../components/Icon.jsx';
import { useResource } from '../../hooks/useResource.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';
import { localMealAnalysisEnabled } from '../../services/localMealAnalysis.js';

const steps = ['Tải ảnh', 'Xác nhận món', 'Xem đánh giá'];

export default function CapturePage() {
  const family = useResource(service.getFamily);
  const action = useAction();
  const [step, setStep] = useState(0);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [dishes, setDishes] = useState([]);
  const [memberId, setMemberId] = useState('');
  const [meal, setMeal] = useState('Bữa trưa');
  const [assessment, setAssessment] = useState(null);
  useEffect(() => { if (family.data?.length && !memberId) setMemberId(family.data[0].id); }, [family.data, memberId]);
  useEffect(() => { if (!file) { setPreview(''); return undefined; } const url = URL.createObjectURL(file); setPreview(url); return () => URL.revokeObjectURL(url); }, [file]);
  async function analyze() {
    const result = await action.run(() => service.analyzePhoto(file), 'Đã tạo kết quả nhận diện giả lập. Vui lòng xác nhận các món.');
    if (result) { setDishes(result.dishes); setStep(1); }
  }
  async function assess() {
    if (!dishes.length || dishes.some((dish) => !dish.name.trim() || !dish.portion.trim())) return action.setError('Vui lòng nhập ít nhất một món với tên và khẩu phần.');
    const result = await action.run(() => service.assessMeal({ dishes, memberId }));
    if (result) { setAssessment(result); setStep(2); }
  }
  async function save() {
    const result = await action.run(() => service.addDiary({ date: new Date().toISOString().slice(0, 10), meal, name: dishes.map((dish) => dish.name.trim()).join(', '), memberId, note: assessment.summary, score: assessment.title, icon: 'plate' }), 'Đã lưu bữa ăn vào nhật ký demo.');
    if (result) { setStep(3); setFile(null); }
  }
  function reset() { setStep(0); setFile(null); setDishes([]); setAssessment(null); action.setError(''); }
  return <div className="page capture-page"><div className="page-top"><div><span className="eyebrow">GHI NHẬN BỮA ĂN</span><h1>Chụp bữa ăn</h1><p>Từ hình ảnh đến nhật ký, qua ba bước đơn giản.</p></div><DemoLabel /></div>
    {localMealAnalysisEnabled && <Link to="/chup-bua-an/vietfood" className="button button--secondary">Phân tích ảnh bằng VietFood</Link>}
    <ol className="stepper">{steps.map((label, index) => <li key={label} className={index <= step ? 'active' : ''}><span>{index + 1}</span>{label}</li>)}</ol>
    <Notice message={action.notice} onClose={() => action.setNotice('')} />{action.error && <p className="form-error" role="alert">{action.error}</p>}
    {step === 0 && <div className="capture-grid"><section className="panel"><span className="eyebrow">BƯỚC 01</span><h2>Tải ảnh bữa ăn</h2><p>Ảnh được xử lý giả lập trong trình duyệt. NutriPlan không gửi ảnh đến máy chủ ở mock mode.</p><label className="upload-zone"><input type="file" accept="image/*" capture="environment" onChange={(event) => { setFile(event.target.files?.[0] || null); action.setError(''); }} /><span className="upload-icon"><Icon name="camera" size={32} /></span><b>{file ? file.name : 'Chọn hoặc chụp một bức ảnh'}</b><small>JPG, PNG hoặc ảnh khác · Tối đa 5 MB</small></label><button className="button button--primary" disabled={!file || action.busy} onClick={analyze}>{action.busy ? 'Đang mô phỏng…' : 'Nhận diện món ăn →'}</button></section><div className="preview-panel panel">{preview ? <img src={preview} alt="Ảnh bữa ăn đã chọn" /> : <div className="preview-empty"><Icon name="plate" size={68} /><p>Ảnh của bạn sẽ hiển thị ở đây</p></div>}</div></div>}
    {step === 1 && <div className="capture-grid"><section className="panel"><span className="eyebrow">BƯỚC 02</span><h2>Xác nhận các món ăn</h2><p>Kết quả nhận diện là dữ liệu mô phỏng. Hãy chỉnh tên món và khẩu phần cho đúng với bữa ăn thực tế.</p><ResourceState loading={family.loading} error={family.error} empty={family.data?.length === 0} onRetry={family.refresh} /><div className="stack-form"><label>Thành viên<select value={memberId} onChange={(e) => setMemberId(e.target.value)}>{family.data?.map((person) => <option value={person.id} key={person.id}>{person.name}</option>)}</select></label><label>Loại bữa ăn<select value={meal} onChange={(e) => setMeal(e.target.value)}><option>Bữa sáng</option><option>Bữa trưa</option><option>Bữa tối</option><option>Bữa phụ</option></select></label></div><div className="dish-list">{dishes.map((dish, index) => <div className="dish-row" key={index}><label>Tên món<input value={dish.name} onChange={(e) => setDishes(dishes.map((item, i) => i === index ? { ...item, name: e.target.value } : item))} /></label><label>Khẩu phần<input value={dish.portion} onChange={(e) => setDishes(dishes.map((item, i) => i === index ? { ...item, portion: e.target.value } : item))} /></label><button className="icon-button" type="button" aria-label={`Xóa món ${index + 1}`} onClick={() => setDishes(dishes.filter((_, i) => i !== index))}>×</button></div>)}</div><button className="text-button" type="button" onClick={() => setDishes([...dishes, { name: '', portion: '' }])}>＋ Thêm món</button><div className="form-actions"><button className="button button--quiet" onClick={() => setStep(0)}>← Đổi ảnh</button><button className="button button--primary" disabled={action.busy || !memberId} onClick={assess}>{action.busy ? 'Đang đánh giá…' : 'Xem đánh giá minh họa →'}</button></div></section><div className="preview-panel panel">{preview && <img src={preview} alt="Ảnh bữa ăn đang xác nhận" />}</div></div>}
    {step === 2 && <section className="panel result-panel"><span className="eyebrow">BƯỚC 03 · KẾT QUẢ DEMO</span><div className="result-icon"><Icon name="sparkles" size={30} /></div><h2>{assessment.title}</h2><p>{assessment.summary}</p><div className="tag-row">{assessment.tags.map((tag) => <span key={tag}>{tag}</span>)}</div><div className="result-dishes"><h3>Các món đã xác nhận</h3>{dishes.map((dish, index) => <div key={index}>{dish.name}<span>{dish.portion}</span></div>)}</div><p className="helper">Đánh giá này không áp dụng ngưỡng bệnh lý và không thay thế tư vấn của chuyên gia.</p><div className="form-actions"><button className="button button--quiet" onClick={() => setStep(1)}>← Chỉnh món</button><button className="button button--primary" disabled={action.busy} onClick={save}>{action.busy ? 'Đang lưu…' : 'Lưu vào nhật ký'}</button></div></section>}
    {step === 3 && <section className="panel success-panel"><div className="result-icon"><Icon name="check" size={30} /></div><h2>Đã lưu bữa ăn!</h2><p>Bữa ăn vừa được thêm vào nhật ký demo. Bạn có thể xem lại hoặc ghi nhận bữa ăn khác.</p><div className="form-actions"><Link className="button button--outline" to="/nhat-ky">Xem nhật ký</Link><button className="button button--primary" onClick={reset}>Ghi bữa ăn khác</button></div></section>}
  </div>;
}
