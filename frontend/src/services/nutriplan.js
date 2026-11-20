import { seed } from '../mocks/seed.js';

const mode = import.meta.env.VITE_DATA_MODE || 'mock';
const storageKey = 'nutriplan-demo-v1';
const clone = (value) => JSON.parse(JSON.stringify(value));
const delay = () => new Promise((resolve) => setTimeout(resolve, 280));

function read() {
  try {
    return { ...clone(seed), ...JSON.parse(localStorage.getItem(storageKey) || '{}') };
  } catch {
    return clone(seed);
  }
}

function write(state) {
  localStorage.setItem(storageKey, JSON.stringify(state));
}

async function request(action) {
  await delay();
  if (mode !== 'mock') {
    throw new Error('Chế độ API thật chưa được cấu hình. Hãy dùng VITE_DATA_MODE=mock cho bản demo.');
  }
  try {
    return { data: action(), error: null };
  } catch (error) {
    throw new Error(error.message || 'Không thể hoàn tất thao tác.');
  }
}

export const service = {
  mode,
  getSession: () => request(() => read().session || null),
  login: ({ email, password }) => request(() => {
    if (!email.trim() || !password.trim()) throw new Error('Vui lòng nhập email và mật khẩu.');
    const state = read();
    state.session = { name: 'Minh Anh', email: email.trim() };
    write(state);
    return state.session;
  }),
  logout: () => request(() => {
    const state = read();
    state.session = null;
    write(state);
    return null;
  }),
  getFamily: () => request(() => read().family),
  addMember: (member) => request(() => {
    const state = read();
    const item = { ...member, id: crypto.randomUUID(), avatar: member.name.trim().split(' ').slice(-2).map((part) => part[0]).join('').toUpperCase(), color: '#e5eee6' };
    state.family.push(item);
    write(state);
    return item;
  }),
  updateMember: (id, changes) => request(() => {
    const state = read();
    const index = state.family.findIndex((item) => item.id === id);
    if (index < 0) throw new Error('Không tìm thấy thành viên.');
    state.family[index] = { ...state.family[index], ...changes };
    write(state);
    return state.family[index];
  }),
  removeMember: (id) => request(() => {
    const state = read();
    state.family = state.family.filter((item) => item.id !== id);
    write(state);
    return id;
  }),
  getDiary: () => request(() => read().diary),
  addDiary: (entry) => request(() => {
    const state = read();
    const item = { ...entry, id: crypto.randomUUID() };
    state.diary.unshift(item);
    write(state);
    return item;
  }),
  removeDiary: (id) => request(() => {
    const state = read();
    state.diary = state.diary.filter((item) => item.id !== id);
    write(state);
    return id;
  }),
  getMenu: () => request(() => read().menu),
  getAlternatives: () => request(() => clone(seed.alternatives)),
  updateMenu: (id, changes) => request(() => {
    const state = read();
    const index = state.menu.findIndex((item) => item.id === id);
    if (index < 0) throw new Error('Không tìm thấy bữa ăn.');
    state.menu[index] = { ...state.menu[index], ...changes };
    write(state);
    return state.menu[index];
  }),
  generateMenu: () => request(() => {
    const state = read();
    const choices = clone(seed.alternatives);
    state.menuGeneration = (state.menuGeneration || 0) + 1;
    state.menu = state.menu.map((item, index) => {
      if (item.locked) return item;
      const choice = choices[(index + state.menuGeneration - 1) % choices.length];
      return { ...item, dish: choice.name, detail: choice.detail };
    });
    write(state);
    return state.menu;
  }),
  analyzePhoto: (file) => request(() => {
    if (!file || !file.type.startsWith('image/')) throw new Error('Vui lòng chọn một tệp ảnh.');
    if (file.size > 5 * 1024 * 1024) throw new Error('Ảnh phải nhỏ hơn 5 MB.');
    return { dishes: [{ name: 'Cơm', portion: '1 chén' }, { name: 'Rau xanh', portion: '1 phần' }, { name: 'Món chính', portion: '1 phần' }], note: 'Nhận diện mô phỏng. Hãy chỉnh lại tên món và khẩu phần trước khi lưu.' };
  }),
  assessMeal: ({ dishes, memberId }) => request(() => {
    if (!memberId || dishes.some((dish) => !dish.name.trim())) throw new Error('Vui lòng chọn thành viên và điền tên các món.');
    return { title: 'Đánh giá minh họa', summary: 'Bữa ăn đã được ghi nhận với các món bạn xác nhận. Hãy tham khảo sự đa dạng thực phẩm và điều chỉnh theo nhu cầu cá nhân.', tags: ['Dữ liệu demo', 'Không phải tư vấn y tế'] };
  }),
  getSettings: () => request(() => read().settings || { notifications: true, photoConsent: false }),
  updateSettings: (changes) => request(() => {
    const state = read();
    state.settings = { ...(state.settings || { notifications: true, photoConsent: false }), ...changes };
    write(state);
    return state.settings;
  }),
  resetDemo: () => request(() => {
    const session = read().session;
    write({ ...clone(seed), session });
    return true;
  }),
};
