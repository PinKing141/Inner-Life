/**
 * App.screens.assets — render the Assets tab + property purchase picker.
 *
 * Layout: Property / Renting (if any) / Housing Market / Vehicles /
 * Vehicle Market. Tapping a Housing Market listing opens an option
 * sub-modal (openListingOptions) with Buy / Mortgage / Rent.
 */
(function (App) {
  "use strict";

  App.renderAssets = function () {
    const s = this.state;
    const props = s.properties || [];
    const market = s.housing_market || [];
    const rental = s.rental;
    const groups = [];

    groups.push({
      label: "Property",
      emptyText: "You own no property.",
      items: props.map(p => ({
        icon: "house", accent: "var(--gold)",
        title: p.name,
        subtitle: p.mortgage_balance
          ? `Value £${(p.value || 0).toLocaleString()} · Mortgage £${p.mortgage_balance.toLocaleString()}`
          : `Value £${(p.value || 0).toLocaleString()}`,
        trailing: { kind: "value", text: "£" + (p.value || 0).toLocaleString() },
        action: "sell-home", payload: p.id,
      })),
    });

    if (rental) {
      groups.push({
        label: "Renting",
        items: [{
          icon: "house", accent: "var(--cat-money)",
          title: rental.name,
          subtitle: `Rent £${(rental.rent || 0).toLocaleString()}/yr`,
          trailing: { kind: "chevron" },
          action: "stop-renting",
        }],
      });
    }

    groups.push({
      label: "Housing Market",
      emptyText: "No listings in your city right now.",
      items: market.map(m => ({
        icon: "house", accent: "var(--cat-money)",
        title: m.name,
        subtitle: `Buy £${(m.price || 0).toLocaleString()} · Rent £${(m.rent || 0).toLocaleString()}/yr`,
        trailing: { kind: "chevron" },
        action: "view-listing", payload: m.id,
      })),
    });

    // Cars/Assets v1 — owned vehicles + dealership listings.
    const vehicles = s.vehicles || [];
    const carMarket = s.car_market || [];

    groups.push({
      label: "Vehicles",
      emptyText: "No cars yet.",
      items: vehicles.map(v => ({
        icon: "car", accent: "var(--gold)",
        title: `${v.brand} ${v.model}`,
        subtitle: `Owned ${v.age_years || 0}y · Bought £${(v.purchase_price || 0).toLocaleString()}`,
        trailing: { kind: "value", text: "£" + (v.current_value || 0).toLocaleString() },
        action: "sell-car", payload: v.instance_id,
      })),
    });

    groups.push({
      label: "Vehicle Market",
      emptyText: "No vehicles available.",
      items: carMarket.map(c => ({
        icon: "car",
        accent: c.available ? "var(--cat-money)" : "var(--ink-faint)",
        title: `${c.brand} ${c.model}`,
        subtitle: `${c.blurb}  ·  Top ${c.top_speed} · Prestige ${c.prestige}`,
        locked: !c.available,
        action: c.available ? "buy-car" : null,
        payload: c.id,
        trailing: c.available
          ? { kind: "value", text: "£" + (c.price || 0).toLocaleString() }
          : { kind: "badge", text: c.lock_reason || "Locked", icon: "lock" },
      })),
    });

    LifeUI.renderScreen("assets", groups);
  };

  App.openListingOptions = function (listingId) {
    const m = (this.state.housing_market || []).find(x => x.id === listingId);
    if (!m) return;
    LifeUI.modal({
      kind: "picker", title: m.name, dismissable: true,
      blocks: [
        { type: "text", text:
          `Price £${(m.price || 0).toLocaleString()} · Annual rent £${(m.rent || 0).toLocaleString()}` },
        { type: "list", items: [
          { icon: "gem", accent: "var(--gold)", title: "Buy Outright",
            subtitle: `£${(m.price || 0).toLocaleString()} now`,
            trailing: { kind: "chevron" }, action: "buy-listing", payload: listingId },
          { icon: "house", accent: "var(--cat-money)", title: "Buy with Mortgage",
            subtitle: "10% deposit, 25-year term",
            trailing: { kind: "chevron" }, action: "mortgage-listing", payload: listingId },
          { icon: "house", accent: "var(--c-smarts)", title: "Rent",
            subtitle: `£${(m.rent || 0).toLocaleString()}/yr`,
            trailing: { kind: "chevron" }, action: "rent-listing", payload: listingId },
        ] },
      ],
      actions: [{ label: "Close", variant: "ghost", action: "__close" }],
    });
  };
})(window.App = window.App || {});
