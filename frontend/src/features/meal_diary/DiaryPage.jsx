import { useState } from 'react';
import { Link } from 'react-router-dom';
import { DemoLabel, Notice, ResourceState } from '../../components/Feedback.jsx';
import Icon from '../../components/Icon.jsx';
import { useResource } from '../../hooks/useResource.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';

export default function DiaryPage() {
  const diary = useResource(service.getDiary);
  const family = useResource(service.getFamily);
  const action = useAction();
  const [member, setMember] = useState('all');
  const [date, setDate] = useState('');
  const [selected, setSelected] = useState(null);
  const entries = diary.data?.filter((entry) => (member === 'all' || entry.memberId === member) && (!date || entry.date === date)).sort((a, b) => b.date.localeCompare(a.date));
  const nameOf = (id) => family.data?.find((person) => person.id === id)?.name || 'Thành viên đã xóa';
  async function remove(id) {
    if (!window.confirm('Xóa bữa ăn này khỏi nhật ký demo?')) return;
    const result = await action.run(() => service.removeDiary(id), 'Đã xóa bữa ăn trong dữ liệu demo.');
    if (result) { setSelected(null); diary.refresh(); }
  }
  return <div className="page">
    <div className="page-top"><div><span className="eyebrow">THEO DÕI HẰNG NGÀY</span><h1>Nhật ký bữa ăn</h1><p>Nhìn lại những bữa ăn đã ghi nhận cho gia đình.</p></div><DemoLabel /></div>
    <div className="section-head"><h2>Các bữa ăn</h2><Link className="button button--primary" to="/chup-bua-an"><Icon name="plus" size={18} /> Ghi bữa ăn</Link></div>
    <Notice message={action.notice} onClose={() => action.setNotice('')} />{action.error && <p className="form-error" role="alert">{action.error}</p>}
    <div className="filter-bar"><label>Thành viên<select value={member} onChange={(event) => setMember(event.target.value)}><option value="all">Tất cả thành viên</option>{family.data?.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label><label>Ngày<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>{(member !== 'all' || date) && <button className="text-button" onClick={() => { setMember('all'); setDate(''); }}>Xóa bộ lọc</button>}</div>
    <ResourceState loading={diary.loading || family.loading} error={diary.error || family.error} empty={entries?.length === 0} onRetry={() => { diary.refresh(); family.refresh(); }} />
    <div className="diary-list">{entries?.map((entry) => <article className="diary-card panel" key={entry.id}>
      <span className="food-emoji"><Icon name={entry.icon} size={28} /></span>
      <div className="diary-card__body"><span className="diary-meta">{entry.date} · {entry.meal} · {nameOf(entry.memberId)}</span><h2>{entry.name}</h2><p>{entry.score} <span className="demo-label">MINH HỌA</span></p>{selected === entry.id && <div className="diary-detail"><p>{entry.note}</p><p className="helper">Đây là nhận xét demo, không phải tư vấn y tế.</p></div>}</div>
      <div className="diary-card__actions"><button className="text-button" onClick={() => setSelected(selected === entry.id ? null : entry.id)} aria-expanded={selected === entry.id}>{selected === entry.id ? 'Thu gọn' : 'Chi tiết'}</button><button className="text-button text-button--danger" onClick={() => remove(entry.id)}>Xóa</button></div>
    </article>)}</div>
  </div>;
}
