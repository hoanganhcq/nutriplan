import { useId } from 'react';
import './components.css';

export default function Input({ label, error, ...rest }) {
  const id = useId();

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} className="input" {...rest} />
      {error && <p className="field__error">{error}</p>}
    </div>
  );
}
