/**
 * Country catalogue + inline SVG flags.
 *
 * Flags are simplified vector renditions — stripes and primary symbols only.
 * No raster, no external CDN. Renders identically on every platform.
 *
 * Each flag is drawn in a 30x20 viewBox (3:2 aspect). The picker renders them
 * larger; CSS handles sizing. Use FLAGS[code] to fetch by ISO-3166 alpha-2.
 */

const FLAGS = (() => {
  const wrap = (inner) =>
    `<svg viewBox="0 0 30 20" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;

  // Horizontal tricolour (three equal stripes top->bottom)
  const hstripes3 = (a, b, c) =>
    wrap(`<rect width="30" height="6.67" fill="${a}"/><rect y="6.67" width="30" height="6.66" fill="${b}"/><rect y="13.33" width="30" height="6.67" fill="${c}"/>`);

  // Vertical tricolour
  const vstripes3 = (a, b, c) =>
    wrap(`<rect width="10" height="20" fill="${a}"/><rect x="10" width="10" height="20" fill="${b}"/><rect x="20" width="10" height="20" fill="${c}"/>`);

  return {
    // Europe
    GB: wrap(`
      <rect width="30" height="20" fill="#012169"/>
      <path d="M0,0 L30,20 M30,0 L0,20" stroke="#fff" stroke-width="3"/>
      <path d="M0,0 L30,20 M30,0 L0,20" stroke="#C8102E" stroke-width="1.5"/>
      <rect x="13" width="4" height="20" fill="#fff"/>
      <rect y="8" width="30" height="4" fill="#fff"/>
      <rect x="13.8" width="2.4" height="20" fill="#C8102E"/>
      <rect y="8.8" width="30" height="2.4" fill="#C8102E"/>`),
    IE: vstripes3("#169B62", "#FFFFFF", "#FF883E"),
    FR: vstripes3("#0055A4", "#FFFFFF", "#EF4135"),
    DE: hstripes3("#000", "#DD0000", "#FFCE00"),
    IT: vstripes3("#009246", "#FFFFFF", "#CE2B37"),
    ES: wrap(`<rect width="30" height="5" fill="#AA151B"/><rect y="5" width="30" height="10" fill="#F1BF00"/><rect y="15" width="30" height="5" fill="#AA151B"/>`),
    NL: hstripes3("#AE1C28", "#FFFFFF", "#21468B"),
    SE: wrap(`<rect width="30" height="20" fill="#006AA7"/><rect x="9" width="3" height="20" fill="#FECC00"/><rect y="8.5" width="30" height="3" fill="#FECC00"/>`),
    PL: wrap(`<rect width="30" height="10" fill="#FFFFFF"/><rect y="10" width="30" height="10" fill="#DC143C"/>`),
    RU: hstripes3("#FFFFFF", "#0039A6", "#D52B1E"),
    PT: wrap(`<rect width="30" height="20" fill="#FF0000"/><rect width="12" height="20" fill="#046A38"/><circle cx="12" cy="10" r="3" fill="#FFD700" stroke="#D52B1E" stroke-width="0.6"/>`),
    GR: wrap(`<rect width="30" height="20" fill="#fff"/>
      <rect y="2.2" width="30" height="2.2" fill="#0D5EAF"/>
      <rect y="6.6" width="30" height="2.2" fill="#0D5EAF"/>
      <rect y="11.0" width="30" height="2.2" fill="#0D5EAF"/>
      <rect y="15.4" width="30" height="2.2" fill="#0D5EAF"/>
      <rect width="11" height="11" fill="#0D5EAF"/>
      <rect x="4.4" width="2.2" height="11" fill="#fff"/>
      <rect y="4.4" width="11" height="2.2" fill="#fff"/>`),

    // North America
    US: wrap(`
      <rect width="30" height="20" fill="#B22234"/>
      <rect y="1.54" width="30" height="1.54" fill="#fff"/>
      <rect y="4.62" width="30" height="1.54" fill="#fff"/>
      <rect y="7.69" width="30" height="1.54" fill="#fff"/>
      <rect y="10.77" width="30" height="1.54" fill="#fff"/>
      <rect y="13.85" width="30" height="1.54" fill="#fff"/>
      <rect y="16.92" width="30" height="1.54" fill="#fff"/>
      <rect width="12" height="10.77" fill="#3C3B6E"/>`),
    CA: wrap(`<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#FF0000"/><rect x="22.5" width="7.5" height="20" fill="#FF0000"/><path d="M15 5 L16 8 L19 7.5 L17.5 10 L19.5 12 L16.5 11.5 L16 14 L15 12.5 L14 14 L13.5 11.5 L10.5 12 L12.5 10 L11 7.5 L14 8 Z" fill="#FF0000"/>`),
    MX: wrap(`<rect width="10" height="20" fill="#006847"/><rect x="10" width="10" height="20" fill="#fff"/><rect x="20" width="10" height="20" fill="#CE1126"/><circle cx="15" cy="10" r="2.6" fill="none" stroke="#8B5A2B" stroke-width="0.6"/>`),

    // South America
    BR: wrap(`<rect width="30" height="20" fill="#009B3A"/><polygon points="15,3 27,10 15,17 3,10" fill="#FFCC29"/><circle cx="15" cy="10" r="3.6" fill="#002776"/>`),
    AR: wrap(`<rect width="30" height="20" fill="#74ACDF"/><rect y="6.67" width="30" height="6.66" fill="#fff"/><circle cx="15" cy="10" r="1.6" fill="#F6B40E"/>`),
    CO: wrap(`<rect width="30" height="10" fill="#FCD116"/><rect y="10" width="30" height="5" fill="#003893"/><rect y="15" width="30" height="5" fill="#CE1126"/>`),
    CL: wrap(`<rect width="30" height="10" fill="#fff"/><rect y="10" width="30" height="10" fill="#D52B1E"/><rect width="10" height="10" fill="#0039A6"/><polygon points="5,3.2 5.7,5.2 7.8,5.2 6.1,6.4 6.8,8.5 5,7.3 3.2,8.5 3.9,6.4 2.2,5.2 4.3,5.2" fill="#fff"/>`),
    PE: vstripes3("#D91023", "#FFFFFF", "#D91023"),

    // Asia
    JP: wrap(`<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="6" fill="#BC002D"/>`),
    CN: wrap(`<rect width="30" height="20" fill="#DE2910"/><polygon points="6,3 7.2,5.6 10,5.6 7.8,7.4 8.6,10.2 6,8.6 3.4,10.2 4.2,7.4 2,5.6 4.8,5.6" fill="#FFDE00"/><circle cx="11.5" cy="2.5" r="0.7" fill="#FFDE00"/><circle cx="13" cy="4.5" r="0.7" fill="#FFDE00"/><circle cx="13" cy="7" r="0.7" fill="#FFDE00"/><circle cx="11.5" cy="9" r="0.7" fill="#FFDE00"/>`),
    KR: wrap(`<rect width="30" height="20" fill="#fff"/>
      <path d="M15,5 a5,5 0 0,1 0,10 a2.5,2.5 0 0,0 0,-5 a2.5,2.5 0 0,1 0,-5 Z" fill="#C60C30"/>
      <path d="M15,5 a5,5 0 0,0 0,10 a2.5,2.5 0 0,1 0,-5 a2.5,2.5 0 0,0 0,-5 Z" fill="#003478"/>`),
    IN: wrap(`<rect width="30" height="6.67" fill="#FF9933"/><rect y="6.67" width="30" height="6.66" fill="#fff"/><rect y="13.33" width="30" height="6.67" fill="#138808"/><circle cx="15" cy="10" r="1.6" fill="none" stroke="#000080" stroke-width="0.5"/>`),
    ID: wrap(`<rect width="30" height="10" fill="#FF0000"/><rect y="10" width="30" height="10" fill="#fff"/>`),
    SA: wrap(`<rect width="30" height="20" fill="#006C35"/><rect x="4" y="13" width="22" height="0.8" fill="#fff"/><rect x="5" y="6" width="20" height="4" fill="none" stroke="#fff" stroke-width="0.6"/>`),
    TH: wrap(`<rect width="30" height="20" fill="#A51931"/><rect y="3.33" width="30" height="13.33" fill="#F4F5F8"/><rect y="6.67" width="30" height="6.67" fill="#2D2A4A"/>`),
    PH: wrap(`<rect width="30" height="20" fill="#0038A8"/><rect y="10" width="30" height="10" fill="#CE1126"/><polygon points="0,0 13,10 0,20" fill="#fff"/><polygon points="3,8.5 3.5,9.7 4.7,9.7 3.8,10.5 4.1,11.7 3,11 1.9,11.7 2.2,10.5 1.3,9.7 2.5,9.7" fill="#FCD116"/>`),

    // Africa
    NG: vstripes3("#008753", "#FFFFFF", "#008753"),
    ZA: wrap(`<rect width="30" height="20" fill="#fff"/>
      <rect width="30" height="6.67" fill="#DE3831"/>
      <rect y="13.33" width="30" height="6.67" fill="#002395"/>
      <polygon points="0,0 13,10 0,20" fill="#000"/>
      <polygon points="0,2 11,10 0,18" fill="#FFB612"/>
      <polygon points="0,4 9,10 0,16" fill="#007A4D"/>`),
    EG: wrap(`<rect width="30" height="6.67" fill="#CE1126"/><rect y="6.67" width="30" height="6.66" fill="#fff"/><rect y="13.33" width="30" height="6.67" fill="#000"/><circle cx="15" cy="10" r="1.4" fill="#C09300"/>`),
    KE: wrap(`<rect width="30" height="5" fill="#000"/><rect y="5" width="30" height="2" fill="#fff"/><rect y="7" width="30" height="6" fill="#BB0000"/><rect y="13" width="30" height="2" fill="#fff"/><rect y="15" width="30" height="5" fill="#006600"/><ellipse cx="15" cy="10" rx="2" ry="3.5" fill="#BB0000" stroke="#fff" stroke-width="0.5"/>`),
    MA: wrap(`<rect width="30" height="20" fill="#C1272D"/><polygon points="15,7 16,10 19,10 16.5,12 17.5,15 15,13.2 12.5,15 13.5,12 11,10 14,10" fill="none" stroke="#006233" stroke-width="0.6"/>`),
    GH: wrap(`<rect width="30" height="6.67" fill="#CE1126"/><rect y="6.67" width="30" height="6.66" fill="#FCD116"/><rect y="13.33" width="30" height="6.67" fill="#006B3F"/><polygon points="15,8.5 15.8,10.5 17.9,10.5 16.2,11.7 16.8,13.7 15,12.5 13.2,13.7 13.8,11.7 12.1,10.5 14.2,10.5" fill="#000"/>`),
    ET: hstripes3("#078930", "#FCDD09", "#DA121A"),

    // Oceania
    AU: wrap(`<rect width="30" height="20" fill="#012169"/>
      <rect width="15" height="10" fill="#012169"/>
      <path d="M0,0 L15,10 M15,0 L0,10" stroke="#fff" stroke-width="1.5"/>
      <path d="M0,0 L15,10 M15,0 L0,10" stroke="#C8102E" stroke-width="0.8"/>
      <rect x="6.5" width="2" height="10" fill="#fff"/>
      <rect y="4" width="15" height="2" fill="#fff"/>
      <rect x="6.9" width="1.2" height="10" fill="#C8102E"/>
      <rect y="4.4" width="15" height="1.2" fill="#C8102E"/>
      <circle cx="23" cy="6" r="0.7" fill="#fff"/>
      <circle cx="20" cy="13" r="0.7" fill="#fff"/>
      <circle cx="26" cy="13" r="0.7" fill="#fff"/>
      <circle cx="23" cy="17" r="0.7" fill="#fff"/>
      <circle cx="27.5" cy="9.5" r="0.6" fill="#fff"/>`),
    NZ: wrap(`<rect width="30" height="20" fill="#012169"/>
      <rect width="15" height="10" fill="#012169"/>
      <path d="M0,0 L15,10 M15,0 L0,10" stroke="#fff" stroke-width="1.5"/>
      <path d="M0,0 L15,10 M15,0 L0,10" stroke="#C8102E" stroke-width="0.8"/>
      <rect x="6.5" width="2" height="10" fill="#fff"/>
      <rect y="4" width="15" height="2" fill="#fff"/>
      <rect x="6.9" width="1.2" height="10" fill="#C8102E"/>
      <rect y="4.4" width="15" height="1.2" fill="#C8102E"/>
      <circle cx="22" cy="6" r="0.8" fill="#CC142B"/>
      <circle cx="26" cy="10" r="0.8" fill="#CC142B"/>
      <circle cx="22" cy="14" r="0.8" fill="#CC142B"/>
      <circle cx="19" cy="11" r="0.8" fill="#CC142B"/>`),
  };
})();

// Continent groupings used by the creation picker.
const COUNTRIES_BY_CONTINENT = [
  { name: "Europe", countries: [
    { code: "GB", name: "United Kingdom" },
    { code: "IE", name: "Ireland" },
    { code: "FR", name: "France" },
    { code: "DE", name: "Germany" },
    { code: "IT", name: "Italy" },
    { code: "ES", name: "Spain" },
    { code: "PT", name: "Portugal" },
    { code: "NL", name: "Netherlands" },
    { code: "SE", name: "Sweden" },
    { code: "PL", name: "Poland" },
    { code: "GR", name: "Greece" },
    { code: "RU", name: "Russia" },
  ]},
  { name: "North America", countries: [
    { code: "US", name: "United States" },
    { code: "CA", name: "Canada" },
    { code: "MX", name: "Mexico" },
  ]},
  { name: "South America", countries: [
    { code: "BR", name: "Brazil" },
    { code: "AR", name: "Argentina" },
    { code: "CO", name: "Colombia" },
    { code: "CL", name: "Chile" },
    { code: "PE", name: "Peru" },
  ]},
  { name: "Asia", countries: [
    { code: "JP", name: "Japan" },
    { code: "CN", name: "China" },
    { code: "KR", name: "South Korea" },
    { code: "IN", name: "India" },
    { code: "ID", name: "Indonesia" },
    { code: "TH", name: "Thailand" },
    { code: "PH", name: "Philippines" },
    { code: "SA", name: "Saudi Arabia" },
  ]},
  { name: "Africa", countries: [
    { code: "NG", name: "Nigeria" },
    { code: "ZA", name: "South Africa" },
    { code: "EG", name: "Egypt" },
    { code: "KE", name: "Kenya" },
    { code: "MA", name: "Morocco" },
    { code: "GH", name: "Ghana" },
    { code: "ET", name: "Ethiopia" },
  ]},
  { name: "Oceania", countries: [
    { code: "AU", name: "Australia" },
    { code: "NZ", name: "New Zealand" },
  ]},
];
