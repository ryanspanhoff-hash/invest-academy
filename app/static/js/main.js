document.addEventListener('DOMContentLoaded', () => {
  initNavToggle();
  initFlashes();
  initTabs();
  initProgressBars();
  initTradeModal();
  initCompleteButtons();
});

/* ---------- Mobile nav ---------- */
function initNavToggle() {
  const toggle = document.getElementById('navToggle');
  const nav = document.getElementById('siteNav');
  if (!toggle || !nav) return;
  toggle.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open);
  });
  nav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
    nav.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  }));
}

/* ---------- Flash messages ---------- */
function initFlashes() {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(flash => {
    const close = flash.querySelector('.flash-close');
    if (close) close.addEventListener('click', () => dismissFlash(flash));
    if (flash.dataset.category !== 'levelup') {
      setTimeout(() => dismissFlash(flash), 5500);
    } else {
      launchConfetti();
      setTimeout(() => dismissFlash(flash), 7000);
    }
  });
}

function dismissFlash(flash) {
  if (!flash || !flash.isConnected) return;
  flash.classList.add('flash-hide');
  setTimeout(() => flash.remove(), 220);
}

/* ---------- Tabs (learning page) ---------- */
function initTabs() {
  const tabBar = document.querySelector('.tab-bar');
  if (!tabBar) return;
  const buttons = tabBar.querySelectorAll('.tab-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById(btn.dataset.tab);
      if (panel) panel.classList.add('active');
      if (history.replaceState) {
        history.replaceState(null, '', '#' + btn.dataset.tab);
      }
    });
  });

  const hash = window.location.hash.replace('#', '');
  if (hash) {
    const match = tabBar.querySelector(`[data-tab="${hash}"]`);
    if (match) match.click();
  }
}

/* ---------- Progress bar fill animation ---------- */
function initProgressBars() {
  document.querySelectorAll('.progress-fill').forEach(bar => {
    const target = bar.dataset.pct || 0;
    requestAnimationFrame(() => {
      setTimeout(() => { bar.style.width = target + '%'; }, 150);
    });
  });
}

/* ---------- Buy / Sell modal ---------- */
function initTradeModal() {
  const overlay = document.getElementById('tradeModal');
  if (!overlay) return;

  const form = document.getElementById('tradeForm');
  const symbolField = document.getElementById('tradeSymbol');
  const sideField = document.getElementById('tradeSide');
  const qtyInput = document.getElementById('tradeQty');
  const titleEl = document.getElementById('tradeTitle');
  const priceEl = document.getElementById('tradePrice');
  const estEl = document.getElementById('tradeEstimate');
  const submitBtn = document.getElementById('tradeSubmit');
  const maxHint = document.getElementById('tradeMaxHint');

  let currentPrice = 0;

  document.querySelectorAll('[data-trade]').forEach(btn => {
    btn.addEventListener('click', () => {
      const side = btn.dataset.trade;
      const symbol = btn.dataset.symbol;
      const name = btn.dataset.name;
      currentPrice = parseFloat(btn.dataset.price);
      const owned = btn.dataset.owned || '0';
      const cash = parseFloat(btn.dataset.cash || '0');

      symbolField.value = symbol;
      sideField.value = side;
      qtyInput.value = 1;
      form.action = side === 'buy' ? form.dataset.buyUrl : form.dataset.sellUrl;

      titleEl.textContent = `${side === 'buy' ? 'Buy' : 'Sell'} ${symbol}`;
      priceEl.textContent = `${name} • $${currentPrice.toFixed(2)} / share`;
      submitBtn.textContent = side === 'buy' ? 'Confirm Buy' : 'Confirm Sell';
      submitBtn.className = 'btn btn-block ' + (side === 'buy' ? 'btn-primary' : 'btn-danger');

      maxHint.textContent = side === 'buy'
        ? `Cash available: $${cash.toFixed(2)}`
        : `You own: ${owned} shares`;

      updateEstimate();
      overlay.classList.add('open');
    });
  });

  function updateEstimate() {
    const qty = parseFloat(qtyInput.value) || 0;
    estEl.textContent = `Estimated total: $${(qty * currentPrice).toFixed(2)}`;
  }
  qtyInput.addEventListener('input', updateEstimate);

  document.querySelectorAll('.qty-buttons button').forEach(btn => {
    btn.addEventListener('click', () => {
      const delta = parseInt(btn.dataset.delta, 10);
      let val = parseFloat(qtyInput.value) || 0;
      val = Math.max(1, val + delta);
      qtyInput.value = val;
      updateEstimate();
    });
  });

  function closeModal() { overlay.classList.remove('open'); }
  overlay.querySelector('.modal-close').addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
}

/* ---------- Learning: mark complete ---------- */
function initCompleteButtons() {
  document.querySelectorAll('[data-complete-id]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const itemId = btn.dataset.completeId;
      btn.disabled = true;
      try {
        const res = await fetch(`/learning/complete/${itemId}`, { method: 'POST' });
        if (res.ok) {
          btn.outerHTML = '<span class="complete-check">✓ Completed</span>';
          bumpLearningProgress();
        } else {
          btn.disabled = false;
        }
      } catch (e) {
        btn.disabled = false;
      }
    });
  });
}

function bumpLearningProgress() {
  const bar = document.getElementById('learningProgressFill');
  const label = document.getElementById('learningProgressLabel');
  if (!bar || !label) return;
  const done = parseInt(bar.dataset.done, 10) + 1;
  const total = parseInt(bar.dataset.total, 10);
  bar.dataset.done = done;
  const pct = total ? Math.round((done / total) * 100) : 0;
  bar.style.width = pct + '%';
  label.textContent = `${done} / ${total} completed`;
}

/* ---------- Confetti ---------- */
function launchConfetti() {
  const layer = document.getElementById('confettiLayer');
  if (!layer) return;
  const colors = ['#16a34a', '#f5b700', '#2563eb', '#e0503a', '#22c55e'];
  for (let i = 0; i < 60; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    piece.style.left = Math.random() * 100 + 'vw';
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.animationDuration = (2.2 + Math.random() * 1.6) + 's';
    piece.style.animationDelay = (Math.random() * 0.4) + 's';
    layer.appendChild(piece);
    setTimeout(() => piece.remove(), 4200);
  }
}
