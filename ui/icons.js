/**
 * Inline SVG icon library.
 *
 * No lucide, no emoji, no external font icons. Every glyph is a hand-tuned
 * SVG path drawn at 24x24 with stroke-based styling so colour and size
 * inherit from the CSS context.
 *
 * Usage:  <span data-icon="brain"></span>
 *         (Hydrated on DOMContentLoaded by Icons.hydrate)
 */

const Icons = (() => {
  const wrap = (path) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;

  const lib = {
    happiness: wrap(`<circle cx="12" cy="12" r="9"/><path d="M8 14c1.2 1.4 2.5 2 4 2s2.8-.6 4-2"/><circle cx="9" cy="10" r=".6" fill="currentColor"/><circle cx="15" cy="10" r=".6" fill="currentColor"/>`),
    health: wrap(`<path d="M20.4 4.6a5.5 5.5 0 0 0-7.8 0L12 5.2l-.6-.6a5.5 5.5 0 0 0-7.8 7.8l.6.6L12 20.8l7.8-7.8.6-.6a5.5 5.5 0 0 0 0-7.8z"/>`),
    smarts: wrap(`<path d="M9.5 3a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 1.5 5 3 3 0 0 0 3.5 4V3z"/><path d="M14.5 3a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-1.5 5 3 3 0 0 1-3.5 4V3z"/><path d="M9.5 12h5"/>`),
    looks: wrap(`<polygon points="12,3 14.6,9 21,9.5 16,13.8 17.7,20 12,16.6 6.3,20 8,13.8 3,9.5 9.4,9"/>`),
    list: wrap(`<line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/><circle cx="3" cy="6" r=".6" fill="currentColor"/><circle cx="3" cy="12" r=".6" fill="currentColor"/><circle cx="3" cy="18" r=".6" fill="currentColor"/>`),
    briefcase: wrap(`<rect x="3" y="7" width="18" height="13" rx="1"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><line x1="3" y1="13" x2="21" y2="13"/>`),
    link: wrap(`<path d="M10 14a3.5 3.5 0 0 0 5 0l3-3a3.5 3.5 0 0 0-5-5l-1.5 1.5"/><path d="M14 10a3.5 3.5 0 0 0-5 0l-3 3a3.5 3.5 0 0 0 5 5l1.5-1.5"/>`),
    pulse: wrap(`<path d="M3 12h4l2-6 4 12 2-6h6"/>`),
    ellipsis: wrap(`<circle cx="6" cy="12" r="1.5" fill="currentColor"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/><circle cx="18" cy="12" r="1.5" fill="currentColor"/>`),
    heart: wrap(`<path d="M20.4 4.6a5.5 5.5 0 0 0-7.8 0L12 5.2l-.6-.6a5.5 5.5 0 0 0-7.8 7.8l.6.6L12 20.8l7.8-7.8.6-.6a5.5 5.5 0 0 0 0-7.8z"/>`),
    book: wrap(`<path d="M4 5a2 2 0 0 1 2-2h13v17H6a2 2 0 0 0-2 2V5z"/><line x1="19" y1="20" x2="6" y2="20"/>`),
    chevron: wrap(`<polyline points="9 6 15 12 9 18"/>`),
    "chevron-left": wrap(`<polyline points="15 6 9 12 15 18"/>`),
    infant: wrap(`<circle cx="12" cy="9" r="5"/><circle cx="10" cy="9" r=".5" fill="currentColor"/><circle cx="14" cy="9" r=".5" fill="currentColor"/><path d="M10.5 11.5c.9.7 2.1.7 3 0"/><path d="M7 14c-1 2-1 4 .5 5.5C9 21 11 21 12 21s3 0 4.5-1.5C18 18 18 16 17 14"/>`),
    school: wrap(`<path d="M3 8.5 12 4l9 4.5-9 4.5z"/><path d="M7 10.5V15c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5v-4.5"/><line x1="21" y1="8.5" x2="21" y2="13"/>`),
    dumbbell: wrap(`<line x1="5" y1="8" x2="5" y2="16"/><line x1="3" y1="10" x2="3" y2="14"/><line x1="19" y1="8" x2="19" y2="16"/><line x1="21" y1="10" x2="21" y2="14"/><line x1="7" y1="12" x2="17" y2="12"/>`),
    stethoscope: wrap(`<path d="M5 4v6a4 4 0 0 0 8 0V4"/><line x1="5" y1="4" x2="5" y2="3"/><line x1="13" y1="4" x2="13" y2="3"/><path d="M9 14v2a4 4 0 0 0 4 4h0a4 4 0 0 0 4-4v-2"/><circle cx="17" cy="11" r="2"/>`),
    people: wrap(`<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 2.7-5 6-5s6 2 6 5"/><circle cx="17" cy="10" r="2.5"/><path d="M14 20c0-2 1.7-4 4-4s3 1 3 3"/>`),
    hourglass: wrap(`<path d="M6 3h12M6 21h12M7 3v3c0 2 5 3 5 6s-5 4-5 6v3"/><path d="M17 3v3c0 2-5 3-5 6s5 4 5 6v3"/>`),
    building: wrap(`<rect x="4" y="3" width="16" height="18" rx="1"/><line x1="8" y1="7" x2="10" y2="7"/><line x1="14" y1="7" x2="16" y2="7"/><line x1="8" y1="11" x2="10" y2="11"/><line x1="14" y1="11" x2="16" y2="11"/><path d="M10 21v-4h4v4"/>`),
  };

  function hydrate(root = document) {
    root.querySelectorAll("[data-icon]").forEach((el) => {
      const name = el.getAttribute("data-icon");
      if (lib[name]) el.innerHTML = lib[name];
    });
  }

  function get(name) {
    return lib[name] || "";
  }

  return { hydrate, get };
})();
