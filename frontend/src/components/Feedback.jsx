import { useEffect, useId, useRef } from 'react';

export function Notice({ message, onClose }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = setTimeout(onClose, 4500);
    return () => clearTimeout(timer);
  }, [message, onClose]);
  return message ? <div className="notice" role="status">{message}<button type="button" onClick={onClose} aria-label="Đóng thông báo">×</button></div> : null;
}

export function ResourceState({ loading, error, empty, onRetry }) {
  if (loading) return <div className="state" role="status">Đang tải dữ liệu…</div>;
  if (error) return <div className="state state--error" role="alert">{error} <button type="button" className="text-button" onClick={onRetry}>Thử lại</button></div>;
  if (empty) return <div className="state">Chưa có dữ liệu. Hãy thêm mục đầu tiên để bắt đầu.</div>;
  return null;
}

export function Modal({ title, children, onClose }) {
  const modalRef = useRef(null);
  const closeRef = useRef(onClose);
  const titleId = useId();
  closeRef.current = onClose;
  useEffect(() => {
    const previousFocus = document.activeElement;
    (modalRef.current?.querySelector('input, select, textarea') || modalRef.current?.querySelector('button'))?.focus();
    const onKey = (event) => {
      if (event.key === 'Escape') closeRef.current();
      if (event.key !== 'Tab') return;
      const focusable = [...modalRef.current.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href]')];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); previousFocus?.focus(); };
  }, []);
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section ref={modalRef} className="modal" role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <div className="modal__head"><h2 id={titleId}>{title}</h2><button type="button" className="icon-button" onClick={onClose} aria-label="Đóng">×</button></div>
      {children}
    </section>
  </div>;
}
