import { clearSession, createSession, currentSession, request as fetchApi } from './api.js';
export { levels as assessmentLabels } from './api.js';

async function request(path, options) {
  const result = await fetchApi(path, options);
  if (options?.raw || (result && Object.hasOwn(result, 'data'))) return result;
  return { data: result };
}

export const mealLabels = {
  breakfast: 'Bữa sáng', lunch: 'Bữa trưa', dinner: 'Bữa tối',
  snack: 'Bữa phụ', snack2: 'Bữa phụ 2', snack3: 'Bữa phụ 3',
};
function mapMember(member) {
  return {
    ...member,
    id: String(member.memberId ?? member.member_id),
    avatar: member.name.trim().split(/\s+/).slice(-2).map((word) => word[0]).join('').toUpperCase(),
    color: '#e5eee6',
    relation: 'Thành viên',
    energyGoalKcal: member.energyGoalKcal ?? member.energy_target_kcal,
    goal: (member.energyGoalKcal ?? member.energy_target_kcal)
      ? `${member.energyGoalKcal ?? member.energy_target_kcal} kcal/ngày` : '',
  };
}

function mapMeal(meal) {
  const memberIds = meal.levels.map(({ memberId }) => String(memberId));
  return {
    ...meal,
    id: String(meal.mealId),
    memberIds,
    date: meal.eatenAt.slice(0, 10),
    meal: mealLabels[meal.mealType] || 'Bữa ăn',
    name: meal.itemNames.join(', ') || 'Bữa ăn',
    score: meal.totals.kcal != null ? `${meal.totals.kcal} kcal` : 'Chưa đủ dữ liệu năng lượng',
    icon: 'plate',
  };
}

const householdId = () => currentSession()?.householdId;
const getSettings = () => request(`/consents?householdId=${householdId()}`);

export const service = {
  async getSession() {
    const session = currentSession();
    if (!session) return { data: null };
    try {
      await request(`/households/${session.householdId}`);
      return { data: session };
    } catch (error) {
      if (![401, 404].includes(error.status)) throw error;
      clearSession();
      return { data: null };
    }
  },
  async login({ householdName }) {
    return { data: await createSession(householdName.trim()) };
  },
  async logout() {
    clearSession();
    return { data: null };
  },
  async getFamily() {
    const { data } = await request(`/members?householdId=${householdId()}`);
    return { data: data.map(mapMember) };
  },
  async addMember(member) {
    const { data } = await request('/members', { method: 'POST', body: {
      householdId: householdId(), name: member.name.trim(), age: member.age,
      conditions: member.conditions, allergies: member.allergies,
      energyGoalKcal: member.energyGoalKcal,
    } });
    return { data: mapMember(data) };
  },
  async updateMember(id, changes) {
    const { data: previous } = await request(`/profiles/${id}`);
    const { data } = await request(`/profiles/${id}`, { method: 'PUT', body: {
      ...previous, name: changes.name.trim(), age: changes.age,
      conditions: changes.conditions, allergies: changes.allergies,
      energy_target_kcal: changes.energyGoalKcal,
    } });
    return { data: mapMember(data) };
  },
  async removeMember(id) {
    await request(`/profiles/${id}`, { method: 'DELETE' });
    return { data: true };
  },
  async getDiary(memberId) {
    const rows = [];
    const filter = memberId && memberId !== 'all' ? `&memberId=${encodeURIComponent(memberId)}` : '';
    let cursor = 0;
    do {
      const { data, meta } = await request(`/meals?status=all&limit=100&cursor=${cursor}${filter}`);
      rows.push(...data);
      cursor = meta?.nextCursor;
    } while (cursor != null);
    return { data: rows.map(mapMeal).reverse() };
  },
  async removeDiary(id) {
    await request(`/meals/${id}`, { method: 'DELETE' });
    return { data: true };
  },
  async getDiaryDetails(id) {
    const [meal, assessment] = await Promise.all([
      request(`/meals/${id}`), request(`/meals/${id}/assessments`),
    ]);
    return { data: { items: meal.data.items, assessments: assessment.data.assessments } };
  },
  getSettings,
  async updateSettings(changes) {
    const { data } = await getSettings();
    return request('/consents', { method: 'PUT', body: {
      householdId: householdId(), policyVersion: data.policyVersion, consents: changes,
    } });
  },
  listPlans: () => request('/menu-plans'),
  getPlan: (planId) => request(`/menu-plans/${planId}`),
  generateMenu: (memberId, startDate, days) => request('/menu-plans/generate', {
    method: 'POST', body: { memberId: Number(memberId), startDate, days: Number(days) },
  }),
  getAlternatives: (planId, itemId) => request(`/menu-plans/${planId}/items/${itemId}/alternatives`),
  replaceMenuItem: (planId, itemId, dishId, grams) => request(`/menu-plans/${planId}/items/${itemId}`, {
    method: 'PATCH', body: { dishId: Number(dishId), grams: Number(grams) },
  }),
  lockMenuItem: (planId, itemId, locked) => request(`/menu-plans/${planId}/items/${itemId}/lock`, {
    method: 'PUT', body: { locked },
  }),
  regenerateMenu: (planId) => request(`/menu-plans/${planId}/regenerate`, {
    method: 'POST', body: { scope: 'all_unlocked' },
  }),
  undoMenu: (planId) => request(`/menu-plans/${planId}/undo`, { method: 'POST', body: { steps: 1 } }),
  validateMenu: (planId) => request(`/menu-plans/${planId}/validate`, { method: 'POST' }),
  exportMenu: (planId, format) => request(`/menu-plans/${planId}/export?format=${format}`, { raw: true }),
  async removePlan(planId) {
    await request(`/menu-plans/${planId}`, { method: 'DELETE' });
    return { data: true };
  },
};
