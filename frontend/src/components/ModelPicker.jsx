import { useState } from 'react';
import Modal from './Modal.jsx';
import Icon from './Icon.jsx';
export default function ModelPicker({ options, value, custom, disabled, onChange }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const current = options.find((m) => m.number === value);
  const matches = options.filter((m) => `${m.name} ${m.number}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  function select(number, manual = false) { onChange(number, manual); setOpen(false); }
  return <div><label id="model-label">Model <span className="optional">(optional)</span></label><button type="button" className="select-button" disabled={disabled} aria-label="Model" aria-haspopup="dialog" onClick={() => { setSearch(''); setOpen(true); }}><span>{value ? current && current.name !== current.number ? `${current.name} · ${value}` : value : 'Choose a model or leave blank'}</span><Icon name="arrow" size={18} /></button>
    {custom ? <><label htmlFor="model-number">Model number</label><input id="model-number" name="modelNumber" value={value} onChange={(e) => onChange(e.target.value, true)} maxLength={120} placeholder="Enter model name or number" /></> : null}
    {open ? <Modal title="Choose model" onClose={() => setOpen(false)}><label className="search-field"><Icon name="search" /><input type="search" autoComplete="off" aria-label="Search models" placeholder="Search model name or number" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
      <ul className="plain-list model-options">{matches.map((m) => <li key={m.number}><button type="button" className="slim-row" onClick={() => select(m.number)}><span><strong>{m.name}</strong>{m.number !== m.name ? <small>{m.number}</small> : null}</span>{value === m.number ? <Icon name="check" /> : <Icon name="arrow" />}</button></li>)}</ul>
      {!matches.length ? <p className="hint">{options.length ? 'No matching suggestion. You can enter your own model.' : 'No verified suggestions for this brand yet. Enter your model or leave it blank.'}</p> : null}
      <button type="button" className="slim-row" onClick={() => select('', true)}><span>Other — enter manually</span><Icon name="plus" /></button><button type="button" className="slim-row" onClick={() => select('', false)}><span>I don’t know</span></button><p className="hint">Suggestions may not include older or regional variants. Check the model on your device or invoice.</p>
    </Modal> : null}
  </div>;
}
