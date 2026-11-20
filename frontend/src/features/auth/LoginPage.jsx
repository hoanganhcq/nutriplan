import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSession } from '../../hooks/sessionContext.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';
import Icon from '../../components/Icon.jsx';

export default function LoginPage() {
  const [email, setEmail] = useState('demo@nutriplan.vn');
  const [password, setPassword] = useState('demo123');
  const { setSession } = useSession();
  const { busy, error, setError, run } = useAction();
  const navigate = useNavigate();
  async function submit(event) {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError('Email không hợp lệ.');
    if (password.length < 6) return setError('Mật khẩu cần ít nhất 6 ký tự.');
    const result = await run(() => service.login({ email, password }));
    if (result) { setSession(result); navigate('/'); }
  }
  return <div className="auth-page"><Link className="brand" to="/welcome"><span className="brand__mark"><Icon name="logo" size={22} /></span> NutriPlan</Link><div className="auth-card"><span className="eyebrow">CHÀO MỪNG TRỞ LẠI</span><h1>Đăng nhập</h1><p>Trải nghiệm các luồng NutriPlan với tài khoản demo.</p><form onSubmit={submit}><label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" /></label><label>Mật khẩu<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button button--primary button--full" disabled={busy}>{busy ? 'Đang đăng nhập…' : 'Đăng nhập demo →'}</button></form><div className="auth-tip">Tài khoản demo đã được điền sẵn. Mọi mật khẩu từ 6 ký tự đều dùng được trong mock mode.</div></div><p className="auth-back"><Link to="/welcome">← Quay lại trang giới thiệu</Link></p></div>;
}
