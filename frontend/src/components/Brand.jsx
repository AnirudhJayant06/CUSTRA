export default function Brand({ compact = false }) {
  return <span className={`brand-logo ${compact ? 'compact' : ''}`} role="img" aria-label="Custra">
    <svg className="logo-symbol" viewBox="552 232 344 392" aria-hidden="true"><image href="/custra-identity.png" width="1448" height="1086" /></svg>
    {!compact ? <svg className="logo-word" viewBox="350 625 750 185" aria-hidden="true"><image href="/custra-identity.png" width="1448" height="1086" /></svg> : null}
  </span>;
}
