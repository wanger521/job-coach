// Native pickers handle all interaction themselves.
if (!window.CSS || !CSS.supports('(appearance: base-select) and selector(::picker(select))')) {
  installFallback();
}

function isTrigger(node) {
  return node instanceof HTMLSelectElement && !node.multiple && node.size <= 1 && !node.matches(':disabled');
}

function nameList(menu, select) {
  if (select.hasAttribute('aria-labelledby')) {
    menu.setAttribute('aria-labelledby', select.getAttribute('aria-labelledby'));
    return;
  }
  const labels = Array.from(select.labels || [], label => {
    const copy = label.cloneNode(true);
    copy.querySelectorAll('select, [aria-hidden="true"]').forEach(node => node.remove());
    return copy.textContent.trim();
  });
  menu.setAttribute('aria-label', select.getAttribute('aria-label') || labels.join(' ') || select.title || '选项');
}

function place(menu, select) {
  const rect = select.getBoundingClientRect();
  const view = window.visualViewport;
  const left = (view?.offsetLeft || 0) + 4, top = (view?.offsetTop || 0) + 4;
  const width = Math.max(0, (view?.width || document.documentElement.clientWidth) - 8);
  const bottom = top + (view?.height || document.documentElement.clientHeight) - 8;
  const above = Math.max(0, rect.top - 4 - top), below = Math.max(0, bottom - rect.bottom - 4);
  const menuWidth = Math.min(width, Math.max(196, rect.width));
  menu.style.width = `${menuWidth}px`;
  menu.style.maxHeight = '22rem';
  const up = menu.offsetHeight > below && above > below;
  menu.style.maxHeight = `${Math.min(menu.offsetHeight, up ? above : below)}px`;
  const start = menu.dir === 'rtl' ? rect.right - menuWidth : rect.left;
  menu.style.left = `${Math.max(left, Math.min(start, left + width - menuWidth))}px`;
  menu.style.top = `${up ? rect.top - 4 - menu.offsetHeight : rect.bottom + 4}px`;
}

function installFallback() {
  let active, sequence = 0;
  const openingKeys = ['Enter', ' ', 'ArrowDown', 'ArrowUp', 'F4'];
  // Intercept the native mouse picker. The subsequent click also covers touch,
  // associated labels and assistive activation. The select stays in the tab order.
  document.addEventListener('mousedown', event => {
    if (event.button !== 0) return;
    if (active && !active.menu.contains(event.target) && event.target !== active.select) active.close(true);
    if (isTrigger(event.target)) event.preventDefault();
  }, true);
  document.addEventListener('click', event => {
    if (event.defaultPrevented || !isTrigger(event.target)) return;
    event.preventDefault();
    if (active?.select === event.target) active.close(true);
    else open(event.target);
  });
  document.addEventListener('keydown', event => {
    if (event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey || !isTrigger(event.target)) return;
    if (!openingKeys.includes(event.key)) return;
    event.preventDefault();
    open(event.target);
  });

  function open(select) {
    active?.close(false);
    const dialog = select.closest('dialog[open]');
    const menu = document.createElement('div');
    menu.className = 'atlas-select-menu';
    menu.setAttribute('role', 'listbox');
    menu.tabIndex = -1;
    menu.id = `atlas-select-menu-${++sequence}`;
    nameList(menu, select);
    const style = getComputedStyle(select);
    menu.style.font = style.font;
    menu.dir = style.direction;

    const choices = new Map(); // Row -> original option, including duplicate values.
    let group, parent = menu;
    for (const option of select.options) {
      const owner = option.closest('optgroup');
      if (option.hidden || owner?.hidden) continue;
      if (group !== owner) {
        group = owner;
        parent = menu;
        if (group) {
          parent = menu.appendChild(document.createElement('div'));
          parent.setAttribute('role', 'group');
          parent.setAttribute('aria-label', group.label);
          const heading = parent.appendChild(document.createElement('div'));
          heading.className = 'atlas-select-group-label';
          heading.setAttribute('aria-hidden', 'true');
          heading.textContent = group.label;
        }
      }
      const row = parent.appendChild(document.createElement('div'));
      row.setAttribute('role', 'option');
      row.setAttribute('aria-selected', String(option.selected));
      row.textContent = option.label;
      if (option.matches(':disabled')) row.setAttribute('aria-disabled', 'true');
      else {
        row.tabIndex = -1;
        choices.set(row, option);
      }
    }
    const rows = [...choices.keys()];
    if (menu.showPopover) menu.setAttribute('popover', 'manual');
    (dialog || document.body).append(menu);
    menu.showPopover?.();
    place(menu, select);
    const previous = ['aria-controls', 'aria-expanded'].map(name => [name, select.getAttribute(name)]);
    select.setAttribute('aria-controls', menu.id);
    select.setAttribute('aria-expanded', 'true');

    function focus(row) {
      (row || menu).focus({ preventScroll: true });
      if (!row) return;
      const box = menu.getBoundingClientRect(), item = row.getBoundingClientRect();
      if (item.top < box.top + 5) menu.scrollTop += item.top - box.top - 5;
      else if (item.bottom > box.bottom - 5) menu.scrollTop += item.bottom - box.bottom + 5;
    }
    const cleanup = [];
    function listen(target, type, handler, capture = false) {
      target?.addEventListener(type, handler, capture);
      cleanup.push(() => target?.removeEventListener(type, handler, capture));
    }
    function close(restore) {
      if (active?.menu !== menu) return;
      active = null;
      cleanup.forEach(remove => remove());
      observer.disconnect();
      menu.remove();
      for (const [name, value] of previous) {
        if (value === null) select.removeAttribute(name);
        else select.setAttribute(name, value);
      }
      if (restore && select.isConnected && (!dialog || dialog.open)) select.focus({ preventScroll: true });
    }
    function commit(row) {
      const option = choices.get(row);
      const changed = option && option.closest('select') === select && isTrigger(select) &&
        !option.matches(':disabled') && option.index !== select.selectedIndex;
      if (changed) select.selectedIndex = option.index;
      close(true); // change handlers may synchronously replace this select or dialog.
      if (changed) {
        select.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
        select.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    // Observe only while expanded. A rerender or option edit invalidates this snapshot.
    const observer = new MutationObserver(records => {
      if (!select.isConnected || !isTrigger(select) || (dialog && !dialog.open) || !select.getClientRects().length ||
          records.some(record => select.contains(record.target))) close(true);
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true,
      attributeFilter: ['open', 'hidden', 'disabled', 'multiple', 'size', 'selected', 'label', 'value'] });
    active = { menu, select, close };
    listen(document, 'scroll', event => { if (!menu.contains(event.target)) close(true); }, true);
    listen(window, 'resize', () => place(menu, select));
    listen(window.visualViewport, 'resize', () => place(menu, select));
    listen(window.visualViewport, 'scroll', () => place(menu, select));
    listen(window, 'blur', () => close(false));
    listen(select.form, 'reset', () => close(true));
    listen(dialog, 'cancel', event => { event.preventDefault(); close(true); });
    menu.onfocusout = event => { if (!menu.contains(event.relatedTarget)) close(false); };
    menu.onmousedown = event => { if (event.target.closest('[role="option"]')) event.preventDefault(); };
    menu.onclick = event => {
      const row = event.target.closest('[role="option"]');
      if (choices.has(row)) commit(row);
    };
    let prefix = '', lastKey = 0;
    menu.onkeydown = event => {
      const { key } = event, index = rows.indexOf(document.activeElement);
      if (event.isComposing || event.ctrlKey || event.metaKey) return;
      if (key === 'Tab') { commit(rows[index]); return; } // Let Tab proceed from the original field.
      if (key === 'Escape') close(true);
      else if (key === 'Enter' || key === ' ' || key === 'F4' || (event.altKey && key === 'ArrowUp')) commit(rows[index]);
      else if (key === 'Home') focus(rows[0]);
      else if (key === 'End') focus(rows[rows.length - 1]);
      else if (key === 'ArrowDown') focus(rows[Math.min(rows.length - 1, index + 1)]);
      else if (key === 'ArrowUp') focus(rows[Math.max(0, index - 1)]);
      else if (key.length === 1 && !event.altKey) {
        const letter = key.toLocaleLowerCase();
        prefix = Date.now() - lastKey > 700 || prefix === letter ? letter : prefix + letter;
        lastKey = Date.now();
        const start = index + (prefix.length === 1 ? 1 : 0);
        const match = rows.slice(start).concat(rows.slice(0, start)).find(row =>
          row.textContent.trim().toLocaleLowerCase().startsWith(prefix));
        if (match) focus(match);
      } else return;
      event.preventDefault();
      event.stopPropagation(); // The first Escape belongs to the list, even in a modal.
    };
    focus(rows.find(row => choices.get(row).selected) || rows[0]);
  }
}
