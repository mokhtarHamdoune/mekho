/**
 * cart.js — CartPanel
 *
 * Pure DOM controller for the shopping cart sidebar.
 * Has zero knowledge of WebSocket or any other transport.
 * Receives plain objects from app.js and updates the DOM.
 *
 * Public API:
 *   const cart = new CartPanel();
 *   cart.addItem({ item: "apple", quantity: "2", status: "added" });
 *   cart.clear();
 */

'use strict';

class CartPanel {
  constructor() {
    /** @type {{ [name: string]: number }} accumulated quantities */
    this._items = {};

    this._panel  = document.getElementById('cart-panel');
    this._list   = document.getElementById('cart-list');
    this._badge  = document.getElementById('cart-badge');
    this._empty  = document.getElementById('cart-empty');
    this._total  = document.getElementById('cart-total');
  }

  // ── Public ─────────────────────────────────────────────────────────────────

  /**
   * Add or accumulate an item coming from a tool_result message.
   * @param {{ item: string, quantity: string, status: string }} result
   */
  addItem({ item, quantity }) {
    const q = parseFloat(quantity);
    if (!item || isNaN(q)) return;
    this._items[item] = (this._items[item] ?? 0) + q;
    this._render();
    this._flash();
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

  /** Orange glow pulse — forces reflow so re-triggering always works. */
  _flash() {
    this._panel.classList.remove('cart--flash');
    void this._panel.offsetWidth;   // force reflow
    this._panel.classList.add('cart--flash');
    setTimeout(() => this._panel.classList.remove('cart--flash'), 700);
  }
}
