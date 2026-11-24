const apiUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sessionKey = 'nutriplan-session';

export function currentSession() {
  try { return JSON.parse(localStorage.getItem(sessionKey)); }
  catch { return null; }
}

export async function request(path, { method = 'GET', body, token = currentSession()?.token } = {}) {
  const multipart = body instanceof FormData;
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined && !multipart) headers['Content-Type'] = 'application/json';
  let response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      method, headers, body: multipart ? body : JSON.stringify(body),
    });
  } catch {
    throw new Error('Không kết nối được API NutriPlan.');
  }
  if (response.status === 204) return null;
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    const code = result?.error?.code;
    if (response.status === 401) localStorage.removeItem(sessionKey);
    const messages = {
      VISION_UNAVAILABLE: 'Chưa kết nối được model nhận diện. Bạn có thể nhập món thủ công.',
      INVALID_IMAGE: 'Ảnh không hợp lệ. Hãy thử một ảnh JPEG, PNG hoặc WebP khác.',
      CONSENT_REQUIRED: 'Cần đồng ý lưu hồ sơ sức khỏe trong mục Gia đình.',
      HARD_CONSTRAINT_VIOLATION: 'Chưa đủ căn cứ để xác nhận bữa ăn. Bữa ăn vẫn ở bản nháp.',
    };
    throw new Error(messages[code] || result?.error?.message || `API trả lỗi ${response.status}.`);
  }
  return result;
}

export async function createSession(name) {
  const { token } = await request('/sessions', { method: 'POST', token: null });
  const household = await request('/households', { method: 'POST', body: { name }, token });
  const session = { token, householdId: household.household_id, name: household.name };
  localStorage.setItem(sessionKey, JSON.stringify(session));
  return session;
}

export const levels = {
  INSUFFICIENT_DATA: 'Chưa đủ căn cứ đánh giá',
  RED: 'Có cảnh báo theo bộ quy tắc',
  YELLOW: 'Cần lưu ý theo bộ quy tắc',
  GREEN: 'Đã đối chiếu bộ quy tắc hiện có',
};

export const nutrients = {
  kcal: 'Năng lượng', proteinG: 'Protein', carbG: 'Carbohydrate', fatG: 'Chất béo',
};
