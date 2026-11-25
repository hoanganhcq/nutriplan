import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Modal, Notice, ResourceState } from '../../components/Feedback.jsx';
import { useAction } from '../../hooks/useAction.js';
import { useResource } from '../../hooks/useResource.js';
import { service, mealLabels } from '../../services/nutriplan.js';

function today() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export default function MenuPage() {
  const family = useResource(service.getFamily);
  const plans = useResource(service.listPlans);
  const action = useAction();
  const [member, setMember] = useState('');
  const [date, setDate] = useState(today);
  const [days, setDays] = useState(1);
  const [plan, setPlan] = useState(null);
  const [editing, setEditing] = useState(null);
  const memberId = member || family.data?.[0]?.id || '';

  async function generate(event) {
    event.preventDefault();
    const result = await action.run(() => service.generateMenu(memberId, date, days), 'Đã lưu thực đơn.');
    if (result) { setPlan(result); plans.refresh(); }
  }
  async function open(id) {
    const result = await action.run(() => service.getPlan(id));
    if (result) setPlan(result);
  }
  async function modify(operation, message) {
    const result = await action.run(async () => {
      await operation();
      return service.getPlan(plan.planId);
    }, message);
    if (result) { setPlan(result); setEditing(null); plans.refresh(); }
  }
  async function choose(item) {
    const alternatives = await action.run(() => service.getAlternatives(plan.planId, item.itemId));
    if (alternatives) setEditing({ item, alternatives });
  }
  async function check() {
    const result = await action.run(() => service.validateMenu(plan.planId));
    if (result) {
      setPlan({ ...plan, validation: result.validation || result });
      action.setNotice((result.validation || result).hardConstraintsPassed
        ? 'Đã đối chiếu bộ quy tắc hiện có.' : 'Có ràng buộc chưa đạt hoặc thiếu dữ liệu.');
    }
  }
  async function download(format) {
    await action.run(async () => {
      const response = await service.exportMenu(plan.planId, format);
      const link = document.createElement('a');
      link.href = URL.createObjectURL(await response.blob());
      link.download = `nutriplan-${plan.startDate}.${format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
      return { data: true };
    });
  }
  async function remove() {
    if (!window.confirm('Xóa thực đơn đang mở?')) return;
    if (await action.run(() => service.removePlan(plan.planId), 'Đã xóa thực đơn.')) {
      setPlan(null);
      plans.refresh();
    }
  }
  return <div className="page">
    <div className="page-top"><div><h1>Lên thực đơn</h1><p>Sinh và chỉnh sửa kế hoạch theo hồ sơ thành viên.</p></div></div>
    <Notice message={action.notice} onClose={() => action.setNotice('')} />
    {action.error && !editing && <p className="form-error" role="alert">{action.error}</p>}
    <ResourceState loading={family.loading || plans.loading} error={family.error || plans.error}
      onRetry={() => { family.refresh(); plans.refresh(); }} />
    {!family.loading && !memberId && <p>Thêm thành viên và mục tiêu năng lượng tại <Link to="/gia-dinh">Gia đình</Link>.</p>}
    <form className="panel menu-panel menu-form" onSubmit={generate}>
      <label>Thành viên<select required value={memberId} onChange={(event) => setMember(event.target.value)}>
        <option value="">Chọn thành viên</option>
        {family.data?.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
      </select></label>
      <label>Ngày bắt đầu<input required type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
      <label>Số ngày<input required type="number" min={1} max={3} value={days} onChange={(event) => setDays(event.target.value)} /></label>
      <button className="button button--primary" disabled={action.busy || !memberId}>Tạo thực đơn</button>
    </form>
    <section className="panel menu-panel">
      <h2>Thực đơn đã lưu</h2>
      {plans.data?.length === 0 && <p>Chưa có thực đơn.</p>}
      <ul className="menu-list">{plans.data?.map((item) => <li key={item.planId}>
        <button className="text-button" disabled={action.busy} onClick={() => open(item.planId)}>{item.startDate} · {item.days} ngày · {family.data?.find((person) => Number(person.id) === item.memberId)?.name || 'Thành viên'}</button>
      </li>)}</ul>
    </section>
    {plan && <>
      <section className="panel menu-panel">
        <h2>Thực đơn từ {plan.startDate}</h2>
        <div className="card-actions">
          <button className="text-button" disabled={action.busy} onClick={check}>Kiểm tra quy tắc</button>
          <button className="text-button" disabled={action.busy} onClick={() => modify(() => service.regenerateMenu(plan.planId), 'Đã cập nhật thực đơn.')}>Tạo lại món chưa khóa</button>
          <button className="text-button" disabled={action.busy || !plan.canUndo} onClick={() => modify(() => service.undoMenu(plan.planId), 'Đã hoàn tác.')}>Hoàn tác</button>
          <button className="text-button" disabled={action.busy} onClick={() => download('pdf')}>Tải PDF</button>
          <button className="text-button text-button--danger" disabled={action.busy} onClick={remove}>Xóa thực đơn</button>
        </div>
        {plan.validation?.hardConstraintsPassed === false && <p>Có ràng buộc chưa đạt hoặc cần thêm dữ liệu.</p>}
      </section>
      {plan.days.map((day) => <section key={day.date}>
        <div className="section-head"><h2>{day.date}</h2>{day.dayTotals.energyKcal != null && <span>{day.dayTotals.energyKcal} kcal</span>}</div>
        <div className="menu-grid">{day.meals.map((meal) => <article className="panel menu-panel" key={meal.mealType}>
          <h3>{mealLabels[meal.mealType] || meal.mealType}</h3>
          <ul className="menu-list">{meal.items.map((item) => <li key={item.itemId}>
            <strong>{item.name}</strong> · {item.grams} g
            <div className="card-actions">
              <button className="text-button" disabled={action.busy || item.locked} onClick={() => choose(item)}>Đổi món</button>
              <button className="text-button" disabled={action.busy} onClick={() => modify(
                () => service.lockMenuItem(plan.planId, item.itemId, !item.locked), 'Đã cập nhật trạng thái khóa.',
              )}>{item.locked ? 'Mở khóa' : 'Khóa món'}</button>
            </div>
          </li>)}</ul>
        </article>)}</div>
      </section>)}
    </>}
    {editing && <Modal title="Chọn món thay thế" onClose={() => setEditing(null)}>
      {action.error && <p className="form-error" role="alert">{action.error}</p>}
      {!editing.alternatives.length && <p>Chưa có món thay thế đáp ứng quy tắc.</p>}
      <div className="alternative-list">{editing.alternatives.map((item) => <button type="button" key={item.dishId} disabled={action.busy} onClick={() => modify(
        () => service.replaceMenuItem(plan.planId, editing.item.itemId, item.dishId, item.grams ?? editing.item.grams), 'Đã đổi món.',
      )}>{item.name}</button>)}</div>
    </Modal>}
  </div>;
}
