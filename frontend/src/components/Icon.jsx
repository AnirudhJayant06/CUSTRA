const paths = {
  lock: 'M5 10h14v12H5Zm3 0V6a4 4 0 0 1 8 0v4m-4 5v3',
  camera: 'M3 7h4l2-3h6l2 3h4v14H3Zm13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z', photo: 'M3 3h18v18H3Zm1 15 6-7 4 4 3-3 4 6M8 7h1',
  home: 'm3 10 9-7 9 7v11h-6v-7H9v7H3Z', products: 'm12 3 9 5v9l-9 5-9-5V8Zm0 10 9-5M12 13 3 8m9 5v9',
  complaints: 'M4 3h16v17H8l-4 3ZM8 8h8M8 12h8M8 16h5', user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 22v-3a8 8 0 0 1 16 0v3',
  plus: 'M12 4v16M4 12h16', search: 'M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0Zm-1 5 6 6', arrow: 'm9 5 7 7-7 7', back: 'm15 5-7 7 7 7',
  pin: 'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  calendar: 'M4 5h16v17H4ZM8 2v6m8-6v6M4 11h16', clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 6v6l4 2',
  phone: 'M6 3 3 6c0 8 7 15 15 15l3-3-5-4-3 2-5-5 2-3Z', file: 'M5 2h9l5 5v15H5ZM14 2v6h5',
  logout: 'M10 3H3v18h7m4-15 6 6-6 6m-7-6h13', check: 'm5 12 4 4L20 5', close: 'm5 5 14 14M5 19 19 5',
  television: 'M2 4h20v14H2Zm10 14v4m-5 0h10', refrigerator: 'M5 2h14v20H5Zm0 8h14M8 5v1m0 6v5',
  washingmachine: 'M4 2h16v20H4Zm0 5h16M7 4h1m3 9a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z',
  smartphone: 'M7 2h10v20H7Zm3 3h4m-3 14h2', microwave: 'M2 5h20v14H2Zm3 3h10v8H5Zm13 1h1m-1 4h1',
  airconditioner: 'M2 4h20v10H2Zm3 7h14m-12 6v4m5-4v5m5-5v4', laptop: 'M4 3h16v14H4ZM2 21h20l-2-4H4Z',
};
export default function Icon({ name, size = 22, ...props }) {
  const key = name?.replaceAll('-', '').replaceAll('_', '');
  const category = key?.includes('tv') ? 'television' : key?.includes('fridge') ? 'refrigerator' : key?.includes('washing') ? 'washingmachine' : key;
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[category] || paths.products} /></svg>;
}
