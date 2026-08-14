// Money Manager Application Controller - Complete v5.0
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initIncomePreview();
    initTradeModalEvents();
    loadDashboard();
    loadPortfolio();
    runNetWorthProjection();
    runCompoundCalculator();
});

let netWorthDonutChart = null;
let projectionLineChart = null;
let compoundLineChart = null;

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            switchTab(tabId);
        });
    });

    const quickIncBtn = document.getElementById('btn-quick-income');
    if (quickIncBtn) quickIncBtn.addEventListener('click', () => switchTab('income'));

    const refBtn = document.getElementById('btn-refresh-prices');
    if (refBtn) refBtn.addEventListener('click', refreshStockPrices);
    const refBtnTab = document.getElementById('btn-refresh-prices-tab');
    if (refBtnTab) refBtnTab.addEventListener('click', refreshStockPrices);

    const addHoldBtn = document.getElementById('btn-add-holding');
    if (addHoldBtn) addHoldBtn.addEventListener('click', () => openModal('modal-add-holding'));
    const addHoldBtnTab = document.getElementById('btn-add-holding-tab');
    if (addHoldBtnTab) addHoldBtnTab.addEventListener('click', () => openModal('modal-add-holding'));

    const addGoalBtn = document.getElementById('btn-add-goal');
    if (addGoalBtn) addGoalBtn.addEventListener('click', () => openModal('modal-add-goal'));

    const runPlanBtn = document.getElementById('btn-run-plan');
    if (runPlanBtn) runPlanBtn.addEventListener('click', runWealthPlan);

    // Form Submissions
    const formInc = document.getElementById('form-income');
    if (formInc) formInc.addEventListener('submit', handleIncomeSubmit);

    const formSync = document.getElementById('form-spending-sync');
    if (formSync) formSync.addEventListener('submit', handleSpendingSyncSubmit);

    const formXfer = document.getElementById('form-transfer');
    if (formXfer) formXfer.addEventListener('submit', handleTransferSubmit);

    const formWithdraw = document.getElementById('form-savings-withdraw');
    if (formWithdraw) formWithdraw.addEventListener('submit', handleSavingsWithdrawSubmit);

    const formHold = document.getElementById('form-add-holding');
    if (formHold) formHold.addEventListener('submit', handleAddHoldingSubmit);

    const formTrade = document.getElementById('form-trade');
    if (formTrade) formTrade.addEventListener('submit', handleTradeSubmit);

    const formProj = document.getElementById('form-projection');
    if (formProj) formProj.addEventListener('submit', handleProjectionSubmit);

    const formComp = document.getElementById('form-compound');
    if (formComp) formComp.addEventListener('submit', handleCompoundSubmit);

    const formGoal = document.getElementById('form-add-goal');
    if (formGoal) formGoal.addEventListener('submit', handleAddGoalSubmit);

    const formWatch = document.getElementById('form-add-watchlist');
    if (formWatch) formWatch.addEventListener('submit', handleAddWatchlistSubmit);
}

function switchTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));

    const targetNav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
    const targetPane = document.getElementById(`tab-${tabId}`);

    if (targetNav && targetPane) {
        targetNav.classList.add('active');
        targetPane.classList.add('active');
    }

    if (tabId === 'overview') {
        loadDashboard();
    } else if (tabId === 'portfolio') {
        loadPortfolio();
        loadWatchlist();
        loadDividendTracker();
    } else if (tabId === 'goals') {
        loadGoals();
    } else if (tabId === 'history') {
        loadTransactionHistory();
    } else if (tabId === 'tools') {
        runCompoundCalculator();
        loadNetWorthMilestones();
    } else if (tabId === 'planner') {
        renderPlanEventList();
    }
}

function switchPortSubtab(subId) {
    document.querySelectorAll('.subtab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.port-subpane').forEach(pane => pane.style.display = 'none');

    const activeBtn = document.getElementById(`subtab-btn-${subId}`);
    const activePane = document.getElementById(`port-sub-${subId}`);

    if (activeBtn) activeBtn.classList.add('active');
    if (activePane) activePane.style.display = 'block';

    const addHoldBtn = document.getElementById('btn-add-holding-tab');
    const addWatchBtn = document.getElementById('btn-add-watchlist-tab');

    if (subId === 'watchlist') {
        if (addHoldBtn) addHoldBtn.style.display = 'none';
        if (addWatchBtn) addWatchBtn.style.display = 'inline-flex';
        loadWatchlist();
    } else {
        if (addHoldBtn) addHoldBtn.style.display = 'inline-flex';
        if (addWatchBtn) addWatchBtn.style.display = 'none';
    }

    if (subId === 'dividends') loadDividendTracker();
    if (subId === 'allocator') loadDashboard();
}

// Income Preview (10% Spending, 40% Liquid Savings, 50% Stock Budget)
function initIncomePreview() {
    const amountInput = document.getElementById('income-amount');
    const spendingPctInput = document.getElementById('income-spending-pct');
    const savingsPctInput = document.getElementById('income-savings-pct');
    const stockPctInput = document.getElementById('income-stock-pct');

    function updatePreview() {
        if (!amountInput) return;
        const pay = parseFloat(amountInput.value) || 0;
        const spendingPct = parseFloat(spendingPctInput.value) || 10;
        const savingsPct = parseFloat(savingsPctInput.value) || 40;
        const stockPct = 100 - spendingPct - savingsPct;

        if (stockPctInput) stockPctInput.value = stockPct > 0 ? stockPct : 0;

        const spendingAmt = pay * (spendingPct / 100);
        const savingsAmt = pay * (savingsPct / 100);
        const stockAmt = pay * (stockPct / 100);

        const prevPay = document.getElementById('prev-pay');
        if (prevPay) prevPay.textContent = `$${pay.toFixed(2)}`;

        const prevSpend = document.getElementById('prev-spending');
        if (prevSpend) prevSpend.textContent = `$${spendingAmt.toFixed(2)}`;

        const prevSave = document.getElementById('prev-savings');
        if (prevSave) prevSave.textContent = `$${savingsAmt.toFixed(2)}`;

        const prevStockActive = document.getElementById('prev-stock-active');
        if (prevStockActive) prevStockActive.textContent = `$${stockAmt.toFixed(2)}`;

        const prevStockDip = document.getElementById('prev-stock-dip');
        if (prevStockDip) prevStockDip.textContent = `$${(0).toFixed(2)}`;
    }

    if (amountInput) amountInput.addEventListener('input', updatePreview);
    if (spendingPctInput) spendingPctInput.addEventListener('input', updatePreview);
    if (savingsPctInput) savingsPctInput.addEventListener('input', updatePreview);

    updatePreview();
}

// Dashboard Loader
async function loadDashboard() {
    try {
        const res = await fetch('/api/dashboard');
        const data = await res.json();

        const netWorthEl = document.getElementById('dash-net-worth');
        if (netWorthEl) netWorthEl.textContent = `$${data.net_worth.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

        const savingsEl = document.getElementById('dash-savings');
        if (savingsEl) savingsEl.textContent = `$${data.liquid_savings.toFixed(2)}`;

        const spendingEl = document.getElementById('dash-spending');
        if (spendingEl) spendingEl.textContent = `$${data.spending_balance.toFixed(2)}`;

        const budgetEl = document.getElementById('dash-stock-budget');
        if (budgetEl) budgetEl.textContent = `$${data.stock_investment_budget.toFixed(2)}`;

        const dipEl = document.getElementById('dash-dip-budget');
        if (dipEl) dipEl.textContent = '';

        const portValEl = document.getElementById('dash-portfolio-val');
        if (portValEl) portValEl.textContent = `$${data.portfolio_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

        const syncBalEl = document.getElementById('sync-current-bal');
        if (syncBalEl) syncBalEl.textContent = `$${data.spending_balance.toFixed(2)}`;

        const gainEl = document.getElementById('dash-portfolio-gain');
        if (gainEl) {
            const gainSign = data.total_gain_loss >= 0 ? '+' : '';
            gainEl.textContent = `Gain/Loss: ${gainSign}$${data.total_gain_loss.toFixed(2)} (${data.gain_loss_pct.toFixed(2)}%)`;
            gainEl.className = data.total_gain_loss >= 0 ? 'metric-footer text-green' : 'metric-footer text-rose';
        }

        const holdingsCountEl = document.getElementById('dash-holdings-count');
        if (holdingsCountEl) holdingsCountEl.textContent = `${data.holdings_count} Holdings`;

        renderNetWorthDonut(data.liquid_savings, data.portfolio_value, data.spending_balance, data.stock_investment_budget);
        renderRecentActivity(data.recent_transactions);
        renderDashboardGoals();
        loadNetWorthMilestones();
    } catch (err) {
        console.error('Failed to load dashboard data:', err);
    }
}

// Portfolio Loader
async function loadPortfolio() {
    try {
        const res = await fetch('/api/portfolio');
        const data = await res.json();

        const totalValEl = document.getElementById('port-total-value');
        if (totalValEl) totalValEl.textContent = `$${data.total_value_aud.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

        const totalCostEl = document.getElementById('port-total-cost');
        if (totalCostEl) totalCostEl.textContent = `$${data.total_cost_aud.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

        const totalGainEl = document.getElementById('port-total-gain');
        if (totalGainEl) {
            const sign = data.total_gain_loss_aud >= 0 ? '+' : '';
            totalGainEl.textContent = `${sign}$${data.total_gain_loss_aud.toFixed(2)} (${data.total_gain_loss_pct.toFixed(2)}%)`;
            totalGainEl.className = data.total_gain_loss_aud >= 0 ? 'metric-value text-green' : 'metric-value text-rose';
        }

        const tbody = document.getElementById('table-portfolio-body');
        if (!tbody) return;

        if (!data.holdings || data.holdings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No stock holdings recorded yet. Click "+ Add Stock Holding" to enter your positions.</td></tr>';
            return;
        }

        tbody.innerHTML = data.holdings.map(h => {
            const returnClass = h.gain_loss_aud >= 0 ? 'text-green' : 'text-rose';
            const returnSign = h.gain_loss_aud >= 0 ? '+' : '';
            const dayClass = h.daily_change >= 0 ? 'text-green' : 'text-rose';
            const daySign = h.daily_change >= 0 ? '+' : '';
            const exBadge = h.exchange === 'ASX' ? 'badge-asx' : 'badge-us';
            const currSymbol = h.currency === 'USD' ? 'US$' : '$';

            return `
                <tr>
                    <td><strong>${h.code}</strong> <span class="badge ${exBadge}">${h.exchange}</span></td>
                    <td style="font-weight: 500;">${h.name}</td>
                    <td>${h.shares}</td>
                    <td>${currSymbol}${h.avg_cost.toFixed(2)}</td>
                    <td>${currSymbol}${h.current_price.toFixed(2)}</td>
                    <td><strong>$${h.market_value_aud.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} AUD</strong> <small class="text-muted">(${currSymbol}${h.market_value_native.toFixed(2)})</small></td>
                    <td class="${dayClass}">${daySign}${currSymbol}${h.daily_change.toFixed(2)} (${h.daily_change_pct.toFixed(2)}%)</td>
                    <td class="${returnClass}" style="font-weight: 700;">${returnSign}$${h.gain_loss_aud.toFixed(2)} AUD (${h.gain_loss_pct.toFixed(2)}%)</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="openTradeModal('BUY', '${h.ticker}', ${h.current_price})">Buy</button>
                        <button class="btn btn-sm btn-secondary" onclick="openTradeModal('SELL', '${h.ticker}', ${h.current_price})">Sell</button>
                    </td>
                </tr>
            `;
        }).join('');

        // Render Active Stock Budget Purchase Calculator Table
        try {
            const dashRes = await fetch('/api/dashboard');
            const dashData = await dashRes.json();
            const activeBudget = dashData.stock_investment_budget || 0.0;

            const calcBudEl = document.getElementById('holding-calc-budget');
            if (calcBudEl) calcBudEl.textContent = activeBudget.toFixed(2);

            const calcTbody = document.getElementById('holding-calc-table-body');
            if (calcTbody && data.holdings) {
                if (activeBudget <= 0) {
                    calcTbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No active stock budget available ($0.00). Log income to allocate stock budget.</td></tr>';
                } else {
                    calcTbody.innerHTML = data.holdings.map(h => {
                        const priceAud = h.market_value_aud / h.shares;
                        const maxShares = Math.floor(activeBudget / priceAud);
                        const totalCost = maxShares * priceAud;
                        const remaining = activeBudget - totalCost;

                        return `
                            <tr>
                                <td><strong>${h.code}</strong></td>
                                <td>${h.name}</td>
                                <td>$${priceAud.toFixed(2)} AUD</td>
                                <td class="text-green font-bold" style="font-size:1.05rem;">${maxShares} shares</td>
                                <td>$${totalCost.toFixed(2)} AUD</td>
                                <td class="text-muted">$${remaining.toFixed(2)} AUD</td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        } catch (errCalc) {
            console.error('Failed to render stock budget purchase calculator:', errCalc);
        }
    } catch (err) {
        console.error('Failed to load portfolio:', err);
    }
}

// Refresh Prices Button
async function refreshStockPrices() {
    const btns = [document.getElementById('btn-refresh-prices'), document.getElementById('btn-refresh-prices-tab')];
    btns.forEach(b => { if (b) { b.disabled = true; b.textContent = 'Refreshing...'; } });
    try {
        await fetch('/api/portfolio/refresh', { method: 'POST' });
        await loadDashboard();
        await loadPortfolio();
        alert('Stock prices refreshed successfully.');
    } catch (err) {
        alert('Failed to refresh stock prices.');
    } finally {
        btns.forEach(b => {
            if (b) {
                b.disabled = false;
                b.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Refresh Prices';
            }
        });
    }
}

// Donut Chart
function renderNetWorthDonut(savings, portfolio, spending, stockBudget) {
    const canvas = document.getElementById('chart-net-worth-donut');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (netWorthDonutChart) netWorthDonutChart.destroy();

    netWorthDonutChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Liquid Savings', 'Stock Portfolio', 'Spending Cash', 'Active Stock Budget'],
            datasets: [{
                data: [savings, portfolio, spending, stockBudget],
                backgroundColor: ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            cutout: '70%'
        }
    });
}

function renderRecentActivity(txs) {
    const container = document.getElementById('dash-recent-txs');
    if (!container) return;
    if (!txs || txs.length === 0) {
        container.innerHTML = '<p class="text-muted">No recent transactions recorded.</p>';
        return;
    }

    const undoableTypes = ['INCOME', 'EXPENSE'];
    container.innerHTML = txs.map(t => `
        <div class="activity-item">
            <div style="display:flex; justify-content:space-between; font-weight:600; align-items:center;">
                <span>${t.type}</span>
                <div style="display:flex; gap:0.5rem; align-items:center;">
                    <span class="${t.type === 'INCOME' ? 'text-green' : (t.type === 'EXPENSE' ? 'text-rose' : 'text-blue')}">$${Math.abs(t.amount).toFixed(2)}</span>
                    ${undoableTypes.includes(t.type) ? `<button class="btn btn-sm" style="padding:2px 8px; font-size:0.72rem; background:rgba(239,68,68,0.15); color:#ef4444; border:1px solid rgba(239,68,68,0.3); border-radius:4px; cursor:pointer;" onclick="undoTransaction(${t.id})">Undo</button>` : ''}
                </div>
            </div>
            <div style="color:var(--text-secondary); font-size:0.8rem; margin-top:2px;">${t.description}</div>
            <div class="activity-date">${new Date(t.date).toLocaleDateString()}</div>
        </div>
    `).join('');
}

async function undoTransaction(txId) {
    if (!confirm(`Reverse transaction #${txId}? This will subtract the amounts back from your account balances.`)) return;
    try {
        const res = await fetch(`/api/transactions/undo/${txId}`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            await loadDashboard();
        } else {
            alert(`Could not undo: ${data.error}`);
        }
    } catch (err) {
        alert('Failed to undo transaction.');
    }
}

async function renderDashboardGoals() {
    const container = document.getElementById('dash-goals-list');
    if (!container) return;
    try {
        const res = await fetch('/api/goals');
        const data = await res.json();
        const goals = data.goals || [];
        if (goals.length === 0) {
            container.innerHTML = '<p class="text-muted">No goals created yet. Visit Goals tab to set targets.</p>';
            return;
        }
        container.innerHTML = goals.map(g => {
            const pct = g.target_amount > 0 ? Math.min(100, Math.round((g.current_amount / g.target_amount) * 100)) : 0;
            const liveDot = g.live_linked ? '<span style="color:#10b981;font-size:0.7rem;"> (live)</span>' : '';
            return `
                <div style="margin-bottom:0.75rem;">
                    <div style="display:flex; justify-content:space-between; font-size:0.88rem; font-weight:600;">
                        <span>${g.title}${liveDot}</span>
                        <span class="text-green">$${g.current_amount.toFixed(2)} / $${g.target_amount.toFixed(2)}</span>
                    </div>
                    <div class="progress-bar-bg" style="margin-top:0.3rem;">
                        <div class="progress-bar-fill" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Failed to load goals for dashboard:', err);
    }
}

// Form Handlers
async function handleIncomeSubmit(e) {
    e.preventDefault();
    const payload = {
        description: document.getElementById('income-desc').value,
        amount: parseFloat(document.getElementById('income-amount').value),
        spending_pct: parseFloat(document.getElementById('income-spending-pct').value),
        savings_pct: parseFloat(document.getElementById('income-savings-pct').value),
        stock_pct: parseFloat(document.getElementById('income-stock-pct').value)
    };

    try {
        const res = await fetch('/api/income', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-income');
            loadDashboard();
            loadPortfolio();
            alert(data.message);
        } else {
            alert('Error: ' + (data.error || 'Failed to record income'));
        }
    } catch (err) {
        alert('Network error while processing income.');
    }
}

async function handleSpendingSyncSubmit(e) {
    e.preventDefault();
    const payload = {
        new_balance: parseFloat(document.getElementById('sync-new-balance').value),
        description: document.getElementById('sync-desc').value
    };

    try {
        const res = await fetch('/api/expenses/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            alert('Spending balance updated successfully.');
            loadDashboard();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to sync spending balance.');
    }
}

async function quickDeduct(amount, desc) {
    try {
        const res = await fetch('/api/expenses/quick', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: amount, description: desc })
        });
        const data = await res.json();
        if (data.success) {
            alert(`Deducted $${amount} for ${desc}. New Spending Cash: $${data.new_balance.toFixed(2)}`);
            loadDashboard();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to execute quick deduction.');
    }
}

async function handleTransferSubmit(e) {
    e.preventDefault();
    const payload = {
        from_account: document.getElementById('transfer-from').value,
        to_account: document.getElementById('transfer-to').value,
        amount: parseFloat(document.getElementById('transfer-amount').value),
        description: document.getElementById('transfer-desc').value
    };

    try {
        const res = await fetch('/api/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            alert('Transfer executed successfully.');
            document.getElementById('form-transfer').reset();
            loadDashboard();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to execute transfer.');
    }
}

async function handleSavingsWithdrawSubmit(e) {
    e.preventDefault();
    const payload = {
        amount: parseFloat(document.getElementById('withdraw-amount').value),
        description: document.getElementById('withdraw-desc').value
    };

    try {
        const res = await fetch('/api/expenses/savings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            alert(`Withdrew $${payload.amount.toFixed(2)} from Liquid Savings.`);
            document.getElementById('form-savings-withdraw').reset();
            loadDashboard();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to process withdrawal.');
    }
}

async function handleAddHoldingSubmit(e) {
    e.preventDefault();
    const payload = {
        ticker: document.getElementById('hold-ticker').value,
        shares: parseFloat(document.getElementById('hold-shares').value),
        avg_cost: parseFloat(document.getElementById('hold-cost').value)
    };

    try {
        const res = await fetch('/api/portfolio/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-add-holding');
            document.getElementById('form-add-holding').reset();
            loadDashboard();
            loadPortfolio();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to add holding.');
    }
}

function initTradeModalEvents() {
    const sharesInput = document.getElementById('trade-shares');
    const priceInput = document.getElementById('trade-price');
    const totalDisplay = document.getElementById('trade-total-display');

    function updateTotal() {
        if (!sharesInput || !priceInput || !totalDisplay) return;
        const shares = parseFloat(sharesInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;
        totalDisplay.textContent = `$${(shares * price).toFixed(2)}`;
    }

    if (sharesInput) sharesInput.addEventListener('input', updateTotal);
    if (priceInput) priceInput.addEventListener('input', updateTotal);
}

function openTradeModal(action, ticker, currentPrice) {
    document.getElementById('trade-action').value = action;
    document.getElementById('trade-modal-title').textContent = `${action} ${ticker}`;
    document.getElementById('trade-ticker').value = ticker;
    document.getElementById('trade-shares').value = 1;
    document.getElementById('trade-price').value = currentPrice;
    document.getElementById('btn-submit-trade').textContent = `Confirm ${action}`;
    document.getElementById('trade-total-display').textContent = `$${currentPrice.toFixed(2)}`;
    openModal('modal-trade');
}

async function handleTradeSubmit(e) {
    e.preventDefault();
    const payload = {
        action: document.getElementById('trade-action').value,
        ticker: document.getElementById('trade-ticker').value,
        shares: parseFloat(document.getElementById('trade-shares').value),
        price: parseFloat(document.getElementById('trade-price').value)
    };

    try {
        const res = await fetch('/api/trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-trade');
            loadDashboard();
            loadPortfolio();
            alert(`Executed ${payload.action} for ${payload.shares} shares of ${payload.ticker}.`);
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to execute trade.');
    }
}

// Net Worth Projection Tool
function handleProjectionSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    runNetWorthProjection();
}

async function runNetWorthProjection() {
    const payAmtEl = document.getElementById('proj-pay-amount');
    const payFreqEl = document.getElementById('proj-pay-freq');
    const stockRetEl = document.getElementById('proj-stock-return');
    const savRetEl = document.getElementById('proj-savings-return');
    const yrsEl = document.getElementById('proj-years');

    if (!payAmtEl || !payFreqEl) return;

    const payload = {
        type: 'projection',
        pay_amount: parseFloat(payAmtEl.value) || 950,
        pay_frequency: payFreqEl.value,
        stock_annual_return: parseFloat(stockRetEl.value) || 8.0,
        savings_annual_return: parseFloat(savRetEl.value) || 4.0,
        years: parseInt(yrsEl.value) || 10
    };

    try {
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            const sim = data.simulation;
            const yr1El = document.getElementById('proj-result-yr1');
            if (yr1El) yr1El.textContent = `$${sim.year_1_net_worth.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

            const yr5El = document.getElementById('proj-result-yr5');
            if (yr5El) yr5El.textContent = `$${sim.year_5_net_worth.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

            const finalEl = document.getElementById('proj-result-final');
            if (finalEl) finalEl.textContent = `$${sim.final_net_worth.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

            renderProjectionChart(sim.labels, sim.net_worth, sim.portfolio, sim.savings);
        }
    } catch (err) {
        console.error('Projection simulation failed:', err);
    }
}

function renderProjectionChart(labels, netWorth, portfolio, savings) {
    const canvas = document.getElementById('chart-projection');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (projectionLineChart) projectionLineChart.destroy();

    projectionLineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Net Worth',
                    data: netWorth,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Stock Portfolio Value',
                    data: portfolio,
                    borderColor: '#8b5cf6',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.2
                },
                {
                    label: 'Liquid Savings',
                    data: savings,
                    borderColor: '#6366f1',
                    borderDash: [2, 2],
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } } }
            },
            scales: {
                x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

// Compound Interest Calculator
function handleCompoundSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    runCompoundCalculator();
}

async function runCompoundCalculator() {
    const initialEl = document.getElementById('comp-initial');
    const monthlyEl = document.getElementById('comp-monthly');
    const rateEl = document.getElementById('comp-rate');
    const yearsEl = document.getElementById('comp-years');

    if (!initialEl || !monthlyEl) return;

    const payload = {
        type: 'compound',
        initial_amount: parseFloat(initialEl.value) || 1000,
        monthly_contribution: parseFloat(monthlyEl.value) || 500,
        annual_interest_rate: parseFloat(rateEl.value) || 8.0,
        years: parseInt(yearsEl.value) || 10
    };

    try {
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            const sim = data.simulation;
            const finalEl = document.getElementById('comp-result-final');
            if (finalEl) finalEl.textContent = `$${sim.final_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

            const contribEl = document.getElementById('comp-result-contrib');
            if (contribEl) contribEl.textContent = `$${sim.total_contributions.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

            const interestEl = document.getElementById('comp-result-interest');
            if (interestEl) interestEl.textContent = `$${sim.total_interest.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

            renderCompoundChart(sim.labels, sim.future_values, sim.total_contributions_timeline);
        }
    } catch (err) {
        console.error('Compound simulation failed:', err);
    }
}

function renderCompoundChart(labels, futureValues, contributions) {
    const canvas = document.getElementById('chart-compound');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (compoundLineChart) compoundLineChart.destroy();

    compoundLineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Future Value',
                    data: futureValues,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Contributions',
                    data: contributions,
                    borderColor: '#6366f1',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } } }
            },
            scales: {
                x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

// Transaction History
async function loadTransactionHistory() {
    try {
        const res = await fetch('/api/transactions');
        const data = await res.json();
        const tbody = document.getElementById('table-history-body');
        if (!tbody) return;

        if (!data.transactions || data.transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No transactions recorded yet.</td></tr>';
            return;
        }

        tbody.innerHTML = data.transactions.map(t => `
            <tr>
                <td>${new Date(t.date).toLocaleString()}</td>
                <td><span class="badge ${t.type === 'INCOME' ? 'badge-success' : (t.type === 'EXPENSE' ? 'badge-warning' : 'badge-info')}">${t.type}</span></td>
                <td>$${t.amount.toFixed(2)}</td>
                <td>${t.ticker || '-'} ${t.shares ? `(${t.shares} @ $${t.price})` : ''}</td>
                <td>${t.description}</td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Failed to load transaction history:', err);
    }
}

// Modal Helpers
function openModal(id) {
    document.getElementById(id).classList.remove('hidden');
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

// =====================================================================
// GOALS - Updated: linked accounts, delete, live badge
// =====================================================================

function updateGoalCurrentVisibility() {
    const linked = document.getElementById('goal-linked').value;
    const group = document.getElementById('goal-current-group');
    if (group) group.style.display = linked === 'none' ? 'block' : 'none';
}

async function loadGoals() {
    try {
        const res = await fetch('/api/goals');
        const data = await res.json();
        const grid = document.getElementById('goals-grid');
        if (!grid) return;
        if (!data.goals || data.goals.length === 0) {
            grid.innerHTML = '<p class="text-muted">No goals created yet. Click "+ Add New Goal" to set a target.</p>';
            return;
        }

        const CAT_COLORS = {
            Savings: 'text-blue', Portfolio: 'text-purple', NetWorth: 'text-green',
            Spending: 'text-orange', Property: 'text-cyan', Custom: 'text-rose'
        };

        grid.innerHTML = data.goals.map(g => {
            const pct = g.target_amount > 0 ? Math.min(100, Math.round((g.current_amount / g.target_amount) * 100)) : 0;
            const colorClass = CAT_COLORS[g.category] || 'text-blue';
            const liveBadge = g.live_linked
                ? '<span class="badge badge-success" style="font-size:0.68rem;">Live</span>'
                : '';
            const linkedLabel = g.linked_account && g.linked_account !== 'none'
                ? `<small class="text-muted" style="font-size:0.73rem;">Linked: ${g.linked_account}</small>`
                : '';
            return `
                <div class="goal-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.35rem;">
                        <div>
                            <span class="badge badge-info" style="margin-bottom:0.3rem;">${g.category}</span>
                            <h3 style="font-size:1rem; font-weight:700;">${g.title}</h3>
                            ${linkedLabel}
                        </div>
                        <div style="display:flex; gap:0.4rem; align-items:center;">
                            ${liveBadge}
                            <button class="btn btn-sm btn-danger" onclick="deleteGoal(${g.id})" title="Delete goal">&#x2715;</button>
                        </div>
                    </div>
                    <div style="font-size:1.4rem; font-weight:700;" class="${colorClass}">$${g.current_amount.toFixed(2)}</div>
                    <div style="font-size:0.82rem; color:var(--text-secondary); margin-bottom:0.4rem;">Target: $${g.target_amount.toFixed(2)}</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${pct}%;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.78rem; font-weight:600; margin-top:0.3rem;">
                        <span>${pct}% reached</span>
                        <span class="text-muted">$${Math.max(0, g.target_amount - g.current_amount).toFixed(2)} to go</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Failed to load goals:', err);
    }
}

async function deleteGoal(id) {
    if (!confirm('Delete this goal?')) return;
    try {
        await fetch(`/api/goals?id=${id}`, { method: 'DELETE' });
        loadGoals();
        loadDashboard();
    } catch (err) {
        alert('Failed to delete goal.');
    }
}

async function handleAddGoalSubmit(e) {
    e.preventDefault();
    const linked = document.getElementById('goal-linked').value;
    const payload = {
        title: document.getElementById('goal-title').value,
        target_amount: parseFloat(document.getElementById('goal-target').value),
        current_amount: linked === 'none' ? parseFloat(document.getElementById('goal-current').value) : 0,
        category: document.getElementById('goal-category').value,
        linked_account: linked
    };

    try {
        const res = await fetch('/api/goals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-add-goal');
            document.getElementById('form-add-goal').reset();
            updateGoalCurrentVisibility();
            loadGoals();
            loadDashboard();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to add goal.');
    }
}

// =====================================================================
// WEALTH PLANNER
// =====================================================================

let planEvents = [];
let wealthPlanChart = null;

function updateEventForm() {
    const type = document.getElementById('event-type').value;
    const allTypes = ['salary_change','property_buy','property_sell','loan_refinance','lump_invest','lump_sell','major_expense','windfall','career_break','split_change'];
    allTypes.forEach(t => {
        const el = document.getElementById(`event-fields-${t}`);
        if (el) el.style.display = t === type ? 'block' : 'none';
    });
}

function addPlanEvent() {
    const type = document.getElementById('event-type').value;
    const year = parseInt(document.getElementById('event-year').value) || 0;
    const month = parseInt(document.getElementById('event-month').value) || 1;

    let ev = { type, year, month };
    let label = '';

    if (type === 'salary_change') {
        ev.new_pay_amount = parseFloat(document.getElementById('ev-salary').value) || 1200;
        label = `Salary change to $${ev.new_pay_amount}/fortnight`;
    } else if (type === 'property_buy') {
        ev.label = document.getElementById('ev-prop-label').value || 'Home';
        ev.price = parseFloat(document.getElementById('ev-price').value) || 600000;
        ev.deposit_pct = parseFloat(document.getElementById('ev-deposit').value) || 20;
        ev.rate_pct = parseFloat(document.getElementById('ev-rate').value) || 5.5;
        ev.term_years = parseInt(document.getElementById('ev-term').value) || 30;
        ev.appreciation_pct = parseFloat(document.getElementById('ev-appreciation').value) || 5;
        ev.rental_yield_pct = parseFloat(document.getElementById('ev-rental-yield').value) || 0;
        const emi = calcEMI(ev.price * (1 - ev.deposit_pct/100), ev.rate_pct, ev.term_years);
        const rentalStr = ev.rental_yield_pct > 0 ? ` | Rental ${ev.rental_yield_pct}%/yr` : ' | Owner-occupied';
        label = `Buy "${ev.label}" $${ev.price.toLocaleString()} | EMI ~$${emi.toFixed(0)}/mo${rentalStr}`;
    } else if (type === 'property_sell') {
        ev.property_id = parseInt(document.getElementById('ev-sell-prop-id').value) || 0;
        const op = document.getElementById('ev-sell-price').value;
        ev.override_price = op ? parseFloat(op) : null;
        label = `Sell Property #${ev.property_id}${ev.override_price ? ` @ $${ev.override_price.toLocaleString()}` : ' (projected price)'}`;
    } else if (type === 'loan_refinance') {
        ev.property_id = parseInt(document.getElementById('ev-refi-prop-id').value) || 0;
        ev.new_rate_pct = parseFloat(document.getElementById('ev-refi-rate').value) || 4.5;
        label = `Refinance Property #${ev.property_id} to ${ev.new_rate_pct}%/yr`;
    } else if (type === 'lump_invest') {
        ev.amount = parseFloat(document.getElementById('ev-invest-amount').value) || 5000;
        label = `Lump sum invest $${ev.amount.toLocaleString()} into stocks`;
    } else if (type === 'lump_sell') {
        ev.amount = parseFloat(document.getElementById('ev-sell-amount').value) || 5000;
        label = `Liquidate $${ev.amount.toLocaleString()} from portfolio`;
    } else if (type === 'major_expense') {
        ev.label = document.getElementById('ev-expense-label').value || 'Expense';
        ev.amount = parseFloat(document.getElementById('ev-expense-amount').value) || 20000;
        label = `${ev.label}: -$${ev.amount.toLocaleString()}`;
    } else if (type === 'windfall') {
        ev.source = document.getElementById('ev-windfall-source').value || 'Windfall';
        ev.amount = parseFloat(document.getElementById('ev-windfall-amount').value) || 50000;
        label = `${ev.source}: +$${ev.amount.toLocaleString()}`;
    } else if (type === 'career_break') {
        ev.duration_months = parseInt(document.getElementById('ev-break-months').value) || 6;
        label = `Career break: ${ev.duration_months} month${ev.duration_months !== 1 ? 's' : ''} with no income`;
    } else if (type === 'split_change') {
        ev.spending_pct = parseFloat(document.getElementById('ev-split-spend').value) || 10;
        ev.savings_pct = parseFloat(document.getElementById('ev-split-save').value) || 40;
        ev.stock_pct = parseFloat(document.getElementById('ev-split-stock').value) || 50;
        label = `Split change: ${ev.spending_pct}% spend / ${ev.savings_pct}% save / ${ev.stock_pct}% stock`;
    }

    ev._label = label;
    ev._id = Date.now();
    planEvents.push(ev);
    renderPlanEventList();
}

function calcEMI(principal, annualRate, termYears) {
    const r = (annualRate / 100) / 12;
    const n = termYears * 12;
    if (r === 0) return principal / n;
    return principal * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
}

function removePlanEvent(id) {
    planEvents = planEvents.filter(e => e._id !== id);
    renderPlanEventList();
}

function renderPlanEventList() {
    const container = document.getElementById('plan-events-list');
    const countEl = document.getElementById('plan-event-count');
    if (countEl) countEl.textContent = `${planEvents.length} event${planEvents.length !== 1 ? 's' : ''}`;
    if (!container) return;

    if (planEvents.length === 0) {
        container.innerHTML = '<p class="text-muted" style="font-size:0.88rem;">No events added yet.</p>';
        return;
    }

    const sorted = [...planEvents].sort((a, b) => a.year*12+a.month - (b.year*12+b.month));
    const TYPE_COLORS = {
        salary_change: 'text-green', property_buy: 'text-blue', property_sell: 'text-cyan',
        loan_refinance: 'text-amber', lump_invest: 'text-purple', lump_sell: 'text-orange',
        major_expense: 'text-rose', windfall: 'text-green', career_break: 'text-rose',
        split_change: 'text-amber'
    };

    container.innerHTML = sorted.map(ev => `
        <div class="plan-event-item">
            <div class="plan-event-time">Yr ${ev.year}, Mo ${ev.month}</div>
            <div class="plan-event-label ${TYPE_COLORS[ev.type] || ''}">${ev._label}</div>
            <button class="btn btn-sm btn-danger" onclick="removePlanEvent(${ev._id})">&#x2715;</button>
        </div>
    `).join('');
}

async function runWealthPlan() {
    const btn = document.getElementById('btn-run-plan');
    if (btn) { btn.disabled = true; btn.textContent = 'Simulating...'; }

    const config = {
        pay_amount: parseFloat(document.getElementById('plan-pay').value) || 950,
        pay_frequency: document.getElementById('plan-freq').value,
        spending_pct: parseFloat(document.getElementById('plan-spending-pct').value) || 10,
        savings_pct: parseFloat(document.getElementById('plan-savings-pct').value) || 40,
        stock_pct: parseFloat(document.getElementById('plan-stock-pct').value) || 50,
        stock_annual_return: parseFloat(document.getElementById('plan-stock-return').value) || 8,
        savings_annual_return: parseFloat(document.getElementById('plan-savings-return').value) || 4.5,
        dividend_yield_pct: parseFloat(document.getElementById('plan-dividend-yield').value) || 2,
        inflation_rate: parseFloat(document.getElementById('plan-inflation').value) || 3,
        employer_super_pct: parseFloat(document.getElementById('plan-super-pct').value) || 11.5,
        super_annual_return: parseFloat(document.getElementById('plan-super-return').value) || 7,
        years: parseInt(document.getElementById('plan-years').value) || 30
    };

    try {
        const res = await fetch('/api/wealth-plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ events: planEvents, config })
        });
        const data = await res.json();
        if (data.success) {
            renderWealthPlanResults(data.plan, config.years);
        } else {
            alert('Simulation failed. Please check your inputs.');
        }
    } catch (err) {
        alert('Failed to run wealth plan simulation.');
        console.error(err);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Run Simulation'; }
    }
}

function renderWealthPlanResults(plan, years) {
    const ms = plan.milestones || {};
    const milestonesEl = document.getElementById('plan-milestones');
    if (milestonesEl) milestonesEl.style.display = 'grid';

    const fmt = v => `$${(v || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = fmt(val); };

    set('plan-yr1',  ms.year_1);
    set('plan-yr5',  ms.year_5);
    set('plan-yr10', ms.year_10);
    set('plan-yr20', ms.year_20);
    set('plan-final', plan.final_net_worth);
    set('plan-final-real', plan.final_real_net_worth);

    // Chart
    const chartCard = document.getElementById('plan-chart-card');
    if (chartCard) chartCard.style.display = 'block';

    const canvas = document.getElementById('chart-wealth-plan');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        if (wealthPlanChart) wealthPlanChart.destroy();
        wealthPlanChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: plan.labels,
                datasets: [
                    { label: 'Total Net Worth',         data: plan.net_worth,       borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.07)', fill: true,  tension: 0.3, borderWidth: 2.5 },
                    { label: 'Real NW (Today\'s $)',    data: plan.real_net_worth,  borderColor: '#f59e0b', borderDash: [6,3], fill: false, tension: 0.3, borderWidth: 1.5 },
                    { label: 'Stock Portfolio',         data: plan.portfolio,       borderColor: '#8b5cf6', borderDash: [5,5], fill: false, tension: 0.2, borderWidth: 1.5 },
                    { label: 'Liquid Savings',          data: plan.savings,         borderColor: '#6366f1', borderDash: [2,4], fill: false, tension: 0.1, borderWidth: 1.5 },
                    { label: 'Property Equity',         data: plan.property_equity, borderColor: '#06b6d4', borderDash: [8,3], fill: false, tension: 0.2, borderWidth: 1.5 },
                    { label: 'Superannuation',          data: plan.super,           borderColor: '#f97316', borderDash: [4,4], fill: false, tension: 0.2, borderWidth: 1.5 }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 }, boxWidth: 20 } }
                },
                scales: {
                    x: { ticks: { color: '#64748b', maxTicksLimit: 10 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y: {
                        ticks: { color: '#64748b', callback: v => '$' + (v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'K' : v.toFixed(0)) },
                        grid: { color: 'rgba(255,255,255,0.04)' }
                    }
                }
            }
        });
    }

    // Table
    const tableCard = document.getElementById('plan-table-card');
    if (tableCard) tableCard.style.display = 'block';

    const tbody = document.getElementById('plan-table-body');
    if (tbody && plan.snapshot_table) {
        const rows = plan.snapshot_table.filter(r => r.year === 1 || r.year % 5 === 0);
        tbody.innerHTML = rows.map(r => {
            const pausedTag = r.pay_paused ? ' <span style="color:#f87171;font-size:0.7rem;">[break]</span>' : '';
            const rentalNote = (r.properties || []).filter(p => p.rental_monthly > 0)
                .map(p => `${p.label}: $${p.rental_monthly.toFixed(0)}/mo`).join(', ');
            return `
                <tr>
                    <td><strong>Year ${r.year}</strong></td>
                    <td class="text-green"><strong>${fmt(r.net_worth)}</strong></td>
                    <td class="text-amber">${fmt(r.real_net_worth)}</td>
                    <td>${fmt(r.savings)}${rentalNote ? `<br><small class="text-green" style="font-size:0.7rem;">Rental: ${rentalNote}</small>` : ''}</td>
                    <td class="text-purple">${fmt(r.portfolio)}</td>
                    <td class="text-cyan">${fmt(r.property_equity)}</td>
                    <td class="text-orange">${fmt(r.super)}</td>
                    <td>$${r.pay.toFixed(0)}${pausedTag}</td>
                </tr>
            `;
        }).join('');
    }
}

// --- WATCHLIST & INVESTOR TOOLS ---
async function loadWatchlist() {
    try {
        const res = await fetch('/api/watchlist');
        const data = await res.json();

        const countEl = document.getElementById('watchlist-count');
        if (countEl) countEl.textContent = `${data.watchlist ? data.watchlist.length : 0} items (${data.active_alerts || 0} alerts)`;

        const reserveEl = document.getElementById('watchlist-dip-reserve');
        if (reserveEl) reserveEl.textContent = `${data.dip_reserve_balance.toFixed(2)}`;

        const allocVal = document.getElementById('allocator-budget-val');
        if (allocVal && data.active_stock_budget !== undefined) {
            allocVal.textContent = data.active_stock_budget.toFixed(2);
        }

        const tbody = document.getElementById('watchlist-table-body');
        if (!tbody) return;

        if (!data.watchlist || data.watchlist.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No watchlist items yet. Click "+ Add to Watchlist" to track tickers.</td></tr>';
            return;
        }

        tbody.innerHTML = data.watchlist.map(item => {
            const isAlert = item.is_dip_triggered;
            const statusBadge = isAlert
                ? '<span class="badge badge-warning" style="background:#ef4444;color:#fff;">DIP ALERT ACTIVE</span>'
                : '<span class="badge badge-success">Normal</span>';

            const currSymbol = item.currency === 'USD' ? 'US$' : '$';
            const dipBuyText = item.suggested_buy_cash > 0
                ? `<strong class="text-green">Deploy $${item.suggested_buy_cash.toFixed(2)}</strong>`
                : '<span class="text-muted">Wait for dip</span>';

            return `
                <tr>
                    <td><strong>${item.ticker}</strong></td>
                    <td class="font-bold">${currSymbol}${item.current_price.toFixed(2)}</td>
                    <td class="text-muted">${currSymbol}${item.year_high.toFixed(2)}</td>
                    <td class="text-muted">${currSymbol}${item.year_low.toFixed(2)}</td>
                    <td class="${item.dip_from_high_pct >= item.target_dip_pct ? 'text-rose font-bold' : ''}">${item.dip_from_high_pct}%</td>
                    <td>${item.target_dip_pct}%</td>
                    <td>${statusBadge}</td>
                    <td>${dipBuyText}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="deleteWatchlistItem(${item.id})">&#x2715;</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Failed to load watchlist:', err);
    }
}

async function handleAddWatchlistSubmit(e) {
    e.preventDefault();
    const payload = {
        ticker: document.getElementById('watch-ticker').value,
        target_dip_pct: parseFloat(document.getElementById('watch-dip-pct').value) || 5.0,
        target_price: parseFloat(document.getElementById('watch-target-price').value) || 0.0,
        notes: document.getElementById('watch-notes').value
    };

    try {
        const res = await fetch('/api/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-add-watchlist');
            document.getElementById('form-add-watchlist').reset();
            loadWatchlist();
        } else {
            alert('Error: ' + (data.error || 'Failed to add watchlist item'));
        }
    } catch (err) {
        alert('Failed to add watchlist item.');
    }
}

async function deleteWatchlistItem(id) {
    try {
        const res = await fetch(`/api/watchlist?id=${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) loadWatchlist();
    } catch (err) {
        console.error('Failed to delete watchlist item:', err);
    }
}

function addAllocatorRow() {
    const container = document.getElementById('alloc-tickers-list');
    if (!container) return;
    const div = document.createElement('div');
    div.className = 'form-row';
    div.style.marginBottom = '0.5rem';
    div.innerHTML = `
        <input type="text" class="form-input alloc-ticker" placeholder="e.g. VHY.AX">
        <input type="number" class="form-input alloc-weight" placeholder="Weight %" value="50">
    `;
    container.appendChild(div);
}

async function runPurchaseAllocator() {
    const budgetInput = document.getElementById('alloc-budget');
    let budget = parseFloat(budgetInput.value);

    if (!budget || budget <= 0) {
        const dashRes = await fetch('/api/dashboard');
        const dashData = await dashRes.json();
        budget = dashData.stock_investment_budget || 0.0;
        if (budgetInput) budgetInput.value = budget;
    }

    const tickerInputs = document.querySelectorAll('.alloc-ticker');
    const weightInputs = document.querySelectorAll('.alloc-weight');

    const targets = [];
    tickerInputs.forEach((tInput, idx) => {
        const tick = tInput.value.trim().toUpperCase();
        const w = parseFloat(weightInputs[idx].value) || 0;
        if (tick) targets.push({ ticker: tick, weight_pct: w });
    });

    if (targets.length === 0) {
        alert('Please specify at least one ticker to allocate purchases.');
        return;
    }

    try {
        const res = await fetch('/api/tools/allocate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ budget, targets })
        });
        const data = await res.json();
        if (data.allocation_plan) {
            const resultsCard = document.getElementById('allocator-results');
            if (resultsCard) resultsCard.style.display = 'block';

            const details = document.getElementById('allocator-plan-details');
            if (details) {
                details.innerHTML = `
                    <p style="margin-bottom:0.5rem;font-size:0.88rem;">Spent: <strong class="text-green">$${data.total_spent.toFixed(2)}</strong> of $${data.total_budget.toFixed(2)} budget | Remaining Unspent Cash: <strong>$${data.remaining_cash.toFixed(2)}</strong></p>
                    <table class="data-table">
                        <thead>
                            <tr><th>Ticker</th><th>Price</th><th>Allocated</th><th>Shares to Buy</th><th>Cost (AUD)</th></tr>
                        </thead>
                        <tbody>
                            ${data.allocation_plan.map(p => `
                                <tr>
                                    <td><strong>${p.ticker}</strong></td>
                                    <td>$${p.price_aud.toFixed(2)}</td>
                                    <td>$${p.allocated_cash.toFixed(2)}</td>
                                    <td class="text-green font-bold" style="font-size:1.05rem;">${p.shares_to_buy} shares</td>
                                    <td>$${p.cost_aud.toFixed(2)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }
        }
    } catch (err) {
        alert('Failed to calculate allocation plan.');
    }
}

async function loadDividendTracker() {
    try {
        const res = await fetch('/api/tools/dividends');
        const data = await res.json();

        const annEl = document.getElementById('div-annual-val');
        if (annEl) annEl.textContent = `$${data.total_annual_dividends.toFixed(2)} / yr`;

        const monEl = document.getElementById('div-monthly-val');
        if (monEl) monEl.textContent = `$${data.total_monthly_dividends.toFixed(2)} / mo`;

        const badge = document.getElementById('div-total-annual');
        if (badge) badge.textContent = `$${data.total_annual_dividends.toFixed(2)} / yr`;

        const tbody = document.getElementById('dividend-table-body');
        if (!tbody) return;

        if (!data.dividend_breakdown || data.dividend_breakdown.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No stock holdings recorded yet. Add positions in Stock Portfolio tab.</td></tr>';
            return;
        }

        tbody.innerHTML = data.dividend_breakdown.map(item => `
            <tr>
                <td><strong>${item.ticker}</strong></td>
                <td>$${item.market_value_aud.toFixed(2)}</td>
                <td><span class="badge badge-info">${item.yield_pct}%</span></td>
                <td class="text-green"><strong>$${item.annual_dividend_aud.toFixed(2)} / yr</strong> ($${item.monthly_dividend_aud.toFixed(2)}/mo)</td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Failed to load dividend tracker:', err);
    }
}

async function loadNetWorthMilestones() {
    try {
        const res = await fetch('/api/tools/milestones');
        const data = await res.json();
        const grid = document.getElementById('milestones-cards-grid');
        if (!grid || !data.milestones) return;

        grid.innerHTML = data.milestones.map(m => {
            const isAchieved = m.achieved;
            const borderClass = isAchieved ? 'border-green' : 'border-blue';
            const badge = isAchieved
                ? '<span class="badge badge-success">ACHIEVED!</span>'
                : `<span class="badge badge-warning">$${m.gap_remaining.toLocaleString()} remaining</span>`;

            return `
                <div class="card metric-card ${borderClass}">
                    <div class="card-header">
                        <span class="metric-title">$${m.target.toLocaleString()} Milestone</span>
                        ${badge}
                    </div>
                    <div class="metric-value ${isAchieved ? 'text-green' : 'text-blue'}">${m.progress_pct}%</div>
                    <div class="progress-bar-bg" style="margin-top:0.4rem;">
                        <div class="progress-bar-fill" style="width:${m.progress_pct}%;"></div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Failed to load milestones:', err);
    }
}
