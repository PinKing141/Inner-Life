const FLAGS = {};

function flagSvgPath(code) {
  if (typeof FLAG_ASSET_MAP === "undefined") return "";
  const meta = FLAG_ASSET_MAP[code];
  return meta ? meta.path : "";
}

function flagSvgImg(code, name = "") {
  const path = flagSvgPath(code);
  if (!path) return "";
  const label = (name || code) + " flag";
  return `<img src="${path}" alt="${label}" class="flag-svg" loading="lazy" decoding="async"/>`;
}
