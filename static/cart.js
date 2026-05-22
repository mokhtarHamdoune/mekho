/**
 * cart.js — CartPanel
 *
 * Pure DOM controller for the shopping cart sidebar.
 * Has zero knowledge of WebSocket or any other transport.
 * Receives the server's ground-truth cart snapshot from app.js and renders it.
 *
 * Public API:
 *   const cart = new CartPanel();
 *   cart.setCart({ "Apple": "2", "Banana": "1" });  // from tool result.cart
 *   cart.clear();
 */

'use strict';

class CartPanel {
  constructor() {
    /** @type {{ [name: string]: number }} mirror of server CartState */
    this._items = {};

    this._panel  = document.getElementById('cart-panel');
    this._list   = document.getElementById('cart-list');
    this._badge  = document.getElementById('cart-badge');
    this._empty  = document.getElementById('cart-empty');
    this._total  = document.getElementById('cart-total');
  }

  // ── Public ─────────────────────────────────────────────────────────────────

  /**
   * Replace the local cart with the server's authoritative snapshot.
   * Called after every tool result — both add and remove.
   * @param {{ [item: string]: string }} snapshot  e.g. { "Apple": "2" }
   * @param {'add'|'remove'} [action]  drives the flash colour
   */
  setCart(snapshot, action = 'add') {
    this._items = {};
    for (const [name, qty] of Object.entries(snapshot ?? {})) {
      const q = parseFloat(qty);
      if (name && !isNaN(q)) this._items[name] = q;
    }
    this._render();
    this._flash(action);
  }

  /** Remove all items and reset the panel to its empty state. */
  clear() {
    this._items = {};
    this._render();
  }

  // ── Private ────────────────────────────────────────────────────────────────

  _render() {
    this._list.innerHTML = '';

    const entries = Object.entries(this._items);
    const hasItems = entries.length > 0;

    this._empty.hidden = hasItems;
    this._total.hidden = !hasItems;

    let total = 0;
    for (const [name, qty] of entries) {
      total += qty;

      const li = document.createElement('li');
      li.className = 'cart__item';

      const nameSpan = document.createElement('span');
      nameSpan.className = 'cart__item-name';
      nameSpan.textContent = name;

      const qtySpan = document.createElement('span');
      qtySpan.className = 'cart__item-qty';
      qtySpan.textContent = `×${qty % 1 === 0 ? qty : qty.toFixed(2)}`;

      li.appendChild(nameSpan);
      li.appendChild(qtySpan);
      this._list.appendChild(li);
    }

    this._badge.textContent  = total % 1 === 0 ? total : total.toFixed(2);
    this._badge.hidden       = !hasItems;
    this._total.textContent  = `${entries.length} item${entries.length !== 1 ? 's' : ''}`;
  }

  /**
   * Glow pulse — orange for adds, blue for removes.
   * Forces reflow so re-triggering always works.
   * @param {'add'|'remove'} action
   */
  _flash(action) {
    const cls = action === 'remove' ? 'cart--flash-remove' : 'cart--flash';
    this._panel.classList.remove('cart--flash', 'cart--flash-remove');
    void this._panel.offsetWidth;   // force reflow
    this._panel.classList.add(cls);
    setTimeout(() => this._panel.classList.remove(cls), 700);
  }
}
