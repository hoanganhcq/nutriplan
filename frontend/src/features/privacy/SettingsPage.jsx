import { DemoLabel, Notice, ResourceState } from '../../components/Feedback.jsx';
import { useResource } from '../../hooks/useResource.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';

export default function SettingsPage() {
  const settings = useResource(service.getSettings);
  const action = useAction();
  async function update(changes) {
    const result = await action.run(() => service.updateSettings(changes), 'Đã lưu tùy chọn vào dữ liệu demo.');
    if (result) settings.refresh();
  }
  async function reset() {
    if (!window.confirm('Khôi phục dữ liệu demo ban đầu? Các thay đổi thành viên, nhật ký và thực đơn sẽ bị xóa.')) return;
    const result = await action.run(service.resetDemo, 'Đã khôi phục dữ liệu demo ban đầu.');
    if (result) settings.refresh();
  }
  return <div className="page"><div className="page-top"><div><span className="eyebrow">TÀI KHOẢN VÀ DỮ LIỆU</span><h1>Cài đặt & quyền riêng tư</h1><p>Kiểm soát trải nghiệm demo và cách dữ liệu được lưu trong trình duyệt.</p></div><DemoLabel /></div><Notice message={action.notice} onClose={() => action.setNotice('')} />{action.error && <p className="form-error" role="alert">{action.error}</p>}<ResourceState loading={settings.loading} error={settings.error} onRetry={settings.refresh} />
    {settings.data && <div className="settings-grid"><section className="panel"><span className="eyebrow">TÙY CHỌN</span><h2>Trải nghiệm</h2><label className="setting-row"><span><b>Thông báo trong ứng dụng</b><p>Hiển thị thông báo khi thao tác demo hoàn tất.</p></span><input type="checkbox" checked={settings.data.notifications} onChange={(event) => update({ notifications: event.target.checked })} disabled={action.busy} /></label><label className="setting-row"><span><b>Đồng ý dùng ảnh cho bản demo</b><p>Ảnh chỉ được xem tạm trong phiên hiện tại. Công tắc này ghi nhận lựa chọn minh họa.</p></span><input type="checkbox" checked={settings.data.photoConsent} onChange={(event) => update({ photoConsent: event.target.checked })} disabled={action.busy} /></label></section><section className="panel"><span className="eyebrow">QUYỀN RIÊNG TƯ</span><h2>Dữ liệu của bạn</h2><p>Hồ sơ gia đình, nhật ký và thực đơn demo được lưu trong localStorage của trình duyệt này. Ảnh tải lên chỉ tồn tại tạm thời để xem trước và mô phỏng nhận diện, không được lưu vào nhật ký.</p><p>Đăng xuất giữ lại dữ liệu demo. Khôi phục sẽ đưa dữ liệu về trạng thái mẫu ban đầu.</p><button className="danger-button" onClick={reset} disabled={action.busy}>Khôi phục dữ liệu demo</button></section><section className="panel"><span className="eyebrow">THÔNG TIN</span><h2>Về bản demo</h2><p>Các kết quả nhận diện, đánh giá và thực đơn đều là ví dụ giả lập. NutriPlan chưa cung cấp tư vấn y tế hoặc quy tắc lâm sàng được xác thực trong giao diện này.</p></section></div>}
  </div>;
}
