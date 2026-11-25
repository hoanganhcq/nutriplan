import { useCallback, useEffect, useRef, useState } from 'react';

export function useResource(loader) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const sequence = useRef(0);
  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    setLoading(true);
    setError('');
    try {
      const response = await loader();
      if (current === sequence.current) setData(response.data);
    } catch (cause) {
      if (current === sequence.current) setError(cause.message);
    } finally {
      if (current === sequence.current) setLoading(false);
    }
  }, [loader]);
  useEffect(() => {
    refresh();
    return () => { sequence.current++; };
  }, [refresh]);
  return { data, loading, error, refresh, setData };
}
