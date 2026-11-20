import { useCallback, useEffect, useState } from 'react';

export function useResource(loader) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await loader();
      setData(response.data);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setLoading(false);
    }
  }, [loader]);
  useEffect(() => { refresh(); }, [refresh]);
  return { data, loading, error, refresh, setData };
}
