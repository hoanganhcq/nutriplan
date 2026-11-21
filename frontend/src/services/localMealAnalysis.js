const baseUrl = import.meta.env.VITE_LOCAL_MEAL_API_URL?.replace(/\/+$/, '');

export const localMealAnalysisEnabled = Boolean(baseUrl);

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${baseUrl}/local-meal-analysis${path}`, options);
  } catch {
    throw new Error('Không kết nối được API phân tích bữa ăn cục bộ.');
  }
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error?.message || 'Không thể phân tích bữa ăn.');
  }
  return { data: body };
}

export const localMealAnalysis = {
  foods: () => request('/foods'),
  recognize(file) {
    const body = new FormData();
    body.append('image', file);
    return request('/recognize', { method: 'POST', body });
  },
  assess: (meal) => request('/assess', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(meal),
  }),
};
