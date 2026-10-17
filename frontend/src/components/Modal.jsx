import { useEffect, useRef } from 'react';
import Icon from './Icon.jsx';
export function trapDialogFocus(event) {
  if (event.key !== 'Tab') return;
  const element = event.currentTarget;
  const items = [...element.querySelectorAll('button, input, select, textarea, a[href], [tabindex="0"]')].filter((node) => !node.disabled && node.getClientRects().length);
  const first = items[0]; const last = items.at(-1);
  if (!first) { event.preventDefault(); element.focus(); return; }
  if (event.shiftKey && (document.activeElement === first || document.activeElement === element)) { event.preventDefault(); last.focus(); }
  if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}
export default function Modal({ title, onClose, children, busy = false, className = '', dismissOnBackdrop = false }) {
  const ref = useRef(null);
  const backdropPress = useRef(false);
  function outside(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    return event.target === event.currentTarget && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom);
  }
  useEffect(() => {
    const previous = document.activeElement;
    const element = ref.current;
    element.showModal();
    return () => { element.close(); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className={`dialog-card ${className}`} aria-label={title} onKeyDown={trapDialogFocus} onCancel={(e) => { e.preventDefault(); if (!busy) onClose(); }} onPointerDown={(e) => { backdropPress.current = outside(e); }} onClick={(e) => { if (dismissOnBackdrop && !busy && backdropPress.current && outside(e)) onClose(); backdropPress.current = false; }}>
    <div className="dialog-heading"><h2>{title}</h2><button type="button" className="icon-button" aria-label="Close" disabled={busy} onClick={onClose}><Icon name="close" /></button></div>{children}
  </dialog>;
}
