import { useState } from 'react';
import { DemoLabel, Modal, Notice, ResourceState } from '../../components/Feedback.jsx';
import Icon from '../../components/Icon.jsx';
import { useResource } from '../../hooks/useResource.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';

export default function MenuPage() {
  const menu = useResource(service.getMenu);
  const alternatives = useResource(service.getAlternatives);
  const action = useAction();
  const [editing, setEditing] = useState(null);
  const [dish, setDish] = useState('');
  function open(item) { setEditing(item); setDish(item.dish); action.setError(''); }
  async function save() {
    if (!dish.trim()) return action.setError('Vui lòng nhập tên món.');
    const result = await action.run(() => service.updateMenu(editing.id, { dish: dish.trim(), detail: 'Món được chọn trong bản demo' }), 'Đã đổi món trong thực đơn demo.');
    if (result) { setEditing(null); menu.refresh(); }
  }
  async function toggle(item) {
    const result = await action.run(() => service.updateMenu(item.id, { locked: !item.locked }), item.locked ? 'Đã mở khóa món demo.' : 'Đã khóa món demo.');
    if (result) menu.refresh();
  }
  async function generate() {
    const result = await action.run(service.generateMenu, 'Đã tạo thực đơn minh họa mới. Các món đã khóa được giữ lại.');
    if (result) menu.refresh();
  }
  return <div className="page">
    <div className="page-top"><div><span className="eyebrow">GỢI Ý CHO GIA ĐÌNH</span><h1>Thực đơn hôm nay</h1><p>Đổi món theo ý thích, khóa món muốn giữ và tạo gợi ý mới.</p></div><DemoLabel /></div>
    <div className="section-head"><div><h2>Kế hoạch trong ngày</h2><p className="helper">Gợi ý chỉ để minh họa, chưa cá nhân hóa theo tình trạng sức khỏe.</p></div><button className="button button--primary" disabled={action.busy} onClick={generate}><Icon name="sparkles" size={18} />{action.busy ? 'Đang tạo…' : 'Tạo thực đơn mới'}</button></div>
    <Notice message={action.notice} onClose={() => action.setNotice('')} />
    {action.error && !editing && <p className="form-error" role="alert">{action.error}</p>}
    <ResourceState loading={menu.loading} error={menu.error} empty={menu.data?.length === 0} onRetry={menu.refresh} />
    <div className="menu-grid">{menu.data?.map((item) => <article className={`menu-card panel${item.locked ? ' locked' : ''}`} key={item.id}>
      <span className="menu-card__icon"><Icon name={item.icon} size={27} /></span><span className="eyebrow">{item.label.toUpperCase()}</span><h2>{item.dish}</h2><p>{item.detail}</p>
      {item.locked && <span className="demo-label">ĐÃ KHÓA</span>}
      <div className="card-actions"><button className="button button--outline" onClick={() => open(item)}>Đổi món</button><button className="text-button" onClick={() => toggle(item)}><Icon name={item.locked ? 'unlock' : 'lock'} size={17} />{item.locked ? 'Mở khóa' : 'Khóa món'}</button></div>
    </article>)}</div>
    {editing && <Modal title={`Đổi món · ${editing.label}`} onClose={() => setEditing(null)}><div className="stack-form"><label>Tên món<input value={dish} onChange={(event) => setDish(event.target.value)} maxLength="100" /></label><p className="helper">Chọn nhanh một món minh họa hoặc nhập tên món của bạn.</p><ResourceState loading={alternatives.loading} error={alternatives.error} empty={alternatives.data?.length === 0} onRetry={alternatives.refresh} /><div className="alternative-list">{alternatives.data?.map((item) => <button type="button" key={item.name} onClick={() => setDish(item.name)}>{item.name}<Icon name="plus" size={18} /></button>)}</div>{action.error && <p className="form-error" role="alert">{action.error}</p>}<div className="modal-actions"><button className="button button--quiet" onClick={() => setEditing(null)}>Hủy</button><button className="button button--primary" disabled={action.busy} onClick={save}>{action.busy ? 'Đang lưu…' : 'Lưu món'}</button></div></div></Modal>}
  </div>;
}
