const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

let samples = [];
let inboxEmails = [];
let gmail = { configured: false, connected: false };
let activeTone = 'Friendly';
let lastSubject = '';
let lastBody = '';

const priorityPalette = {
  Critical: { className: 'critical', tone: 'danger' },
  High: { className: 'high', tone: 'danger' },
  Medium: { className: 'medium', tone: 'warning' },
  Low: { className: 'low', tone: 'success' }
};

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[char]));
}

function setTheme(isDark) {
  document.body.classList.toggle('dark-mode', isDark);
  const themeIcon = $('.theme-icon');
  if (themeIcon) {
    themeIcon.textContent = isDark ? '☀' : '☾';
  }
}

function initTheme() {
  const saved = localStorage.getItem('mailmind-theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const shouldDark = saved ? saved === 'dark' : prefersDark;
  setTheme(shouldDark);
}

function setAnalyzeLoading(isLoading) {
  const button = $('#analyze');
  if (!button) return;

  button.classList.toggle('is-loading', isLoading);
  const label = button.querySelector('.btn-label');
  if (label) label.textContent = isLoading ? 'Analyzing…' : 'Analyze email';

  const arrow = button.querySelector('.btn-arrow');
  if (arrow) arrow.style.display = isLoading ? 'none' : 'inline';

  if (isLoading) {
    const spinner = document.createElement('span');
    spinner.className = 'spinner';
    spinner.setAttribute('aria-hidden', 'true');
    button.insertBefore(spinner, button.firstChild);
  } else {
    const spinner = button.querySelector('.spinner');
    if (spinner) spinner.remove();
  }
}

function renderEmptyState() {
  $('#results').innerHTML = `
    <div class="empty-state">
      <div class="empty-mark">✦</div>
      <div>
        <h2 class="empty-title">Your email intelligence<br />will appear here.</h2>
      </div>
      <p class="empty-copy">Paste an email and let MailMind find the signal in the noise.</p>
      <div class="skeleton-grid" aria-hidden="true">
        <div class="skeleton-card">
          <div class="skeleton-line wide"></div>
          <div class="skeleton-line mid"></div>
          <div class="skeleton-line short"></div>
        </div>
        <div class="skeleton-card">
          <div class="skeleton-line wide"></div>
          <div class="skeleton-line mid"></div>
          <div class="skeleton-line short"></div>
        </div>
      </div>
    </div>
  `;
}

function showToast(message = 'Copied ✓') {
  const toast = $('#copyToast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 1200);
}

function safeList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  return [String(value).trim()].filter(Boolean);
}

function pickPriorityMeta(priority) {
  const normalized = priority || 'Medium';
  const meta = priorityPalette[normalized] || priorityPalette.Medium;
  return { label: normalized, className: meta.className, tone: meta.tone };
}

function renderReasonBullets(data) {
  const items = [
    data.priority_reason || 'This message requires attention and should be reviewed carefully.',
    data.deadline ? `Deadline: ${data.deadline}` : 'No explicit deadline was included in the message.',
    data.response_required ? 'A response is expected.' : 'No direct response is required right now.',
    data.summary || 'The email carries a clear action or signal worth reviewing.'
  ];

  const icons = ['⚑', '✓', '⏱', '✦'];
  return items.slice(0, 4).map((item, index) => `
    <li>
      <span class="reason-icon" aria-hidden="true">${icons[index % icons.length]}</span>
      <span>${escapeHTML(item)}</span>
    </li>
  `).join('');
}

function renderDetailItems(data) {
  const items = [
    { label: 'Deadline', value: data.deadline || 'No deadline' },
    { label: 'Time', value: safeList(data.dates_times).slice(0, 2).join(', ') || 'Not specified' },
    { label: 'Action required', value: data.response_required ? 'Yes' : 'No' },
    { label: 'Sender', value: data.sender || 'Unknown sender' },
    { label: 'Category', value: data.category || 'Uncategorized' }
  ];

  return items.map((item) => `
    <div class="detail-item">
      <span class="detail-label">${escapeHTML(item.label)}</span>
      <span class="detail-value">${escapeHTML(item.value)}</span>
    </div>
  `).join('');
}

function applyToneToReply(value, tone) {
  const text = String(value || '').trim();
  if (!text) return '';

  switch (tone) {
    case 'Formal':
      return text
        .replace(/^hi\s+/i, 'Dear team,\n\n')
        .replace(/^hello\s+/i, 'Dear team,\n\n')
        .replace(/\n\nthank you/i, '\n\nThank you');
    case 'Short':
      return text
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .slice(0, 3)
        .join('\n\n');
    case 'Friendly':
    default:
      return text;
  }
}

function renderResult(data) {
  const priorityMeta = pickPriorityMeta(data.priority);
  const confidenceValue = Number(data.confidence ?? 0);
  const replyText = applyToneToReply(data.reply_draft || 'Thanks for the update. I’ll review this shortly.', activeTone);

  $('#results').innerHTML = `
    <div class="result-shell">
      <article class="result-card priority-card">
        <div class="result-header">
          <span class="key-label">Priority</span>
          <span class="source-pill">${escapeHTML(data.source || 'Demo Intelligence')}</span>
        </div>
        <div class="priority-row">
          <div class="priority-badge" data-level="${escapeHTML(priorityMeta.label)}">
            <span class="priority-dot" aria-hidden="true"></span>
            <span class="priority-value">${escapeHTML(priorityMeta.label)}</span>
          </div>

          <div class="confidence-box">
            <div class="confidence-meta">
              <span>Confidence</span>
              <strong>${confidenceValue}%</strong>
            </div>
            <div class="confidence-track" aria-hidden="true">
              <span class="confidence-fill" style="width: ${confidenceValue}%;"></span>
            </div>
          </div>
        </div>
      </article>

      <article class="result-card reasons-card">
        <div class="result-header compact">
          <span class="key-label">Why this priority</span>
        </div>
        <ul class="reason-list">${renderReasonBullets(data)}</ul>
      </article>

      <article class="result-card details-card">
        <div class="result-header compact">
          <span class="key-label">Key details</span>
        </div>
        <div class="detail-grid">${renderDetailItems({ ...data, sender: data.sender || 'Unknown sender' })}</div>
      </article>

      <article class="result-card reply-card">
        <div class="reply-topbar">
          <span class="key-label">Suggested reply</span>
          <div class="reply-actions">
            <button class="mini-btn copy-btn" type="button">Copy</button>
            <button class="mini-btn" type="button" data-action="regenerate">Regenerate</button>
          </div>
        </div>

        <div class="tone-group" role="group" aria-label="Reply tone">
          <button type="button" class="tone-btn ${activeTone === 'Friendly' ? 'is-active' : ''}" data-tone="Friendly">Friendly</button>
          <button type="button" class="tone-btn ${activeTone === 'Formal' ? 'is-active' : ''}" data-tone="Formal">Formal</button>
          <button type="button" class="tone-btn ${activeTone === 'Short' ? 'is-active' : ''}" data-tone="Short">Short</button>
        </div>

        <div class="reply-body" tabindex="0">${escapeHTML(replyText)}</div>
      </article>
    </div>
  `;

  const replyBody = $('.reply-body');
  if (replyBody) replyBody.textContent = applyToneToReply(data.reply_draft || '', activeTone);

  $('.copy-btn')?.addEventListener('click', async () => {
    const text = applyToneToReply(data.reply_draft || '', activeTone);
    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied ✓');
    } catch (error) {
      showToast('Copy failed');
    }
  });

  $('[data-action="regenerate"]')?.addEventListener('click', async () => {
    if (!lastSubject || !lastBody) return;
    setAnalyzeLoading(true);
    try {
      const fresh = await analyzeEmail(lastSubject, lastBody);
      renderResult(fresh);
    } finally {
      setAnalyzeLoading(false);
    }
  });

  $$('.tone-btn').forEach((button) => {
    button.addEventListener('click', () => {
      activeTone = button.dataset.tone || 'Friendly';
      const freshText = applyToneToReply(data.reply_draft || '', activeTone);
      const replyBodyNode = $('.reply-body');
      if (replyBodyNode) replyBodyNode.textContent = freshText;
      $$('.tone-btn').forEach((node) => node.classList.toggle('is-active', node.dataset.tone === activeTone));
    });
  });
}

function renderSamples() {
  if (!samples.length) {
    $('#sampleMenu').innerHTML = '<span class="sample-chip">Loading…</span>';
    return;
  }

  $('#sampleMenu').innerHTML = samples.map((sample, index) => `
    <button type="button" class="sample-chip" data-sample-index="${index}">${escapeHTML(sample.name || sample.subject || 'Sample email')}</button>
  `).join('');

  $('#sampleMenu').querySelectorAll('.sample-chip').forEach((button) => {
    button.addEventListener('click', () => {
      const index = Number(button.dataset.sampleIndex);
      const sample = samples[index];
      if (!sample) return;
      $('#subject').value = sample.subject || '';
      $('#body').value = sample.body || '';
      $$('.sample-chip').forEach((chip) => chip.classList.toggle('active', chip === button));
    });
  });
}

function renderInboxItems() {
  if (!inboxEmails.length) {
    $('#sampleMenu').innerHTML = '<span class="sample-chip">No recent messages</span>';
    return;
  }

  $('#sampleMenu').innerHTML = inboxEmails.map((mail, index) => `
    <button type="button" class="sample-chip" data-mail-index="${index}">${escapeHTML(mail.subject || '(No subject)')}</button>
  `).join('');

  $('#sampleMenu').querySelectorAll('.sample-chip').forEach((button) => {
    button.addEventListener('click', async () => {
      const mailIndex = Number(button.dataset.mailIndex);
      const mail = inboxEmails[mailIndex];
      if (!mail) return;
      $('#subject').value = mail.subject || '';
      $('#body').value = mail.body || '';
      lastSubject = $('#subject').value.trim();
      lastBody = $('#body').value.trim();
      setAnalyzeLoading(true);
      try {
        const result = await analyzeEmail(lastSubject, lastBody);
        renderResult(result);
      } finally {
        setAnalyzeLoading(false);
      }
    });
  });
}

async function loadSamples() {
  try {
    const response = await fetch('/api/samples');
    samples = await response.json();
    renderSamples();
  } catch (error) {
    $('#sampleMenu').innerHTML = '<span class="sample-chip">Sample list unavailable</span>';
  }
}

async function gmailStatus() {
  try {
    gmail = await fetch('/api/gmail/status').then((r) => r.json());
  } catch (error) {
    gmail = { configured: false, connected: false };
  }

  const gmailBtn = $('#gmailBtn');
  const gmailSwitchBtn = $('#gmailSwitchBtn');
  if (gmailBtn) {
    gmailBtn.textContent = gmail.connected ? 'Fetch inbox' : 'Connect Gmail';
  }
  if (gmailSwitchBtn) {
    gmailSwitchBtn.hidden = !gmail.connected;
  }
}

async function fetchInbox() {
  const gmailBtn = $('#gmailBtn');
  if (!gmailBtn) return;

  if (!gmail.connected) {
    window.location.href = '/auth/gmail/connect';
    return;
  }

  gmailBtn.disabled = true;
  gmailBtn.textContent = 'Fetching…';

  try {
    const response = await fetch('/api/gmail/emails?limit=5');
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to fetch Gmail messages.');
    inboxEmails = Array.isArray(data) ? data : [];
    renderInboxItems();
  } catch (error) {
    alert(error.message || 'Unable to fetch your inbox right now.');
  } finally {
    gmailBtn.disabled = false;
    gmailBtn.textContent = 'Fetch inbox';
  }
}

async function analyzeEmail(subject, body) {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, body })
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Unable to analyze this email.');
  return data;
}

$('#gmailBtn').addEventListener('click', fetchInbox);
$('#gmailSwitchBtn').addEventListener('click', () => {
  window.location.href = '/auth/gmail/connect';
});
$('#themeToggle').addEventListener('click', () => {
  const currentlyDark = document.body.classList.contains('dark-mode');
  const nextDark = !currentlyDark;
  setTheme(nextDark);
  localStorage.setItem('mailmind-theme', nextDark ? 'dark' : 'light');
});

$('#analyze').addEventListener('click', async () => {
  const subject = $('#subject').value.trim();
  const body = $('#body').value.trim();

  if (!subject || !body) {
    $('#results').innerHTML = `
      <div class="result-card" style="padding: 18px;">
        <p class="key-label">Analysis needed</p>
        <p style="line-height: 1.6; color: var(--ink-soft);">Please add both a subject and email content before analyzing.</p>
      </div>
    `;
    return;
  }

  lastSubject = subject;
  lastBody = body;
  setAnalyzeLoading(true);

  try {
    const result = await analyzeEmail(subject, body);
    renderResult(result);
  } catch (error) {
    $('#results').innerHTML = `
      <div class="result-card" style="padding: 18px;">
        <p class="key-label">Analysis unavailable</p>
        <p style="line-height: 1.6; color: var(--ink-soft);">${escapeHTML(error.message || 'Something went wrong.')}</p>
      </div>
    `;
  } finally {
    setAnalyzeLoading(false);
  }
});

initTheme();
renderEmptyState();
loadSamples();
gmailStatus();