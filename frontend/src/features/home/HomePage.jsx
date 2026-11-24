import { Link } from 'react-router-dom';
import { ResourceState } from '../../components/Feedback.jsx';
import Icon from '../../components/Icon.jsx';
import FoodArt from '../../components/FoodArt.jsx';
import { useResource } from '../../hooks/useResource.js';
import { service } from '../../services/nutriplan.js';
import { useSession } from '../../hooks/sessionContext.js';

export default function HomePage() {
  const { session } = useSession();
  const family = useResource(service.getFamily);
  const diary = useResource(service.getDiary);
  return <div className="page home-page">
    <div className="page-top"><div><span className="eyebrow">KHÔNG GIAN CỦA GIA ĐÌNH BẠN</span><h1>Chào {session?.name || 'bạn'}</h1><p>Cùng chăm sóc những bữa ăn hằng ngày, từng bước một.</p></div></div>
    <section className="hero-panel"><div><span className="hero-panel__kicker">BỮA ĂN HÔM NAY</span><h2>Một bữa ăn tốt bắt đầu từ việc ghi nhớ.</h2><p>Tải ảnh, kiểm tra món và lưu bữa ăn vào nhật ký.</p><Link className="button button--light" to="/chup-bua-an"><Icon name="plus" size={18} /> Ghi lại bữa ăn</Link></div><FoodArt className="hero-panel__illustration" /></section>
    <div className="section-grid"><section className="panel"><div className="section-head"><div><span className="eyebrow">CÙNG NHAU CHĂM SÓC</span><h2>Gia đình của bạn</h2></div><Link className="text-link" to="/gia-dinh">Quản lý →</Link></div><ResourceState loading={family.loading} error={family.error} empty={family.data?.length === 0} onRetry={family.refresh} /><div className="family-preview">{family.data?.map((person) => <Link to={`/gia-dinh/${person.id}`} className="person-mini" key={person.id}><span className="avatar" style={{ background: person.color }}>{person.avatar}</span><span><b>{person.name}</b><small>{person.relation}</small></span></Link>)}</div></section>
    <section className="panel"><div className="section-head"><div><span className="eyebrow">NHỮNG GHI NHẬN GẦN ĐÂY</span><h2>Nhật ký bữa ăn</h2></div><Link className="text-link" to="/nhat-ky">Xem tất cả →</Link></div><ResourceState loading={diary.loading} error={diary.error} empty={diary.data?.length === 0} onRetry={diary.refresh} /><div className="recent-list">{diary.data?.slice(0, 3).map((entry) => <div className="recent-item" key={entry.id}><span className="food-emoji"><Icon name={entry.icon} size={24} /></span><span><b>{entry.name}</b><small>{entry.meal} · {entry.date}</small></span></div>)}</div></section></div>
    <section className="quick-actions"><Link to="/thuc-don"><Icon name="menu" size={25} /><b>Lên thực đơn</b><small>Chọn món cho hôm nay →</small></Link><Link to="/nhat-ky"><Icon name="diary" size={25} /><b>Xem nhật ký</b><small>Nhìn lại các bữa ăn →</small></Link><Link to="/cai-dat"><Icon name="settings" size={25} /><b>Quyền riêng tư</b><small>Quản lý dữ liệu →</small></Link></section>
  </div>;
}
