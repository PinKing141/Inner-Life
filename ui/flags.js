/**
 * Country groupings used by the creation picker.
 *
 * The large inline FLAGS map was removed in favor of loading file-based
 * SVGs live under `ui/flags-svg/<continent>/<code>.svg`. Keep only the
 * country group metadata here; the UI will reference `flags-svg/<continent>/<code>.svg`.
 */
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
 
