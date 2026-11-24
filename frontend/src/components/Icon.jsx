const paths = {
  logo: <><path d="M12 2.5c4.8 2.5 7.5 6.4 7.5 10.1A7.5 7.5 0 1 1 4.5 13C4.5 8.8 7.4 5.1 12 2.5Z" /><path d="M12 20V9m0 7-4-4m4 2 4-4" /></>,
  home: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V10Z" /><path d="M9 21v-7h6v7" /></>,
  camera: <><path d="M4 7h3l2-3h6l2 3h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z" /><circle cx="12" cy="14" r="3.5" /></>,
  menu: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M8 4v16M12 9h6m-6 4h6m-6 4h4" /></>,
  diary: <><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 3v18m4-13h5m-5 4h5m-5 4h3" /></>,
  family: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-2a6 6 0 0 1 12 0v2H3Z" /><circle cx="18" cy="9" r="2.5" /><path d="M17 14a5 5 0 0 1 4 5v1h-4" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M10 2h4l.6 2.2 2 1.1 2.2-.7 2 3.5-1.6 1.7v2.4l1.6 1.7-2 3.5-2.2-.7-2 1.1L14 22h-4l-.6-2.2-2-1.1-2.2.7-2-3.5 1.6-1.7v-2.4L3.2 10l2-3.5 2.2.7 2-1.1L10 2Z" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" /></>,
  plate: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4.5" /><path d="M2 4v16M22 4v16" /></>,
  moon: <path d="M19.5 15.5A8 8 0 0 1 8.5 4.5a8 8 0 1 0 11 11Z" />,
  bowl: <><path d="M3 13h18a9 9 0 0 1-18 0Zm6 8h6" /><path d="M7 10c0-2 2-2 2-4m3 4c0-2 2-2 2-4m3 4c0-2 2-2 2-4" /></>,
  leaf: <><path d="M20 4c-9 0-15 3-15 10a6 6 0 0 0 6 6c7 0 10-6 9-16Z" /><path d="M5 19c3-4 6-7 12-10" /></>,
  sparkles: <><path d="m12 2 1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8L12 2Zm7 13 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" /></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
  unlock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  check: <path d="m4 12 5 5L20 6" />,
  logout: <><path d="M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h5" /><path d="M13 7l5 5-5 5m5-5H8" /></>,
};

const legacyNames = { '🥣': 'bowl', '🍚': 'plate', '🥬': 'leaf', '🍽️': 'plate', '☀️': 'sun', '🌙': 'moon' };

export default function Icon({ name, size = 20, className = '', ...rest }) {
  return <svg className={`icon ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...rest}>{paths[legacyNames[name] || name] || paths.leaf}</svg>;
}
