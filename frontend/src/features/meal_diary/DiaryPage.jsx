import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { Notice, ResourceState } from '../../components/Feedback.jsx';
import Icon from '../../components/Icon.jsx';
import { useResource } from '../../hooks/useResource.js';
import { useAction } from '../../hooks/useAction.js';
import { assessmentLabels, service } from '../../services/nutriplan.js';

export default function DiaryPage() {
  const family = useResource(service.getFamily);
  const action = useAction();
  const [member, setMember] = useState('all');
  const [date, setDate] = useState('');
  const [selected, setSelected] = useState(null);
  const [details, setDetails] = useState(null);
  const loadDiary = useCallback(() => service.getDiary(member), [member]);
  const diary = useResource(loadDiary);
  const entries = diary.data?.filter((entry) => !date || entry.date === date)
    .sort((a, b) => b.date.localeCompare(a.date));
  const nameOf = (id) => family.data?.find((person) => person.id === id)?.name || 'Thành viên đã xóa';
  async function remove(id) {
    if (!window.confirm('Xóa bữa ăn này khỏi nhật ký?')) return;
    const result = await action.run(() => service.removeDiary(id), 'Đã xóa bữa ăn.');
    if (result) { setSelected(null); diary.refresh(); }
  }
  async function toggleDetails(id) {
    if (selected === id) { setSelected(null); return; }
    setSelected(id);
    setDetails(null);
    const result = await action.run(() => service.getDiaryDetails(id));
    if (result) setDetails(result);
  }
  return <div className="page">
    <div className="page-top"><div><span className="eyebrow">THEO DÕI HẰNG NGÀY</span><h1>Nhật ký bữa ăn</h1><p>Nhìn lại những bữa ăn đã ghi nhận cho gia đình.</p></div></div>
    <div className="section-head"><h2>Các bữa ăn</h2><Link className="button button--primary" to="/chup-bua-an"><Icon name="plus" size={18} /> Ghi bữa ăn</Link></div>
    <Notice message={action.notice} onClose={() => action.setNotice('')} />{action.error && <p className="form-error" role="alert">{action.error}</p>}
    <div className="filter-bar"><label>Thành viên<select value={member} onChange={(event) => setMember(event.target.value)}><option value="all">Tất cả thành viên</option>{family.data?.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label><label>Ngày<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>{(member !== 'all' || date) && <button className="text-button" onClick={() => { setMember('all'); setDate(''); }}>Xóa bộ lọc</button>}</div>
    <ResourceState loading={diary.loading || family.loading} error={diary.error || family.error} empty={entries?.length === 0} onRetry={() => { diary.refresh(); family.refresh(); }} />
    <div className="diary-list">{entries?.map((entry) => <article className="diary-card panel" key={entry.id}>
      <span className="food-emoji"><Icon name={entry.icon} size={28} /></span>
      <div className="diary-card__body">
        <span className="diary-meta">{[entry.date, entry.meal, ...entry.memberIds.map(nameOf)].join(' · ')}</span>
        <h2>{entry.name}</h2>
        <p>{entry.score} · {entry.status === 'confirmed' ? 'Đã xác nhận' : 'Bản nháp'}</p>
        {selected === entry.id && <div className="diary-detail">
          {details && <ul>{details.items.map((item) => <li key={item.itemId}>{item.name} · {item.grams} g{item.isEstimate ? ' (ước lượng)' : ''}</li>)}</ul>}
          {action.busy && <p role="status">Đang tải đánh giá…</p>}
          {details?.assessments.map((item) => <p key={item.assessmentId}>{nameOf(String(item.memberId))} · {assessmentLabels[item.level] || item.level}</p>)}
        </div>}
      </div>
      <div className="diary-card__actions">
        <Link className="text-link" to={`/chup-bua-an?draft=${entry.id}`}>{entry.status === 'confirmed' ? 'Xem bữa ăn' : 'Mở bản nháp'}</Link>
        <button className="text-button" disabled={action.busy} onClick={() => toggleDetails(entry.id)} aria-expanded={selected === entry.id}>{selected === entry.id ? 'Thu gọn' : 'Chi tiết'}</button>
        <button className="text-button text-button--danger" disabled={action.busy} onClick={() => remove(entry.id)}>Xóa</button>
      </div>
    </article>)}</div>
  </div>;
}
