import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { DemoLabel, Modal, Notice, ResourceState } from '../../components/Feedback.jsx';
import Icon from '../../components/Icon.jsx';
import { useResource } from '../../hooks/useResource.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';

const emptyForm = { name: '', relation: '', age: '', goal: '' };

export default function FamilyPage() {
  const { memberId } = useParams();
  const family = useResource(service.getFamily);
  const action = useAction();
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const selected = family.data?.find((item) => item.id === memberId);
  function open(person) { setEditing(person || 'new'); setForm(person ? { name: person.name, relation: person.relation, age: person.age, goal: person.goal } : emptyForm); }
  async function save(event) {
    event.preventDefault();
    if (!form.name.trim() || !form.relation.trim() || !form.age || Number(form.age) < 1 || Number(form.age) > 120) return action.setError('Vui lòng nhập tên, quan hệ và tuổi hợp lệ.');
    const payload = { ...form, age: Number(form.age) };
    const result = await action.run(() => editing === 'new' ? service.addMember(payload) : service.updateMember(editing.id, payload), 'Đã lưu thành viên vào dữ liệu demo.');
    if (result) { setEditing(null); family.refresh(); }
  }
  async function remove(id) {
    if (!window.confirm('Xóa thành viên này khỏi dữ liệu demo?')) return;
    const result = await action.run(() => service.removeMember(id), 'Đã xóa thành viên khỏi dữ liệu demo.');
    if (result) family.refresh();
  }
  return <div className="page"><div className="page-top"><div><span className="eyebrow">HỒ SƠ GIA ĐÌNH</span><h1>{selected ? selected.name : 'Gia đình của bạn'}</h1><p>{selected ? 'Thông tin cá nhân trong bản demo.' : 'Thêm và quản lý thành viên để ghi nhận bữa ăn riêng cho từng người.'}</p></div><DemoLabel /></div><Notice message={action.notice} onClose={() => action.setNotice('')} />{action.error && !editing && <p className="form-error" role="alert">{action.error}</p>}
    {memberId && <Link className="text-link back-link" to="/gia-dinh">← Tất cả thành viên</Link>}
    <ResourceState loading={family.loading} error={family.error} empty={family.data?.length === 0} onRetry={family.refresh} />
    {memberId && !family.loading && !selected && <div className="state">Không tìm thấy thành viên.</div>}
    {selected ? <section className="profile-card panel"><span className="avatar avatar--large" style={{ background: selected.color }}>{selected.avatar}</span><div><span className="eyebrow">{selected.relation}</span><h2>{selected.name}</h2><p>{selected.age} tuổi · {selected.goal || 'Chưa đặt mục tiêu'}</p><p className="helper">Hồ sơ này chỉ dùng để minh họa trải nghiệm, không chứa đánh giá sức khỏe.</p><button className="button button--outline" onClick={() => open(selected)}>Chỉnh sửa hồ sơ</button></div></section> : !memberId && <><div className="section-head"><h2>Thành viên ({family.data?.length || 0})</h2><button className="button button--primary" onClick={() => open(null)}><Icon name="plus" size={18} /> Thêm thành viên</button></div><div className="member-grid">{family.data?.map((person) => <article className="member-card panel" key={person.id}><span className="avatar avatar--large" style={{ background: person.color }}>{person.avatar}</span><span className="eyebrow">{person.relation}</span><h2>{person.name}</h2><p>{person.age} tuổi · {person.goal || 'Chưa đặt mục tiêu'}</p><div className="card-actions"><Link className="text-link" to={`/gia-dinh/${person.id}`}>Xem hồ sơ →</Link><button className="text-button" onClick={() => open(person)}>Sửa</button><button className="text-button text-button--danger" onClick={() => remove(person.id)}>Xóa</button></div></article>)}</div></>}
    {editing && <Modal title={editing === 'new' ? 'Thêm thành viên' : 'Chỉnh sửa thành viên'} onClose={() => setEditing(null)}><form className="stack-form" onSubmit={save}><label>Họ và tên<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength="60" required /></label><label>Quan hệ<input value={form.relation} onChange={(e) => setForm({ ...form, relation: e.target.value })} placeholder="Ví dụ: Mẹ, Bố, Con" required /></label><label>Tuổi<input type="number" min="1" max="120" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} required /></label><label>Mục tiêu cá nhân (tùy chọn)<input value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} placeholder="Ví dụ: Ăn uống đa dạng" /></label>{action.error && <p className="form-error" role="alert">{action.error}</p>}<div className="modal-actions"><button type="button" className="button button--quiet" onClick={() => setEditing(null)}>Hủy</button><button className="button button--primary" disabled={action.busy}>{action.busy ? 'Đang lưu…' : 'Lưu thành viên'}</button></div></form></Modal>}
  </div>;
}
