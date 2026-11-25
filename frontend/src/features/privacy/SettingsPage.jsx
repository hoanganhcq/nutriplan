import { Notice, ResourceState } from '../../components/Feedback.jsx';
import { useResource } from '../../hooks/useResource.js';
import { useAction } from '../../hooks/useAction.js';
import { service } from '../../services/nutriplan.js';

const consentLabels = {
  store_health_profile: 'Lưu hồ sơ sức khỏe',
  send_image_to_ai_provider: 'Gửi ảnh đến dịch vụ nhận diện bên ngoài',
  llm_explanation: 'Cho phép dùng LLM để giải thích',
  usage_analytics: 'Chia sẻ thống kê sử dụng',
};

export default function SettingsPage() {
  const settings = useResource(service.getSettings);
  const action = useAction();
  async function change(key, granted) {
    const result = await action.run(() => service.updateSettings({ [key]: granted }), 'Đã lưu quyền riêng tư.');
    if (result) settings.setData(result);
  }
  return <div className="page">
    <div className="page-top"><div><h1>Cài đặt & quyền riêng tư</h1><p>Quản lý quyền sử dụng dữ liệu của hộ gia đình.</p></div></div>
    <Notice message={action.notice} onClose={() => action.setNotice('')} />
    <ResourceState loading={settings.loading} error={settings.error} onRetry={settings.refresh} />
    {action.error && <p className="form-error" role="alert">{action.error}</p>}
    {settings.data && <section className="panel local-meal-section">
      <h2>Quyền sử dụng dữ liệu</h2>
      {Object.entries(consentLabels).map(([key, label]) => <label className="setting-row" key={key}>
        <span>{label}</span>
        <input type="checkbox" checked={Boolean(settings.data.consents[key])} disabled={action.busy}
          onChange={(event) => change(key, event.target.checked)} />
      </label>)}
    </section>}
  </div>;
}
