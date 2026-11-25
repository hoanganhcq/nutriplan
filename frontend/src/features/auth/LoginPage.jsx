import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../../hooks/sessionContext.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';
import Icon from '../../components/Icon.jsx';

export default function LoginPage() {
  const [householdName, setHouseholdName] = useState('');
  const { setSession } = useSession();
  const action = useAction();
  async function submit(event) {
    event.preventDefault();
    if (!householdName.trim()) return action.setError('Vui lòng nhập tên hộ gia đình.');
    const result = await action.run(() => service.login({ householdName }));
    if (result) setSession(result);
  }
  return <div className="auth-page">
    <Link className="brand" to="/welcome"><span className="brand__mark"><Icon name="logo" size={22} /></span> NutriPlan</Link>
    <div className="auth-card">
      <h1>Tạo phiên gia đình</h1>
      <p>NutriPlan dùng phiên ẩn danh cho trình duyệt này.</p>
      <form onSubmit={submit}>
        <label>Tên hộ gia đình<input required maxLength={100} value={householdName} onChange={(event) => setHouseholdName(event.target.value)} /></label>
        {action.error && <p className="form-error" role="alert">{action.error}</p>}
        <button className="button button--primary button--full" disabled={action.busy}>Tạo phiên</button>
      </form>
    </div>
  </div>;
}
