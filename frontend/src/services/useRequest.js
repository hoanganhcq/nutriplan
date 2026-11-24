import { useState } from 'react';

export default function useRequest() {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function run(operation) {
    setError('');
    setBusy(true);
    try { return await operation(); }
    catch (problem) { setError(problem.message); }
    finally { setBusy(false); }
  }
  return { busy, error, run };
}
