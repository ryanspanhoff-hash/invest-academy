document.addEventListener('DOMContentLoaded', () => {
  initNavToggle();
  initFlashes();
  initTabs();
  initProgressBars();
  initTradeModal();
  initCompleteButtons();
  initChartModal();
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
  document.querySelectorAll('.tab-bar').forEach(initOneTabBar);
}

function initOneTabBar(tabBar) {
  const buttons = Array.from(tabBar.querySelectorAll('.tab-btn')).filter(b => b.dataset.tab);
  if (!buttons.length) return;
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
let openTradeModal = null;

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

  openTradeModal = (side, symbol, name, price, cash, owned) => {
    currentPrice = parseFloat(price);
    cash = parseFloat(cash || 0);
    owned = owned || '0';

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
  };

  document.querySelectorAll('[data-trade]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openTradeModal(btn.dataset.trade, btn.dataset.symbol, btn.dataset.name, btn.dataset.price, btn.dataset.cash, btn.dataset.owned);
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

/* ---------- Stock price chart modal ---------- */
function initChartModal() {
  const overlay = document.getElementById('chartModal');
  if (!overlay || typeof Chart === 'undefined') return;

  const titleEl = document.getElementById('chartTitle');
  const subtitleEl = document.getElementById('chartSubtitle');
  const sourceEl = document.getElementById('chartSource');
  const loadingEl = document.getElementById('chartLoading');
  const canvas = document.getElementById('priceChart');
  const buyBtn = document.getElementById('chartBuyBtn');
  const rangeButtons = overlay.querySelectorAll('[data-range]');

  let chart = null;
  let currentSymbol = null;
  let currentName = null;
  let currentPrice = 0;
  let currentRange = '1m';
  let requestToken = 0;

  async function loadRange(range) {
    currentRange = range;
    rangeButtons.forEach(b => b.classList.toggle('active', b.dataset.range === range));
    loadingEl.classList.remove('hidden');

    const token = ++requestToken;
    try {
      const res = await fetch(`/practice/api/history/${currentSymbol}?range=${range}`);
      const data = await res.json();
      if (token !== requestToken) return;
      if (!res.ok) throw new Error(data.error || 'Failed to load chart');
      renderChart(data);
    } catch (e) {
      if (token !== requestToken) return;
      sourceEl.textContent = 'Could not load chart data.';
    } finally {
      if (token === requestToken) loadingEl.classList.add('hidden');
    }
  }

  function renderChart(data) {
    const labels = data.points.map(p => formatLabel(p.t, data.range));
    const prices = data.points.map(p => p.price);
    const rising = prices.length > 1 && prices[prices.length - 1] >= prices[0];
    const lineColor = rising ? '#16a34a' : '#e0503a';

    if (chart) chart.destroy();
    chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: prices,
          borderColor: lineColor,
          backgroundColor: rising ? 'rgba(22,163,74,0.08)' : 'rgba(224,80,58,0.08)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.25,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: true, ticks: { maxTicksLimit: 6, autoSkip: true }, grid: { display: false } },
          y: { display: true, ticks: { callback: v => '$' + v }, grid: { color: '#eef1f5' } },
        },
        interaction: { intersect: false, mode: 'index' },
      },
    });

    sourceEl.textContent = data.live
      ? 'Real historical prices'
      : 'Simulated historical prices (live chart data unavailable for this stock)';
  }

  function formatLabel(t, range) {
    const d = new Date(t * 1000);
    if (range === '1d') return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    if (range === '1w') return d.toLocaleDateString([], { weekday: 'short', hour: 'numeric' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  document.querySelectorAll('[data-chart-row]').forEach(row => {
    row.addEventListener('click', (e) => {
      if (e.target.closest('.trade-btn')) return;
      currentSymbol = row.dataset.symbol;
      currentName = row.dataset.name;
      currentPrice = parseFloat(row.dataset.price);

      titleEl.textContent = currentSymbol;
      subtitleEl.textContent = `${currentName} • $${currentPrice.toFixed(2)} / share`;
      overlay.classList.add('open');
      loadRange('1m');
    });
  });

  rangeButtons.forEach(btn => {
    btn.addEventListener('click', () => loadRange(btn.dataset.range));
  });

  buyBtn.addEventListener('click', () => {
    overlay.classList.remove('open');
    if (openTradeModal) {
      const cashRow = document.querySelector('[data-trade="buy"][data-symbol="' + currentSymbol + '"]');
      const cash = cashRow ? cashRow.dataset.cash : 0;
      openTradeModal('buy', currentSymbol, currentName, currentPrice, cash, null);
    }
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
