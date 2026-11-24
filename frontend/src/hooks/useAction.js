import { useState } from 'react';

export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  async function run(operation, success) {
    setBusy(true);
    setError('');
    try {
      const response = await operation();
      if (success) setNotice(success);
      return response.data;
    } catch (cause) {
      setError(cause.message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, setError, notice, setNotice, run };
}
