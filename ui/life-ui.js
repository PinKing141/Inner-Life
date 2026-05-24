/* ============================================================================
   LIFE — A DEEPER SIMULATION  ·  UI ADAPTER  (life-ui.js)   v1.1
   ----------------------------------------------------------------------------
   See docs/UI-PATTERN-GUIDE.md for the architectural seam and full vocabulary.
   ============================================================================ */

const LifeUI = (function () {
  'use strict';

  const ICONS = {
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
  };
  const svg = (key, sw = 1.9) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}">${ICONS[key] || ICONS.box}</svg>`;

  const S = { root: null, screens: [], handlers: {}, creation: null };
  const $ = (sel, ctx) => (ctx || S.root).querySelector(sel);
  const money = n => (n < 0 ? '-' : '') + '£' + Math.abs(Math.round(n)).toLocaleString();
  const esc = s => String(s == null ? '' : s);

  function section(label, count) {
    return `<div class="ui-section"><span class="lbl">${esc(label)}</span>` +
           `<span class="rule"></span>` +
           (count != null ? `<span class="count">${count}</span>` : '') + `</div>`;
  }
  function meter(value, colorVar) {
    const v = Math.max(0, Math.min(100, value || 0));
    return `<div class="ui-meter" style="--accent:${colorVar || 'var(--gold)'}">` +
           `<i style="width:${v}%"></i></div>`;
  }
  function pill(text, colorVar, iconKey) {
    return `<span class="ui-pill" style="--accent:${colorVar || 'var(--gold)'}">` +
           (iconKey ? svg(iconKey) : '') + esc(text) + `</span>`;
  }
  function empty(message) {
    return `<div class="ui-empty">${svg('box')}<p>${esc(message)}</p></div>`;
  }
  function button(spec) {
    const variant = spec.variant || 'ghost';
    const attrs = spec.action
      ? ` data-action="${esc(spec.action)}"` +
        ` data-payload="${encodeURIComponent(JSON.stringify(spec.payload ?? null))}"`
      : '';
    return `<button class="ui-btn ${variant}${spec.wide ? ' wide' : ''}"` +
           `${spec.disabled ? ' disabled' : ''}${attrs}>` +
           (spec.icon ? svg(spec.icon) : '') + esc(spec.label) + `</button>`;
  }
  function item(spec) {
    const accent = spec.accent || 'var(--gold)';
    let trail = '';
    const t = spec.trailing;
    if (t) {
      if (t.kind === 'value')
        trail = `<span class="value${t.negative ? ' neg' : ''}">${esc(t.text)}</span>`;
      else if (t.kind === 'meter')
        trail = `<span class="meter-wrap">${meter(t.value, t.color)}` +
                `<span class="pct">${Math.round(t.value)}%</span></span>`;
      else if (t.kind === 'badge')
        trail = pill(t.text, accent, t.icon);
      else if (t.kind === 'chevron')
        trail = `<span class="chevron">${svg('chevron', 2)}</span>`;
    }
    const tappable = spec.action && !spec.locked;
    const attrs = tappable
      ? ` data-action="${esc(spec.action)}"` +
        ` data-payload="${encodeURIComponent(JSON.stringify(spec.payload ?? null))}"`
      : '';
    const tag = tappable ? 'button' : 'div';
    return `<${tag} class="ui-item${tappable ? ' is-tappable' : ''}` +
           `${spec.locked ? ' is-locked' : ''}" style="--accent:${accent}"${attrs}>` +
           `<span class="ui-tile">${svg(spec.icon || 'box')}</span>` +
           `<span class="body"><span class="title">${esc(spec.title)}</span>` +
           (spec.subtitle ? `<span class="subtitle">${esc(spec.subtitle)}</span>` : '') +
           `</span>` +
           (trail ? `<span class="ui-trail">${trail}</span>` : '') +
           `</${tag}>`;
  }
  function eventHTML(e, latest) {
    const cat = e.category || 'event';
    return `<div class="ui-event t-${cat}${latest ? ' is-latest' : ''}` +
           `${cat === 'birth' ? ' is-birth' : ''}${latest ? ' fresh' : ''}" ` +
           `style="--accent:var(--cat-${cat},var(--gold))">` +
           `<div class="node">${esc(e.age)}</div>` +
           `<div class="card"><div class="cat"><i></i>` +
           `<span>${esc(e.label || cat)}</span>` +
           `<span class="age">Age ${esc(e.age)}</span></div>` +
           `<div class="text">${e.text == null ? '' : e.text}</div></div></div>`;
  }

  const KIND_DEFAULTS = {
    event:   { icon: 'spark',  accent: 'var(--cat-event)',     eyebrow: 'Pending Event' },
    offer:   { icon: 'brief',  accent: 'var(--cat-money)',     eyebrow: 'Offer' },
    notice:  { icon: 'warn',   accent: 'var(--cat-event)',     eyebrow: 'Notice' },
    confirm: { icon: 'warn',   accent: 'var(--c-warn)',        eyebrow: 'Confirm' },
    profile: { icon: 'person', accent: 'var(--cat-family)',    eyebrow: 'Profile' },
    exam:    { icon: 'pen',    accent: 'var(--cat-education)', eyebrow: 'Examination' },
    picker:  { icon: 'box',    accent: 'var(--gold)',          eyebrow: 'Choose' },
    award:   { icon: 'trophy', accent: 'var(--gold-bright)',   eyebrow: 'Awarded' },
  };

  function blockHTML(b, accent) {
    if (b.type === 'text')
      return `<p class="ui-mtext">${b.text == null ? '' : b.text}</p>`;
    if (b.type === 'divider')
      return `<div class="ui-mdiv"></div>`;
    if (b.type === 'choices') {
      return `<div class="ui-choices">` + b.choices.map(c => {
        const ca = c.action || b.action || 'modal-choice';
        const pl = encodeURIComponent(JSON.stringify(
          Object.assign({ choiceId: c.id }, b.payload || {}, c.payload || {})));
        return `<button class="ui-choice" style="--accent:${c.accent || accent}"` +
               `${c.disabled ? ' disabled' : ''}` +
               ` data-action="${esc(ca)}" data-payload="${pl}"` +
               `${c.keepOpen ? ' data-keepopen="1"' : ''}>` +
               `<span class="c-body"><span class="c-label">${esc(c.label)}</span>` +
               (c.note ? `<span class="c-note">${esc(c.note)}</span>` : '') +
               `</span><span class="c-arrow">${svg('chevron', 2)}</span></button>`;
      }).join('') + `</div>`;
    }
    if (b.type === 'deltas') {
      return `<div class="ui-deltas">` + b.deltas.map(d =>
        `<div class="ui-delta"><span class="d-label">${esc(d.label)}</span>` +
        `<span class="d-value ${d.tone || ''}">${esc(d.value)}</span></div>`
      ).join('') + `</div>`;
    }
    if (b.type === 'list') {
      return (b.items && b.items.length)
        ? b.items.map(item).join('')
        : empty(b.emptyText || 'Nothing here.');
    }
    if (b.type === 'award') {
      return `<div class="ui-award">` +
             `<div class="a-ring">${svg(b.icon || 'trophy')}</div>` +
             `<div class="a-title">${esc(b.title)}</div>` +
             (b.subtitle ? `<div class="a-sub">${esc(b.subtitle)}</div>` : '') +
             `</div>`;
    }
    if (b.type === 'section')
      return section(b.label, b.count);
    return '';
  }

  function modal(spec) {
    const k = KIND_DEFAULTS[spec.kind] || KIND_DEFAULTS.notice;
    const accent  = spec.accent  || k.accent;
    const icon    = spec.icon    || k.icon;
    const eyebrow = spec.eyebrow || k.eyebrow;
    const body = (spec.blocks || []).map(b => blockHTML(b, accent)).join('');
    const foot = (spec.actions && spec.actions.length)
      ? `<div class="ui-modal-foot"><div class="ui-btn-row">` +
        spec.actions.map(a => button(a)).join('') + `</div></div>`
      : '';
    const closeBtn = spec.dismissable
      ? `<button class="m-close" data-modal-close>${svg('x', 2.2)}</button>` : '';

    const ov = $('.ui-overlay');
    ov.dataset.dismissable = spec.dismissable ? '1' : '';
    ov.innerHTML = `
      <div class="ui-modal" style="--accent:${accent}">
        <div class="ui-modal-head">
          <div class="eyebrow">${esc(eyebrow)}</div>
          ${closeBtn}
          <div class="titlerow">
            <div class="m-ico">${svg(icon)}</div>
            <h3>${esc(spec.title)}</h3>
          </div>
        </div>
        <div class="ui-modal-body">${body}</div>
        ${foot}
      </div>`;
    if (spec.actions) {
      ov.querySelectorAll('.ui-modal-foot .ui-btn').forEach((btn, i) => {
        if (spec.actions[i] && spec.actions[i].keepOpen) btn.dataset.keepopen = '1';
      });
    }
    requestAnimationFrame(() => ov.classList.add('show'));
    return LifeUI;
  }

  function confirm(spec) {
    return modal({
      kind: 'confirm',
      title: spec.title || 'Are you sure?',
      dismissable: spec.dismissable !== false,
      blocks: spec.message ? [{ type: 'text', text: spec.message }] : [],
      actions: [
        { label: spec.cancelLabel || 'Cancel', variant: 'ghost',
          action: spec.cancelAction || '__close' },
        { label: spec.confirmLabel || 'Confirm',
          variant: spec.danger ? 'danger' : 'primary',
          action: spec.action || '__close', payload: spec.payload },
      ],
    });
  }

  function closeModal() {
    const ov = $('.ui-overlay');
    if (!ov) return;
    ov.classList.remove('show');
    setTimeout(() => { if (!ov.classList.contains('show')) ov.innerHTML = ''; }, 280);
  }

  const BUILTIN = [
    { id: 'life',       label: 'Infant',    icon: 'infant' },
    { id: 'assets',     label: 'Assets',    icon: 'assets' },
    { id: 'relations',  label: 'Relations', icon: 'heart'  },
    { id: 'activities', label: 'Activities',icon: 'dots'   },
  ];

  function registerScreen(id, opts) {
    opts = opts || {};
    if (S.screens.find(s => s.id === id)) return;
    S.screens.push({ id, label: opts.label || id, icon: opts.icon || 'box',
                     intro: opts.intro || '' });
    if (S.root && $('.app-screens')) buildScreensAndNav();
  }

  function renderScreen(id, groups) {
    const sc = S.screens.find(s => s.id === id);
    if (!sc || !sc.el) return;
    if (id === 'life') return;
    const intro = sc.intro ? `<p class="ui-intro">${esc(sc.intro)}</p>` : '';
    const body = (groups || []).map(g => {
      const head = g.label
        ? section(g.label, g.count != null ? g.count : (g.items ? g.items.length : 0))
        : '';
      const inner = (g.items && g.items.length)
        ? g.items.map(item).join('')
        : empty(g.emptyText || 'Nothing here yet.');
      return head + inner;
    }).join('');
    sc.el.innerHTML = intro + body;
  }

  function showScreen(id) {
    S.screens.forEach(s => {
      if (s.el) s.el.classList.toggle('is-active', s.id === id);
    });
    S.root.querySelectorAll('.app-nav button[data-screen]').forEach(b =>
      b.classList.toggle('is-active', b.dataset.screen === id));
    const sr = $('.app-screens');
    if (sr) sr.scrollTo({ top: 0, behavior: 'smooth' });
    fire('navigate', id);
  }

  function scene(name) {
    const app = $('.app');
    const cr  = $('.creation');
    if (name === 'creation') {
      if (app) app.style.display = 'none';
    } else {
      if (app) app.style.display = '';
      if (cr) cr.remove();
      S.creation = null;
    }
  }

  function creationShow(step) {
    let cr = $('.creation');
    if (!cr) {
      cr = document.createElement('div');
      cr.className = 'creation';
      S.root.querySelector('div').appendChild(cr);
    }
    scene('creation');

    S.creation = { stepId: step.id, values: {}, fields: step.fields || [] };
    (step.fields || []).forEach(f => {
      if (f.value != null) S.creation.values[f.key] = f.value;
    });

    const total = step.total || 1;
    const idx   = step.step  || 1;
    const dots = Array.from({ length: total }, (_, i) =>
      `<i class="${i < idx - 1 ? 'done' : i === idx - 1 ? 'now' : ''}"></i>`).join('');

    const fieldsHTML = (step.fields || []).map(creationFieldHTML).join('');

    cr.innerHTML = `
      <div class="cr-head">
        <div class="cr-progress">${dots}</div>
        <div class="step-no">Step ${idx} of ${total}</div>
        <h2>${esc(step.title)}</h2>
        ${step.subtitle ? `<div class="sub">${esc(step.subtitle)}</div>` : ''}
      </div>
      <div class="cr-body">${fieldsHTML}</div>
      <div class="cr-foot">
        ${step.back ? button({ label: 'Back', variant: 'ghost',
                               action: '__cr_back' }) : ''}
        ${button({ label: step.submitLabel || 'Continue', variant: 'primary',
                   action: '__cr_next', wide: !step.back, disabled: true })}
      </div>`;

    wireCreation(cr);
    refreshCreationSubmit(cr);
    return LifeUI;
  }

  function creationFieldHTML(f) {
    const head = `<span class="f-label">${esc(f.label)}</span>`;
    if (f.type === 'text') {
      return `<div class="cr-field" data-key="${esc(f.key)}">${head}` +
             `<input class="cr-input" type="text" data-cr-text ` +
             `placeholder="${esc(f.placeholder || '')}" ` +
             `value="${esc(f.value || '')}"></div>`;
    }
    if (f.type === 'segment') {
      const opts = f.options.map(o => {
        const id = typeof o === 'string' ? o : o.id;
        const lb = typeof o === 'string' ? o : o.label;
        return `<button data-cr-opt="${esc(id)}"` +
               `${f.value === id ? ' class="sel"' : ''}>${esc(lb)}</button>`;
      }).join('');
      return `<div class="cr-field" data-key="${esc(f.key)}" data-cr-field="segment">` +
             `${head}<div class="cr-segment">${opts}</div></div>`;
    }
    if (f.type === 'flaggrid') {
      const opts = f.options.map(o =>
        `<button class="cr-flag${f.value === o.id ? ' sel' : ''}" data-cr-opt="${esc(o.id)}">` +
        `<span class="fimg">${o.flag || ''}</span>` +
        `<span class="fname">${esc(o.label)}</span></button>`).join('');
      return `<div class="cr-field" data-key="${esc(f.key)}" data-cr-field="grid">` +
             `${head}<div class="cr-grid">${opts}</div></div>`;
    }
    if (f.type === 'cards') {
      const opts = f.options.map(o =>
        `<button class="cr-card${f.value === o.id ? ' sel' : ''}" data-cr-opt="${esc(o.id)}" ` +
        `style="--accent:${o.accent || 'var(--gold)'}">` +
        `<span class="cc-ico">${svg(o.icon || 'spark')}</span>` +
        `<span class="cc-body"><span class="cc-name">${esc(o.label)}</span>` +
        (o.desc ? `<span class="cc-desc">${esc(o.desc)}</span>` : '') +
        `</span></button>`).join('');
      return `<div class="cr-field" data-key="${esc(f.key)}" data-cr-field="cards">` +
             `${head}<div class="cr-cards">${opts}</div></div>`;
    }
    if (f.type === 'list') {
      const opts = f.options.map(o =>
        `<button class="cr-row${f.value === o.id ? ' sel' : ''}" data-cr-opt="${esc(o.id)}">` +
        `${esc(o.label)}${o.sub ? `<span class="r-sub">${esc(o.sub)}</span>` : ''}</button>`
      ).join('');
      return `<div class="cr-field" data-key="${esc(f.key)}" data-cr-field="list">` +
             `${head}<div class="cr-list">${opts}</div></div>`;
    }
    return '';
  }

  function wireCreation(cr) {
    cr.querySelectorAll('[data-cr-text]').forEach(inp => {
      const key = inp.closest('.cr-field').dataset.key;
      if (inp.value.trim()) S.creation.values[key] = inp.value.trim();
      inp.addEventListener('input', () => {
        S.creation.values[key] = inp.value.trim();
        refreshCreationSubmit(cr);
      });
    });
    cr.querySelectorAll('[data-cr-field]').forEach(field => {
      const key = field.dataset.key;
      field.querySelectorAll('[data-cr-opt]').forEach(opt => {
        opt.addEventListener('click', () => {
          field.querySelectorAll('[data-cr-opt]').forEach(o => o.classList.remove('sel'));
          opt.classList.add('sel');
          S.creation.values[key] = opt.dataset.crOpt;
          refreshCreationSubmit(cr);
        });
      });
    });
    cr.querySelector('[data-action="__cr_next"]').addEventListener('click', () => {
      fire('creation-submit', {
        stepId: S.creation.stepId,
        values: Object.assign({}, S.creation.values),
      });
    });
    const back = cr.querySelector('[data-action="__cr_back"]');
    if (back) back.addEventListener('click', () =>
      fire('creation-back', { stepId: S.creation.stepId }));
  }

  function refreshCreationSubmit(cr) {
    const done = S.creation.fields.every(f =>
      S.creation.values[f.key] != null && S.creation.values[f.key] !== '');
    const btn = cr.querySelector('[data-action="__cr_next"]');
    if (btn) btn.disabled = !done;
  }

  function on(name, fn) { (S.handlers[name] = S.handlers[name] || []).push(fn); }
  function fire(name, arg) { (S.handlers[name] || []).forEach(fn => fn(arg)); }

  function setIdentity(d) {
    d = d || {};
    if (d.name != null) $('.app-identity .nm').textContent = d.name;
    if (d.stage != null) {
      $('.app-identity .stage .txt').textContent = d.stage;
      const lifeTab = S.root.querySelector('.app-nav button[data-screen="life"] span');
      if (lifeTab) lifeTab.textContent = d.stage;
    }
    if (d.location != null) $('.app-identity .stage .loc').textContent = d.location;
    if (d.balance != null) $('.app-identity .bal .v').textContent = money(d.balance);
    if (d.flag != null) $('.app-identity .flag').innerHTML = d.flag;
  }

  const STAT_META = {
    happiness: { label: 'Happiness', icon: 'happy',  color: 'var(--c-happy)'  },
    health:    { label: 'Health',    icon: 'health', color: 'var(--c-health)' },
    smarts:    { label: 'Smarts',    icon: 'smarts', color: 'var(--c-smarts)' },
    looks:     { label: 'Looks',     icon: 'looks',  color: 'var(--c-looks)'  },
  };
  function setStats(stats) {
    Object.keys(stats || {}).forEach(key => {
      const row = S.root.querySelector(`.ui-stat[data-stat="${key}"]`);
      if (!row) return;
      const v = Math.max(0, Math.min(100, Math.round(stats[key])));
      row.querySelector('.ui-meter > i').style.width = v + '%';
      row.querySelector('.num').textContent = v;
    });
  }

  function logEvent(e) {
    const tl = $('.app-screens .screen[data-screen="life"] .ui-timeline');
    if (!tl) return;
    tl.querySelectorAll('.ui-event.is-latest').forEach(n =>
      n.classList.remove('is-latest', 'fresh'));
    tl.insertAdjacentHTML('beforeend', eventHTML(e, true));
    tl.lastElementChild.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function clearLife() {
    const tl = $('.app-screens .screen[data-screen="life"] .ui-timeline');
    if (tl) tl.innerHTML = '';
  }

  let toastTimer;
  function toast(msg) {
    const t = $('.ui-toast');
    t.querySelector('span').textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
  }

  function buildScreensAndNav() {
    const screensEl = $('.app-screens');
    const navEl = $('.app-nav');
    screensEl.innerHTML = '';
    S.screens.forEach(s => {
      const div = document.createElement('div');
      div.className = 'screen';
      div.dataset.screen = s.id;
      if (s.id === 'life') div.innerHTML = '<div class="ui-timeline"></div>';
      s.el = div;
      screensEl.appendChild(div);
    });
    const navScreens = S.screens.slice(0, 4);
    const cells = [];
    navScreens.slice(0, 2).forEach(s => cells.push(navBtn(s)));
    cells.push('<div class="nav-spacer"></div>');
    navScreens.slice(2, 4).forEach(s => cells.push(navBtn(s)));
    navEl.innerHTML = cells.join('');
    if (S.screens[0]) showScreen(S.screens[0].id);
  }
  function navBtn(s) {
    return `<button data-screen="${s.id}"><svg viewBox="0 0 24 24" fill="none" ` +
           `stroke="currentColor" stroke-width="1.9">${ICONS[s.icon] || ICONS.box}` +
           `</svg><span>${esc(s.label)}</span></button>`;
  }

  function mount(selector) {
    S.root = document.querySelector(selector);
    if (!S.screens.length) S.screens = BUILTIN.map(s => Object.assign({}, s));

    S.root.innerHTML = `
      <div style="width:100%;height:100%;position:relative">
      <div class="app">
        <div class="app-topbar" data-drag>
          <div class="mark"></div>
          <div class="title">Life — A Deeper Simulation</div>
          <button class="app-menu" data-menu>${svg('menu', 2)}</button>
          <div class="win-controls">
            <button class="win-btn" data-win="min" aria-label="Minimize" title="Minimize">
              <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><line x1="2.5" y1="6" x2="9.5" y2="6"/></svg>
            </button>
            <button class="win-btn" data-win="max" aria-label="Maximize" title="Maximize">
              <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><rect x="2.5" y="2.5" width="7" height="7" rx="1"/></svg>
            </button>
            <button class="win-btn win-close" data-win="close" aria-label="Close" title="Close">
              <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><line x1="3" y1="3" x2="9" y2="9"/><line x1="9" y1="3" x2="3" y2="9"/></svg>
            </button>
          </div>
        </div>
        <div class="app-identity">
          <div class="flag"></div>
          <div class="who">
            <div class="nm">—</div>
            <div class="stage"><span class="txt">—</span>
              <span class="sep"></span><span class="loc">—</span></div>
          </div>
          <div class="bal"><div class="k">Bank Balance</div><div class="v">£0</div></div>
        </div>
        <div class="app-screens"></div>
        <div class="ui-toast">${svg('check', 2.4)}<span>Done</span></div>
        <div class="ui-overlay"></div>
        <div class="app-navwrap">
          <div class="app-nav"></div>
          <button class="age-btn" data-age>
            <svg class="hourglass" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              ${ICONS.hourglass}</svg>
            <span class="age-lbl">Age</span>
          </button>
        </div>
        <div class="app-statbar">
          ${['happiness','health','smarts','looks'].map(k => {
            const m = STAT_META[k];
            return `<div class="ui-stat" data-stat="${k}" style="--accent:${m.color}">` +
                   `<span class="ico">${svg(m.icon, 2)}</span>` +
                   `<span class="name">${m.label}</span>` +
                   `${meter(0, m.color)}<span class="num">0</span></div>`;
          }).join('')}
        </div>
      </div>
      </div>`;

    buildScreensAndNav();

    $('.app-nav').addEventListener('click', e => {
      const b = e.target.closest('button[data-screen]');
      if (b) showScreen(b.dataset.screen);
    });
    $('.age-btn').addEventListener('click', () => {
      $('.age-btn').classList.toggle('flip');
      fire('ageup');
    });
    $('.app-menu').addEventListener('click', () => fire('menu'));
    $('.app-screens').addEventListener('click', e => {
      const it = e.target.closest('.ui-item[data-action]');
      if (!it) return;
      const payload = JSON.parse(decodeURIComponent(it.dataset.payload || 'null'));
      fire('action', { action: it.dataset.action, payload });
    });
    $('.ui-overlay').addEventListener('click', e => {
      const ov = $('.ui-overlay');
      if (e.target === ov) {
        if (ov.dataset.dismissable) closeModal();
        return;
      }
      const closeX = e.target.closest('[data-modal-close]');
      if (closeX) { closeModal(); return; }
      const hit = e.target.closest('[data-action]');
      if (!hit) return;
      const action = hit.dataset.action;
      const payload = JSON.parse(decodeURIComponent(hit.dataset.payload || 'null'));
      const keepOpen = hit.dataset.keepopen === '1';
      if (action === '__close') { closeModal(); return; }
      if (!keepOpen) closeModal();
      fire('action', { action, payload });
    });

    return LifeUI;
  }

  return {
    mount, setIdentity, setStats, logEvent, clearLife,
    registerScreen, renderScreen, showScreen,
    modal, confirm, closeModal,
    scene, creationShow,
    on, toast,
    item, section, empty, pill, meter, button, icon: svg,
  };
})();

if (typeof module !== 'undefined') module.exports = LifeUI;
