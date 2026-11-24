import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Modal, Notice, ResourceState } from '../../components/Feedback.jsx';
import { useResource } from '../../hooks/useResource.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';

const emptyProfile = { name: '', age: '', energyGoalKcal: '', conditions: [], allergies: [] };
const conditions = {
  diabetes: 'Đái tháo đường', hypertension: 'Tăng huyết áp', dyslipidemia: 'Rối loạn lipid máu',
  obesity: 'Béo phì', kidney_disease: 'Bệnh thận', gout: 'Gút', celiac: 'Celiac',
};
const allergies = {
  milk: 'Sữa', egg: 'Trứng', peanut: 'Đậu phộng', tree_nut: 'Hạt cây', soy: 'Đậu nành',
  wheat: 'Lúa mì', fish: 'Cá', shellfish: 'Hải sản có vỏ',
};

function ProfileOptions({ title, options, values, onChange }) {
  return <fieldset>
    <legend>{title}</legend>
    {Object.entries(options).map(([id, label]) => <label className="setting-row" key={id}>
      <span>{label}</span>
      <input type="checkbox" checked={values.includes(id)} onChange={(event) =>
        onChange(event.target.checked ? [...values, id] : values.filter((value) => value !== id))} />
    </label>)}
  </fieldset>;
}

export default function FamilyPage() {
  const { memberId } = useParams();
  const family = useResource(service.getFamily);
  const permissions = useResource(service.getSettings);
  const action = useAction();
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyProfile);
  const selected = family.data?.find((item) => item.id === memberId);
  function edit(person) {
    action.setError('');
    setEditing(person || 'new');
    setForm(person ? {
      name: person.name, age: person.age, energyGoalKcal: person.energyGoalKcal ?? '',
      conditions: (person.conditions || []).filter((value) => value !== 'none'),
      allergies: (person.allergies || []).filter((value) => value !== 'none'),
    } : emptyProfile);
  }
  async function save(event) {
    event.preventDefault();
    const values = {
      ...form, name: form.name.trim(), age: Number(form.age),
      energyGoalKcal: form.energyGoalKcal === '' ? null : Number(form.energyGoalKcal),
    };
    if (!values.name) return action.setError('Vui lòng nhập họ và tên.');
    const result = await action.run(() => editing === 'new'
      ? service.addMember(values) : service.updateMember(editing.id, values), 'Đã lưu hồ sơ.');
    if (result) { setEditing(null); family.refresh(); }
  }
  async function remove(person) {
    if (!window.confirm(`Xóa hồ sơ của ${person.name}?`)) return;
    if (await action.run(() => service.removeMember(person.id), 'Đã xóa hồ sơ.')) family.refresh();
  }
  return <div className="page">
    <div className="page-top"><div><h1>{selected?.name || 'Gia đình của bạn'}</h1><p>Quản lý hồ sơ để ghi nhận bữa ăn theo từng thành viên.</p></div></div>
    <Notice message={action.notice} onClose={() => action.setNotice('')} />
    <ResourceState loading={family.loading || permissions.loading} error={family.error || permissions.error}
      onRetry={() => { family.refresh(); permissions.refresh(); }} />
    {action.error && !editing && <p className="form-error" role="alert">{action.error}</p>}
    {!permissions.loading && permissions.data?.consents.store_health_profile === false &&
      <p>Bật <Link to="/cai-dat">quyền lưu hồ sơ sức khỏe</Link> để thêm hoặc chỉnh sửa hồ sơ.</p>}
    {memberId && <Link to="/gia-dinh">← Tất cả thành viên</Link>}
    {!memberId && <div className="section-head"><h2>Thành viên</h2>
      <button className="button button--primary" onClick={() => edit(null)} disabled={!permissions.data?.consents.store_health_profile}>Thêm thành viên</button>
    </div>}
    <div className="member-grid">{(memberId ? (selected ? [selected] : []) : family.data || []).map((person) =>
      <article className="member-card panel" key={person.id}>
        <span className="avatar avatar--large" style={{ background: person.color }}>{person.avatar}</span>
        <h2>{person.name}</h2><p>{person.age} tuổi · {person.goal || 'Chưa đặt mục tiêu năng lượng'}</p>
        <p>{person.conditions?.map((condition) => conditions[condition]).filter(Boolean).join(', ') || 'Chưa ghi nhận bệnh lý'}</p>
        <p>{person.allergies?.map((allergy) => allergies[allergy]).filter(Boolean).join(', ') || 'Chưa ghi nhận dị ứng'}</p>
        <div className="card-actions">
          {!memberId && <Link to={`/gia-dinh/${person.id}`}>Xem hồ sơ</Link>}
          <button className="text-button" onClick={() => edit(person)} disabled={!permissions.data?.consents.store_health_profile}>Sửa</button>
          {!memberId && <button className="text-button text-button--danger" onClick={() => remove(person)}>Xóa</button>}
        </div>
      </article>)}</div>
    {editing && <Modal title={editing === 'new' ? 'Thêm thành viên' : 'Chỉnh sửa thành viên'} onClose={() => setEditing(null)}>
      <form className="stack-form" onSubmit={save}>
        <label>Họ và tên<input required maxLength={100} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
        <label>Tuổi<input type="number" required min={1} max={120} value={form.age} onChange={(event) => setForm({ ...form, age: event.target.value })} /></label>
        <label>Mục tiêu năng lượng (kcal/ngày)<input type="number" min={1} max={10000} value={form.energyGoalKcal} onChange={(event) => setForm({ ...form, energyGoalKcal: event.target.value })} /></label>
        <ProfileOptions title="Bệnh lý đã biết" options={conditions} values={form.conditions} onChange={(values) => setForm({ ...form, conditions: values })} />
        <ProfileOptions title="Dị ứng đã biết" options={allergies} values={form.allergies} onChange={(values) => setForm({ ...form, allergies: values })} />
        {action.error && <p className="form-error" role="alert">{action.error}</p>}
        <button className="button button--primary" disabled={action.busy}>Lưu thành viên</button>
      </form>
    </Modal>}
  </div>;
}
