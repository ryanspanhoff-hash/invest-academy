function whenDomReady(fn) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn);
  } else {
    fn();
  }
}

whenDomReady(() => {
  initNavToggle();
  initFlashes();
  initTabs();
  initProgressBars();
  initTradeModal();
  initCompleteButtons();
  initChartModal();
  initSymbolSearch();
  initLevelUpCelebration();
});

function formatPrice(price) {
  return price < 1 ? price.toFixed(6) : price.toFixed(2);
}

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
    setTimeout(() => dismissFlash(flash), 5500);
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
  const qtyLabel = document.getElementById('tradeQtyLabel');
  const qtyButtons = document.getElementById('qtyButtons');
  const titleEl = document.getElementById('tradeTitle');
  const priceEl = document.getElementById('tradePrice');
  const estEl = document.getElementById('tradeEstimate');
  const submitBtn = document.getElementById('tradeSubmit');
  const maxHint = document.getElementById('tradeMaxHint');

  let currentPrice = 0;
  let currentIsCrypto = false;

  const STOCK_DELTAS = [-5, -1, 1, 5];
  const CRYPTO_DOLLAR_DELTAS = [-50, -10, 10, 50];

  openTradeModal = (side, symbol, name, price, cash, owned, isCrypto) => {
    currentPrice = parseFloat(price);
    currentIsCrypto = !!isCrypto;
    cash = parseFloat(cash || 0);
    owned = owned || '0';
    const unit = currentIsCrypto ? 'units' : 'shares';

    symbolField.value = symbol;
    sideField.value = side;
    form.action = side === 'buy' ? form.dataset.buyUrl : form.dataset.sellUrl;

    if (currentIsCrypto) {
      qtyInput.step = 'any';
      qtyInput.min = '0.000001';
      qtyInput.value = currentPrice > 0 ? Math.max(0.000001, Math.round((50 / currentPrice) * 1e6) / 1e6) : 1;
      qtyLabel.textContent = 'Quantity (units)';
    } else {
      qtyInput.step = '1';
      qtyInput.min = '1';
      qtyInput.value = 1;
      qtyLabel.textContent = 'Quantity (shares)';
    }

    titleEl.textContent = `${side === 'buy' ? 'Buy' : 'Sell'} ${symbol}`;
    priceEl.textContent = `${name} • $${formatPrice(currentPrice)} / ${currentIsCrypto ? 'unit' : 'share'}`;
    submitBtn.textContent = side === 'buy' ? 'Confirm Buy' : 'Confirm Sell';
    submitBtn.className = 'btn btn-block ' + (side === 'buy' ? 'btn-primary' : 'btn-danger');

    maxHint.textContent = side === 'buy'
      ? `Cash available: $${cash.toFixed(2)}`
      : `You own: ${owned} ${unit}`;

    renderQtyButtons();
    updateEstimate();
    overlay.classList.add('open');
  };

  function renderQtyButtons() {
    qtyButtons.innerHTML = '';
    if (currentIsCrypto) {
      CRYPTO_DOLLAR_DELTAS.forEach(dollars => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = (dollars > 0 ? '+$' : '-$') + Math.abs(dollars);
        btn.addEventListener('click', () => {
          const deltaQty = currentPrice > 0 ? dollars / currentPrice : 0;
          let val = parseFloat(qtyInput.value) || 0;
          val = Math.max(0.000001, val + deltaQty);
          qtyInput.value = Math.round(val * 1e6) / 1e6;
          updateEstimate();
        });
        qtyButtons.appendChild(btn);
      });
    } else {
      STOCK_DELTAS.forEach(delta => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = (delta > 0 ? '+' : '') + delta;
        btn.addEventListener('click', () => {
          let val = parseFloat(qtyInput.value) || 0;
          val = Math.max(1, val + delta);
          qtyInput.value = val;
          updateEstimate();
        });
        qtyButtons.appendChild(btn);
      });
    }
  }

  document.querySelectorAll('[data-trade]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openTradeModal(btn.dataset.trade, btn.dataset.symbol, btn.dataset.name, btn.dataset.price, btn.dataset.cash, btn.dataset.owned, btn.dataset.crypto === 'true');
    });
  });

  function updateEstimate() {
    const qty = parseFloat(qtyInput.value) || 0;
    estEl.textContent = `Estimated total: $${(qty * currentPrice).toFixed(2)}`;
  }
  qtyInput.addEventListener('input', updateEstimate);

  function closeModal() { overlay.classList.remove('open'); }
  overlay.querySelector('.modal-close').addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
}

/* ---------- Stock price chart modal ---------- */
let openChartModal = null;

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
  let currentIsCrypto = false;
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
          y: { display: true, ticks: { callback: v => '$' + formatPrice(v) }, grid: { color: '#eef1f5' } },
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

  openChartModal = (symbol, name, price, isCrypto) => {
    currentSymbol = symbol;
    currentName = name;
    currentPrice = parseFloat(price);
    currentIsCrypto = !!isCrypto;

    titleEl.textContent = currentSymbol;
    subtitleEl.textContent = `${currentName} • $${formatPrice(currentPrice)} / ${currentIsCrypto ? 'unit' : 'share'}`;
    buyBtn.textContent = currentIsCrypto ? 'Buy this crypto' : 'Buy this stock';
    overlay.classList.add('open');
    loadRange('1m');
  };

  document.querySelectorAll('[data-chart-row]').forEach(row => {
    row.addEventListener('click', (e) => {
      if (e.target.closest('.trade-btn')) return;
      openChartModal(row.dataset.symbol, row.dataset.name, row.dataset.price, row.dataset.crypto === 'true');
    });
  });

  rangeButtons.forEach(btn => {
    btn.addEventListener('click', () => loadRange(btn.dataset.range));
  });

  buyBtn.addEventListener('click', () => {
    overlay.classList.remove('open');
    if (openTradeModal) {
      openTradeModal('buy', currentSymbol, currentName, currentPrice, window.PORTFOLIO_CASH || 0, null, currentIsCrypto);
    }
  });

  function closeModal() { overlay.classList.remove('open'); }
  overlay.querySelector('.modal-close').addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
}

/* ---------- Symbol search (stocks + crypto) ---------- */
function initSymbolSearch() {
  const input = document.getElementById('symbolSearch');
  const resultsBox = document.getElementById('searchResults');
  if (!input || !resultsBox) return;

  let debounceTimer = null;
  let requestToken = 0;

  input.addEventListener('input', () => {
    const query = input.value.trim();
    clearTimeout(debounceTimer);
    if (!query) {
      resultsBox.classList.remove('open');
      resultsBox.innerHTML = '';
      return;
    }
    debounceTimer = setTimeout(() => runSearch(query), 300);
  });

  input.addEventListener('focus', () => {
    if (resultsBox.innerHTML) resultsBox.classList.add('open');
  });

  document.addEventListener('click', (e) => {
    if (!resultsBox.contains(e.target) && e.target !== input) {
      resultsBox.classList.remove('open');
    }
  });

  async function runSearch(query) {
    const token = ++requestToken;
    try {
      const res = await fetch(`/practice/api/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      if (token !== requestToken) return;
      renderResults(data.results || []);
    } catch (e) {
      if (token !== requestToken) return;
      resultsBox.innerHTML = '<div class="search-result-empty">Search failed — try again.</div>';
      resultsBox.classList.add('open');
    }
  }

  function renderResults(results) {
    resultsBox.innerHTML = '';
    if (!results.length) {
      resultsBox.innerHTML = '<div class="search-result-empty">No matches found.</div>';
      resultsBox.classList.add('open');
      return;
    }
    results.forEach(r => {
      const row = document.createElement('div');
      row.className = 'search-result-row' + (r.locked ? ' locked' : '');
      row.innerHTML = `
        <div class="search-result-left">
          <span class="search-result-sym">${r.symbol}</span>
          <span class="search-result-name">${r.name}</span>
        </div>
        ${r.locked ? `<span class="search-result-lock">🔒 Lvl ${window.CRYPTO_UNLOCK_LEVEL}</span>` : (r.type === 'crypto' ? '<span class="tag">Crypto</span>' : '')}
      `;
      if (!r.locked) {
        row.addEventListener('click', () => selectResult(r));
      }
      resultsBox.appendChild(row);
    });
    resultsBox.classList.add('open');
  }

  async function selectResult(r) {
    resultsBox.classList.remove('open');
    input.value = '';
    try {
      const res = await fetch(`/practice/api/quote/${encodeURIComponent(r.symbol)}`);
      const quote = await res.json();
      if (!res.ok) throw new Error(quote.error || 'Could not load quote');
      if (openChartModal) {
        openChartModal(quote.symbol, quote.name, quote.price, quote.is_crypto);
      }
    } catch (e) {
      resultsBox.innerHTML = `<div class="search-result-empty">Couldn't load ${r.symbol} — try again.</div>`;
      resultsBox.classList.add('open');
    }
  }
}

/* ---------- Level-up celebration ---------- */
function initLevelUpCelebration() {
  const payloadEl = document.getElementById('levelUpPayload');
  const overlay = document.getElementById('celebrationOverlay');
  if (!payloadEl || !overlay) return;

  let data;
  try {
    data = JSON.parse(payloadEl.textContent);
  } catch (e) {
    return;
  }

  document.getElementById('celebrationIcon').textContent = data.icon;
  document.getElementById('celebrationLevel').textContent = data.level;
  document.getElementById('celebrationBadge').textContent = `${data.icon} ${data.name}`;

  overlay.classList.add('open');
  launchConfetti();
  setTimeout(launchConfetti, 400);

  function close() { overlay.classList.remove('open'); }
  document.getElementById('celebrationDismiss').addEventListener('click', close);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
  setTimeout(close, 8000);
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
