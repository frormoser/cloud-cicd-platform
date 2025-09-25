// Minimal frontend for the GitHub profile demo.
// Written to be dependency-free and small; uses Chart.js from CDN for charts.

const $ = (sel) => document.querySelector(sel);

async function fetchProfile(username) {
  // Try backend API first (preferred for rate-limited, token-enabled usage)
  const apiUrl = `/api/profile/${encodeURIComponent(username)}`;
  try {
    const res = await fetch(apiUrl);
    if (res.ok) return res.json();
    // If API not available (e.g., running purely static on Netlify), fallthrough
  } catch (err) {
    // ignore and try direct GitHub fallback
    console.warn('Backend API not reachable, falling back to direct GitHub API', err);
  }

  // Fallback: call GitHub public endpoints directly. This is unauthenticated and
  // should be used only for demo/static hosting. Rate limits will apply.
  const gh = 'https://api.github.com';
  const userResp = await fetch(`${gh}/users/${encodeURIComponent(username)}`);
  if (!userResp.ok) throw new Error(`GitHub user fetch failed: ${userResp.status}`);
  const user = await userResp.json();

  const reposResp = await fetch(`${gh}/users/${encodeURIComponent(username)}/repos?per_page=100`);
  const repos = reposResp.ok ? await reposResp.json() : [];

  // Helper: normalize language labels for nicer display (HCL, Dockerfile, etc.)
  function normalizeLang(raw) {
    if (!raw) return 'Unknown';
    const s = String(raw).trim();
    if (!s) return 'Unknown';
    const lower = s.toLowerCase();
    const map = { 'hcl': 'HCL', 'dockerfile': 'Dockerfile' };
    if (map[lower]) return map[lower];
    // Preserve common capitalization (e.g., 'JavaScript' or 'Go')
    return s;
  }

  // Sort repositories by most recent push (newest first). Use pushed_at then updated_at.
  function repoTimeKey(r) {
    const t = r.pushed_at || r.updated_at || null;
    return t ? new Date(t).getTime() : 0;
  }

  const sortedByRecent = (repos || []).slice().sort((a, b) => repoTimeKey(b) - repoTimeKey(a));

  // Convert into the same shape as backend API for rendering simplicity
  const total_stars = (repos || []).reduce((s, r) => s + (r.stargazers_count || 0), 0);
  const languages = {};
  for (const r of (repos || [])) {
    const raw = r.language || null;
    const l = normalizeLang(raw);
    languages[l] = (languages[l] || 0) + 1;
  }

  return {
    ok: true,
    profile: {
      username: user.login,
      name: user.name,
      bio: user.bio,
      avatar_url: user.avatar_url,
      html_url: user.html_url,
      followers: user.followers,
      following: user.following,
      public_repos: user.public_repos,
      total_stars,
      repo_count: (repos || []).length,
      // For the UI we show the most recently updated/pushed repos first so a
      // candidate's latest work is visible immediately in the demo.
      top_repos: sortedByRecent.slice(0, 6).map((r) => ({
        name: r.name,
        html_url: r.html_url,
        stars: r.stargazers_count,
        language: normalizeLang(r.language),
      })),
      languages,
      recent_repo_updates_90d: 0,
    },
  };
}

function animateCount(el, target) {
  const start = 0;
  const duration = 700;
  const startTime = performance.now();

  function tick(now) {
    const t = Math.min(1, (now - startTime) / duration);
    const value = Math.floor(start + (target - start) * t);
    el.textContent = value;
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function renderProfile(data) {
  const p = data.profile;
  // Provide a fallback avatar if none available
  $('#avatar').src = p.avatar_url || 'https://avatars.githubusercontent.com/u/9919?s=200&v=4';
  $('#name').textContent = p.name || p.username;
  $('#profile-link').href = p.html_url;
  $('#bio').textContent = p.bio || '';

  animateCount($('#followers'), p.followers || 0);
  animateCount($('#repos'), p.public_repos || 0);
  animateCount($('#stars'), p.total_stars || 0);

  const ul = $('#top-repos');
  ul.innerHTML = '';
  (p.top_repos || []).forEach(r => {
    const li = document.createElement('li');
    li.innerHTML = `<a href="${r.html_url}" target="_blank">${r.name}</a> <span class="meta">★ ${r.stars} • ${r.language || '—'}</span>`;
    ul.appendChild(li);
  });

  // Languages chart
  const langs = p.languages || {};
  const labels = Object.keys(langs);
  const values = Object.values(langs);
  const ctx = document.getElementById('langChart').getContext('2d');
  if (window._langChart) window._langChart.destroy();
  window._langChart = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: labels.map((_,i)=>`hsl(${i*40%360} 70% 60%)`) }] },
    options: { plugins: { legend: { position: 'bottom' } } }
  });

  $('#profile').classList.remove('hidden');
}

document.getElementById('fetch').addEventListener('click', async () => {
  const username = $('#username').value.trim();
  if (!username) return alert('Please enter a username');
  try {
    const payload = await fetchProfile(username);
    if (!payload.ok) throw new Error(payload.error || 'Unknown');
    renderProfile(payload);
  } catch (err) {
    alert('Error: ' + err.message);
    console.error(err);
  }
});

// Allow pressing enter in the input
$('#username').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('#fetch').click(); });
