export default function ConversationTimeline({ events, pending }) {
  return <section className="conversation" aria-label="Automated conversation">
    <h2>Automated conversation</h2>
    <p className="hint">Custra answers on your behalf. The Business Agent is a simulator.</p>
    <ol className="record-list" aria-live="polite" aria-relevant="additions">
      {events.map((event) => <li key={event.eventId} className={`message message-${event.role}`}>
        <strong>{event.role === 'consumer' ? 'Consumer Agent · Custra' : event.role === 'user' ? 'You · Resolution confirmation' : 'Business Agent · Simulated'}</strong>
        <p>{event.displayText}</p>
      </li>)}
    </ol>
    {pending ? <p role="status">Working on the next saved step…</p> : null}
  </section>;
}
