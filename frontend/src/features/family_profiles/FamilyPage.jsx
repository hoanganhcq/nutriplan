import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createSession, currentSession, request } from '../../services/api.js';
import useRequest from '../../services/useRequest.js';

export default function FamilyPage() {
  const [session, setSession] = useState(currentSession);
  const [members, setMembers] = useState([]);
  const [consent, setConsent] = useState(null);
  const action = useRequest();

  useEffect(() => {
    if (!session) return;
    const params = `?householdId=${session.householdId}`;
    action.run(async () => {
      const [profiles, permissions] = await Promise.all([
        request(`/members${params}`), request(`/consents${params}`),
      ]);
      setMembers(profiles.data);
      setConsent(permissions.data);
    });
  }, [session]);

  function start(event) {
    event.preventDefault();
    const name = new FormData(event.currentTarget).get('household').trim();
    if (name) action.run(async () => setSession(await createSession(name)));
  }

  function grant(event) {
    const granted = event.target.checked;
    action.run(async () => {
      const result = await request('/consents', {
        method: 'PUT',
        body: { householdId: session.householdId, policyVersion: consent.policyVersion, consents: { store_health_profile: granted } },
      });
      setConsent(result.data);
    });
  }

  function addMember(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const name = values.get('name').trim();
    if (!name) return;
    action.run(async () => {
      const result = await request('/members', {
        method: 'POST',
        body: {
          householdId: session.householdId, name, age: Number(values.get('age')),
          conditions: values.getAll('condition'),
        },
      });
      setMembers((previous) => [...previous, result.data]);
      form.reset();
    });
  }

  return <section className="meal-flow">
    <h1>Gia đình</h1>
    {action.error && <p role="alert">{action.error}</p>}
    {!session ? <form onSubmit={start} className="meal-panel">
      <label>Tên hộ gia đình<input name="household" required maxLength={100} /></label>
      <button type="submit" disabled={action.busy}>Tạo phiên hộ gia đình</button>
    </form> : <>
      <h2>{session.name}</h2>
      {consent && <label className="meal-checkbox">
        <input type="checkbox" onChange={grant} disabled={action.busy} checked={consent.consents.store_health_profile} />
        Đồng ý lưu hồ sơ sức khỏe
      </label>}
      {members.length > 0 && <ul>{members.map((member) =>
        <li key={member.memberId}>{member.name} · {member.age} tuổi</li>)}</ul>}
      {consent?.consents.store_health_profile && <form onSubmit={addMember} className="meal-panel">
        <h2>Thêm thành viên</h2>
        <label>Họ và tên<input name="name" required maxLength={100} /></label>
        <label>Tuổi<input name="age" type="number" min="1" max="120" required /></label>
        <fieldset>
          <legend>Bệnh lý đã ghi nhận</legend>
          <label className="meal-checkbox"><input type="checkbox" name="condition" value="diabetes" /> Đái tháo đường</label>
          <label className="meal-checkbox"><input type="checkbox" name="condition" value="hypertension" /> Tăng huyết áp</label>
          <label className="meal-checkbox"><input type="checkbox" name="condition" value="kidney_disease" /> Bệnh thận</label>
        </fieldset>
        <button type="submit" disabled={action.busy}>Lưu thành viên</button>
      </form>}
      {members.length > 0 && <Link to="/chup-bua-an">Ghi bữa ăn</Link>}
    </>}
  </section>;
}
