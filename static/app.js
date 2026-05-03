/* ─── Poly Bot Dashboard — Frontend Logic ─── */

const API = '';  // same origin

let currentSettings = {};
let isPaused = false;

// ─── Init ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupCharCount();
    loadStatus();
    loadSettings();
    loadTweets();

    // Auto-refresh every 60s
    setInterval(loadStatus, 60000);
});

// ─── Tab Navigation ───────────────────────────────
function setupTabs() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`tab-${tab}`).classList.add('active');

            if (tab === 'history') loadTweets();
        });
    });
}

// ─── Status ───────────────────────────────────────
async function loadStatus() {
    try {
        const res = await fetch(`${API}/api/status`);
        const data = await res.json();

        document.getElementById('statTweets').textContent = data.tweets_posted;
        document.getElementById('statRef').textContent = data.ref_code;

        const time = new Date(data.server_time + 'Z');
        document.getElementById('statTime').textContent = time.toLocaleTimeString();

        isPaused = data.paused;
        updatePauseButton();
        updateBotStatus();

        // Upcoming jobs
        const jobList = document.getElementById('jobList');
        if (data.upcoming_jobs && data.upcoming_jobs.length > 0) {
            jobList.innerHTML = data.upcoming_jobs.map(job => {
                const next = job.next_run ? new Date(job.next_run).toLocaleTimeString() : '—';
                const icon = job.id.includes('trending') ? '🔥' :
                             job.id.includes('portfolio') ? '📈' : '🚀';
                return `<div class="job-item">
                    <span class="job-name">${icon} ${job.id}</span>
                    <span class="job-time">${next}</span>
                </div>`;
            }).join('');
        } else {
            jobList.innerHTML = '<div class="loading-text">No scheduled jobs</div>';
        }

        // Recent tweets on overview
        loadRecentTweets();
    } catch (e) {
        console.error('Failed to load status:', e);
    }
}

function updatePauseButton() {
    const btn = document.getElementById('btnPauseResume');
    if (isPaused) {
        btn.textContent = '▶ Resume';
        btn.className = 'btn btn-success';
        document.getElementById('statStatus').textContent = '⏸ Paused';
        document.getElementById('statStatus').style.color = 'var(--orange)';
    } else {
        btn.textContent = '⏸ Pause';
        btn.className = 'btn btn-danger';
        document.getElementById('statStatus').textContent = '🟢 Running';
        document.getElementById('statStatus').style.color = 'var(--green)';
    }
}

function updateBotStatus() {
    const statusEl = document.getElementById('botStatus');
    const dot = statusEl.querySelector('.status-dot');
    const label = statusEl.querySelector('span:last-child');
    if (isPaused) {
        dot.className = 'status-dot paused';
        label.textContent = 'Bot Paused';
    } else {
        dot.className = 'status-dot running';
        label.textContent = 'Bot Running';
    }
}

async function togglePause() {
    const endpoint = isPaused ? '/api/bot/resume' : '/api/bot/pause';
    try {
        await fetch(`${API}${endpoint}`, { method: 'POST' });
        isPaused = !isPaused;
        updatePauseButton();
        updateBotStatus();
        showToast(isPaused ? 'Bot paused' : 'Bot resumed', 'success');
    } catch (e) {
        showToast('Failed to toggle bot', 'error');
    }
}

// ─── Settings ─────────────────────────────────────
async function loadSettings() {
    try {
        const res = await fetch(`${API}/api/settings`);
        currentSettings = await res.json();

        document.getElementById('settingAggr').value = currentSettings.aggressiveness || 5;
        document.getElementById('settingStyle').value = currentSettings.style || 'balanced';
        document.getElementById('settingTrending').checked = currentSettings.trending_enabled !== false;
        document.getElementById('settingPortfolio').checked = currentSettings.portfolio_enabled !== false;
        document.getElementById('settingViral').checked = currentSettings.viral_enabled !== false;
        document.getElementById('settingAutoReply').checked = currentSettings.auto_reply_enabled !== false;

        const sched = currentSettings.schedule || {};
        document.getElementById('scheduleTrending').value = (sched.trending || [6,12,20]).join(', ');
        document.getElementById('schedulePortfolio').value = (sched.portfolio || [10,16]).join(', ');
        document.getElementById('scheduleViral').value = (sched.viral || [8,14,18]).join(', ');

        updateAggrLabel();
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

async function saveSettings() {
    const parseHours = (str) => str.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));

    const settings = {
        aggressiveness: parseInt(document.getElementById('settingAggr').value),
        style: document.getElementById('settingStyle').value,
        trending_enabled: document.getElementById('settingTrending').checked,
        portfolio_enabled: document.getElementById('settingPortfolio').checked,
        viral_enabled: document.getElementById('settingViral').checked,
        auto_reply_enabled: document.getElementById('settingAutoReply').checked,
        schedule: {
            trending: parseHours(document.getElementById('scheduleTrending').value),
            portfolio: parseHours(document.getElementById('schedulePortfolio').value),
            viral: parseHours(document.getElementById('scheduleViral').value),
        }
    };

    try {
        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        if (res.ok) {
            showToast('Settings saved!', 'success');
            currentSettings = settings;
        } else {
            showToast('Failed to save settings', 'error');
        }
    } catch (e) {
        showToast('Network error', 'error');
    }
}

function updateAggrLabel() {
    const val = parseInt(document.getElementById('settingAggr').value);
    const labels = {
        1: '1 — Very Safe', 2: '2 — Conservative', 3: '3 — Cautious',
        4: '4 — Measured', 5: '5 — Balanced', 6: '6 — Bold',
        7: '7 — Aggressive', 8: '8 — Very Bold', 9: '9 — Savage',
        10: '10 — Full Degen'
    };
    document.getElementById('aggrLabel').textContent = labels[val] || val;
}

// ─── Tweets ───────────────────────────────────────
async function loadTweets() {
    try {
        const res = await fetch(`${API}/api/tweets`);
        const tweets = await res.json();
        renderTweetList(tweets, 'tweetHistory');
    } catch (e) {
        console.error('Failed to load tweets:', e);
    }
}

async function loadRecentTweets() {
    try {
        const res = await fetch(`${API}/api/tweets`);
        const tweets = await res.json();
        renderTweetList(tweets.slice(0, 5), 'recentTweets');
    } catch (e) {}
}

function renderTweetList(tweets, containerId) {
    const container = document.getElementById(containerId);
    if (!tweets || tweets.length === 0) {
        container.innerHTML = '<div class="empty-state">No tweets yet. The bot will start posting on schedule.</div>';
        return;
    }

    container.innerHTML = tweets.map(t => {
        const time = t.timestamp ? new Date(t.timestamp + 'Z').toLocaleString() : '';
        const moduleClass = t.module || 'manual';
        const tweetUrl = t.id ? `https://x.com/girlmathtorich/status/${t.id}` : '';

        return `<div class="tweet-item">
            <div class="tweet-header">
                <span class="tweet-module ${moduleClass}">${moduleClass}</span>
                <span class="tweet-time">${time}</span>
            </div>
            <div class="tweet-text">${escapeHtml(t.text || '')}</div>
            ${tweetUrl ? `<div class="tweet-id"><a href="${tweetUrl}" target="_blank">View on X →</a></div>` : ''}
        </div>`;
    }).join('');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Compose ──────────────────────────────────────
async function generatePreview() {
    const module = document.getElementById('previewModule').value;
    const box = document.getElementById('previewBox');
    const text = document.getElementById('previewText');
    const chars = document.getElementById('previewChars');

    text.textContent = 'Generating...';
    box.style.display = 'block';

    try {
        const res = await fetch(`${API}/api/tweet/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ module }),
        });
        const data = await res.json();
        text.textContent = data.tweet;
        chars.textContent = `${data.chars}/280 chars`;
    } catch (e) {
        text.textContent = 'Error generating tweet';
    }
}

async function postPreview() {
    const text = document.getElementById('previewText').textContent;
    const module = document.getElementById('previewModule').value;
    if (!text || text === 'Generating...' || text === 'Error generating tweet') return;

    try {
        const res = await fetch(`${API}/api/tweet/post`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, module }),
        });
        const data = await res.json();
        if (data.status === 'posted') {
            showToast('Tweet posted! + Ref reply ✅', 'success');
            document.getElementById('previewBox').style.display = 'none';
            loadStatus();
        } else {
            showToast(data.error || 'Failed to post', 'error');
        }
    } catch (e) {
        showToast('Network error', 'error');
    }
}

async function postManual() {
    const text = document.getElementById('manualText').value.trim();
    if (!text) {
        showToast('Write something first!', 'error');
        return;
    }

    try {
        const res = await fetch(`${API}/api/tweet/post`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, module: 'manual' }),
        });
        const data = await res.json();
        if (data.status === 'posted') {
            showToast('Tweet posted! + Ref reply ✅', 'success');
            document.getElementById('manualText').value = '';
            document.getElementById('manualChars').textContent = '0';
            loadStatus();
        } else {
            showToast(data.error || 'Failed to post', 'error');
        }
    } catch (e) {
        showToast('Network error', 'error');
    }
}

// ─── Quick Actions ────────────────────────────────
async function runModule(module) {
    try {
        const res = await fetch(`${API}/api/tweet/run-module`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ module }),
        });
        const data = await res.json();
        showToast(`${module} module triggered!`, 'success');
    } catch (e) {
        showToast('Failed to trigger module', 'error');
    }
}

// ─── Helpers ──────────────────────────────────────
function setupCharCount() {
    const ta = document.getElementById('manualText');
    if (ta) {
        ta.addEventListener('input', () => {
            document.getElementById('manualChars').textContent = ta.value.length;
        });
    }
}

function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = `toast show ${type}`;
    setTimeout(() => toast.className = 'toast', 3000);
}
