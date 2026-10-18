export const dateLabel = (value) => value ? new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' }).format(new Date(value.length === 10 ? `${value}T12:00:00+05:30` : value)) : 'Not recorded';
export const timeLabel = (value) => new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(new Date(value));
export const slotLabel = (slot) => `${timeLabel(slot.start)} – ${timeLabel(slot.end)} IST`;
export const formatSlot = (value) => `${dateLabel(value)}, ${timeLabel(value)} IST`;
export const statusLabel = (status, reason) => reason === 'product_deleted' && status === 'CLOSED' ? 'Closed — product deleted' : ({ PROCESSING: 'Registering', AWAITING_USER: 'Your input needed', PAUSED: 'Resuming', AWAITING_APPOINTMENT: 'Confirm visit', BOOKED: 'Visit scheduled', CLOSED: 'Resolved', ERROR: 'Needs attention' }[status] || status);
export const caseAction = (row) => row.status === 'AWAITING_APPOINTMENT' ? 'Confirm visit' : row.status === 'PROCESSING' ? 'View progress' : 'View complaint';
export const sortCases = (rows) => [...rows].sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')));
export const caseName = (row) => row.factsSnapshot?.product?.displayName || 'Product';
export function warrantyStatus(product, today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date())) {
  if (!product.warrantyExpiry) return 'Warranty details missing';
  return product.warrantyExpiry >= today ? 'Under warranty' : 'Out of warranty';
}
