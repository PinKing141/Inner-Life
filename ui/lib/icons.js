/* ============================================================================
   LIFE — ICONS table
   ----------------------------------------------------------------------------
   Single source of truth for the inline-SVG glyph library used throughout the
   UI. Each value is the inner-markup of a 24×24 viewBox SVG; the consumer
   (life-ui.js' `svg()` helper) wraps it in the <svg> tag with the right
   stroke / fill defaults. Kept separate so life-ui.js stays focused on
   structural code rather than 40 lines of path data.
   ============================================================================ */
window.LIFE_ICONS = {
  infant:`<circle cx="12" cy="9" r="3.4"/><path d="M6 20c.5-3.4 3-5.3 6-5.3s5.5 1.9 6 5.3" stroke-linecap="round"/>`,
  child:`<circle cx="12" cy="8" r="3.4"/><path d="M5.5 20c.6-3.6 3.3-5.6 6.5-5.6S17.9 16.4 18.5 20" stroke-linecap="round"/>`,
  cap:`<path d="M12 4l10 4-10 4L2 8z M6 10.5V15c0 1.7 2.7 3 6 3s6-1.3 6-3v-4.5" stroke-linecap="round" stroke-linejoin="round"/>`,
  adult:`<circle cx="12" cy="7.5" r="3.2"/><path d="M5.5 20c0-4 3-6.3 6.5-6.3S18.5 16 18.5 20" stroke-linecap="round"/>`,
  assets:`<rect x="4" y="9" width="16" height="11" rx="1.5"/><path d="M8 9V6.5A1.5 1.5 0 0 1 9.5 5h5A1.5 1.5 0 0 1 16 6.5V9M4 13h16" stroke-linecap="round"/>`,
  heart:`<path d="M12 20s-6.5-3.9-6.5-9A3.5 3.5 0 0 1 12 8.4 3.5 3.5 0 0 1 18.5 11c0 5.1-6.5 9-6.5 9z" stroke-linejoin="round"/>`,
  dots:`<circle cx="6" cy="12" r="1.7" fill="currentColor"/><circle cx="12" cy="12" r="1.7" fill="currentColor"/><circle cx="18" cy="12" r="1.7" fill="currentColor"/>`,
  hourglass:`<path d="M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9" stroke-linecap="round" stroke-linejoin="round"/>`,
  happy:`<circle cx="12" cy="12" r="9"/><path d="M8.5 14.5a4.5 4.5 0 0 0 7 0" stroke-linecap="round"/><circle cx="9" cy="10" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r="1" fill="currentColor" stroke="none"/>`,
  health:`<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/><path d="M5 12h3l1.5-3 2.5 6 1.8-3.6L16 12h3" stroke-linecap="round" stroke-linejoin="round"/>`,
  smarts:`<path d="M9 4.5A3 3 0 0 0 6 9a3 3 0 0 0-1 5.5A3 3 0 0 0 9 19.5V4.5z"/><path d="M15 4.5A3 3 0 0 1 18 9a3 3 0 0 1 1 5.5A3 3 0 0 1 15 19.5V4.5z"/><path d="M12 5v14" stroke-linecap="round"/>`,
  looks:`<path d="M12 3l1.9 4.4L18.5 9l-3.8 3 1 4.9L12 14.6 8.3 16.9l1-4.9L5.5 9l4.6-1.6z" stroke-linejoin="round"/>`,
  house:`<path d="M4 11l8-6 8 6M6 10v9h12v-9M10 19v-5h4v5" stroke-linecap="round" stroke-linejoin="round"/>`,
  car:`<path d="M4 14l2-5h12l2 5M3 14h18v4H3zM6 18v1.5M18 18v1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="7.5" cy="14.5" r="1.4"/><circle cx="16.5" cy="14.5" r="1.4"/>`,
  bike:`<circle cx="6" cy="16" r="3.4"/><circle cx="18" cy="16" r="3.4"/><path d="M6 16l4-7h5l-3 7M10 9l-2-3h3" stroke-linecap="round" stroke-linejoin="round"/>`,
  gem:`<path d="M6 4h12l3 5-9 11L3 9z M3 9h18 M9 4l-3 5 6 11 6-11-3-5" stroke-linejoin="round"/>`,
  pet:`<circle cx="7" cy="9" r="1.8"/><circle cx="12" cy="7" r="1.8"/><circle cx="17" cy="9" r="1.8"/><path d="M12 12c-3 0-5 2.6-5 5 0 2 1.6 2.5 2.8 1.6.9-.7 3.5-.7 4.4 0 1.2.9 2.8.4 2.8-1.6 0-2.4-2-5-5-5z" stroke-linejoin="round"/>`,
  doctor:`<path d="M9 4v4a3 3 0 0 0 6 0V4M9 4h6M12 11v3a5 5 0 0 0 5 5 3 3 0 0 0 3-3v-1" stroke-linecap="round" stroke-linejoin="round"/><circle cx="20" cy="14" r="2"/>`,
  book:`<path d="M5 5.5A2 2 0 0 1 7 4h12v14H7a2 2 0 0 0-2 2zM5 5.5V20M19 18v3H7" stroke-linecap="round" stroke-linejoin="round"/>`,
  dumbbell:`<path d="M4 9v6M7 7v10M17 7v10M20 9v6M7 12h10" stroke-linecap="round"/>`,
  brief:`<rect x="3" y="8" width="18" height="12" rx="2"/><path d="M9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18" stroke-linecap="round"/>`,
  moon:`<path d="M18 14.5A8 8 0 0 1 8.5 5 8 8 0 1 0 18 14.5z" stroke-linejoin="round"/>`,
  lotus:`<path d="M12 20c4-1 8-4 8-8-2 0-3.5 1-4.5 2.5M12 20c-4-1-8-4-8-8 2 0 3.5 1 4.5 2.5M12 20c0-5 0-9 0-13-2.5 2.5-3 5.5-2.5 8.5M12 7c2.5 2.5 3 5.5 2.5 8.5" stroke-linecap="round" stroke-linejoin="round"/>`,
  person:`<circle cx="12" cy="7.5" r="3.4"/><path d="M5.5 20c0-3.8 3-6 6.5-6s6.5 2.2 6.5 6" stroke-linecap="round"/>`,
  spark:`<path d="M12 3v6M12 15v6M3 12h6M15 12h6M6 6l3.5 3.5M14.5 14.5L18 18M18 6l-3.5 3.5M9.5 14.5L6 18" stroke-linecap="round"/>`,
  trophy:`<path d="M7 4h10v4a5 5 0 0 1-10 0zM7 6H4v1a4 4 0 0 0 3 3.9M17 6h3v1a4 4 0 0 1-3 3.9M9 17h6M10 14v3M14 14v3M8 20h8" stroke-linecap="round" stroke-linejoin="round"/>`,
  pen:`<path d="M14 4l6 6M4 20l3-1L18 8l-3-3L4 16z" stroke-linecap="round" stroke-linejoin="round"/>`,
  music:`<path d="M9 18V5l11-2v13" stroke-linecap="round" stroke-linejoin="round"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>`,
  save:`<path d="M5 4h11l3 3v13H5zM8 4v5h7V4M8 20v-6h8v6" stroke-linecap="round" stroke-linejoin="round"/>`,
  menu:`<path d="M4 7h16M4 12h16M4 17h16" stroke-linecap="round"/>`,
  lock:`<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3" stroke-linecap="round"/>`,
  chevron:`<path d="M9 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/>`,
  check:`<path d="M5 12.5l4.5 4.5L19 7" stroke-linecap="round" stroke-linejoin="round"/>`,
  x:`<path d="M6 6l12 12M18 6L6 18" stroke-linecap="round"/>`,
  box:`<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M4 10h16M9 14h6" stroke-linecap="round"/>`,
  warn:`<path d="M12 4l9 16H3zM12 10v5M12 17.5v.5" stroke-linecap="round" stroke-linejoin="round"/>`,
  dummy:`<circle cx="12" cy="5" r="2.5"/><circle cx="12" cy="14" r="6"/><circle cx="12" cy="14" r="2"/><path d="M6.7 11.5 4 10.5M17.3 11.5 20 10.5" stroke-linecap="round"/>`,
  students:`<path d="M3 8l9-3.5L21 8l-9 3.5z" stroke-linejoin="round"/><path d="M7 10v3.5c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5V10" stroke-linecap="round"/><circle cx="12" cy="18.5" r="1.6"/><path d="M9 22c0-1.4 1.3-2.5 3-2.5s3 1.1 3 2.5" stroke-linecap="round"/>`,
};
