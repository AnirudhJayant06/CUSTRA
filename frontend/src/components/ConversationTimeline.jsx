export default function ConversationTimeline({ events, pending, closed = false }) {
  return <section className={`conversation${closed ? ' is-closed' : ''}`} data-read-only={closed} aria-label={closed ? 'Agent conversation (read-only)' : 'Agent conversation'}><h2 className="sr-only">Agent conversation</h2>
    <ol className="chat-list" aria-live={closed ? 'off' : 'polite'} aria-relevant="additions">{events.map((event) => <li key={event.eventId} className={`message message-${event.role}`}><span className="speaker">{event.role === 'consumer' ? 'Custra · your agent' : event.role === 'user' ? 'You' : event.role === 'system' ? 'Custra' : 'Business support · simulated'}</span><p>{event.displayText}</p></li>)}</ol>
    {pending ? <p className="processing" role="status">Custra is working on the next step…</p> : null}</section>;
}
