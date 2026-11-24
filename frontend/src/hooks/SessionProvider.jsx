import { useEffect, useState } from 'react';
import { service } from '../services/nutriplan.js';
import { SessionContext } from './sessionContext.js';

export default function SessionProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    service.getSession().then(({ data }) => setSession(data)).catch((cause) => setError(cause.message)).finally(() => setLoading(false));
  }, []);
  return <SessionContext.Provider value={{ session, setSession, loading, error }}>{children}</SessionContext.Provider>;
}
