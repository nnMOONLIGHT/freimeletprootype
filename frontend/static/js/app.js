const API = '';
const state = { user: null, reg: { role: 'school', directions: [] } };

const directions = [
  { id: 'design', name: 'Дизайн и графика' },
  { id: '3d', name: '3D и цифровое' },
  { id: 'fashion', name: 'Fashion' },
  { id: 'craft', name: 'Ремесло' },
  { id: 'media', name: 'Медиа' },
  { id: 'text', name: 'Тексты и музыка' },
];

const roleHints = {
  school: 'Если тебе меньше 18 — после регистрации родителю нужно загрузить согласие. До этого доступен просмотр.',
  student: 'Студентам 18+ полный доступ открывается сразу после регистрации.',
  parent: 'Кабинет для контроля активности ребёнка и управления согласиями.',
  partner: 'Регистрация партнёра — заявка на верификацию, доступ к стажировкам через 3 дня.',
};

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: opts.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...opts,
    body: opts.body instanceof FormData ? opts.body : opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Ошибка сервера');
  return data;
}

function $(id) { return document.getElementById(id); }

function toast(msg) {
  const t = $('toast');
  $('toastText').textContent = msg;
  t.classList.add('show');
  clearTimeout(toast._tm);
  toast._tm = setTimeout(() => t.classList.remove('show'), 2600);
}

function show(screen) {
  ['loginScreen', 'app'].forEach(id => $(id).classList.add('hide'));
  $(screen).classList.remove('hide');
  if (screen === 'app') $('app').style.display = 'grid';
}

function go(view) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  $(view).classList.add('active');
  document.querySelectorAll('[data-view]').forEach(b =>
    b.classList.toggle('active', b.dataset.view === view));
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (view === 'videos') loadVideos();
  if (view === 'works') loadWorks();
}

function selectRole(el) {
  document.querySelectorAll('.role').forEach(r => r.classList.remove('sel'));
  el.classList.add('sel');
  state.reg.role = el.dataset.role;
  $('roleNotice').textContent = roleHints[state.reg.role];
}

function regStep(n) {
  if (n === 3 && !validateStep1()) return;
  [1, 2, 3, 99].forEach(i => {
    const el = $('regStep' + i);
    if (el) el.classList.toggle('hide', i !== n);
  });
  if (n <= 3) {
    document.querySelectorAll('.step-dots i').forEach((d, i) => d.classList.toggle('on', i < n));
  }
}

function focusRegister() {
  regStep(1);
  document.querySelector('.login-box')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function validateStep1() {
  const f = {
    full_name: $('regName').value.trim(),
    age: $('regAge').value,
    region: $('regRegion').value.trim(),
    email: $('regEmail').value.trim(),
    password: $('regPass').value,
  };
  if (!f.full_name || !f.age || !f.region || !f.email || !f.password) {
    toast('Заполни все поля');
    return null;
  }
  if (+f.age < 14) { toast('Минимальный возраст — 14 лет'); return null; }
  Object.assign(state.reg, f);
  return f;
}

async function downloadConsent() {
  const { text } = await api('/api/consent-template');
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'soglasie-freimelet.txt';
  a.click();
}

function buildDirPick() {
  const box = $('dirPick');
  box.innerHTML = '';
  directions.forEach(d => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'dir-opt';
    b.textContent = d.name;
    b.onclick = () => {
      b.classList.toggle('on');
      if (b.classList.contains('on')) state.reg.directions.push(d.id);
      else state.reg.directions = state.reg.directions.filter(x => x !== d.id);
    };
    box.appendChild(b);
  });
}

async function submitRegister() {
  if (!validateStep1()) return;
  if (+state.reg.age < 18 && !$('consentCheck').checked) {
    toast('Нужно подтвердить согласие родителя');
    return;
  }
  const btn = $('regSubmit');
  btn.disabled = true;
  try {
    const { user } = await api('/api/register', { method: 'POST', body: state.reg });
    state.user = user;
    enterApp();
    toast('Добро пожаловать на Фреймлёт!');
  } catch (e) {
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
}

async function doLogin() {
  try {
    const { user } = await api('/api/login', {
      method: 'POST',
      body: { email: $('loginEmail').value, password: $('loginPass').value },
    });
    state.user = user;
    enterApp();
    toast('С возвращением!');
  } catch (e) {
    toast(e.message);
  }
}

async function doLogout() {
  await api('/api/logout', { method: 'POST' });
  state.user = null;
  $('app').style.display = 'none';
  show('loginScreen');
  regStep(1);
}

async function enterApp() {
  show('app');
  syncProfile();
  syncConsentUI();
  loadWorks();
  try {
    const { activities } = await api('/api/me');
    if (activities?.length) renderActivities(activities);
  } catch (_) {}
}

function syncProfile() {
  const u = state.user;
  if (!u) return;
  const initial = u.full_name.charAt(0);
  document.querySelectorAll('.u-initial').forEach(el => el.textContent = initial);
  document.querySelectorAll('.u-name').forEach(el => el.textContent = u.full_name.split(' ')[0]);
  document.querySelectorAll('.u-full').forEach(el => el.textContent = u.full_name);
  document.querySelectorAll('.u-age-dir').forEach(el =>
    el.textContent = `${u.age} лет · ${u.directions.length ? u.directions.join(', ') : 'направления не выбраны'}`);
  document.querySelectorAll('.u-region').forEach(el => el.textContent = u.region);
  $('heroPoints').textContent = u.points;
  $('heroPct').textContent = Math.min(99, Math.round(u.points / 10)) + '%';
  $('profPoints').textContent = u.points;
  $('profWorks').textContent = u.works_count;
  $('profChallenges').textContent = u.challenges_count;
}

function syncConsentUI() {
  const u = state.user;
  if (!u) return;
  const pending = u.age < 18 && u.parent_consent === 'pending';
  const badge = $('sideStatusBadge');
  badge.className = 'badge ' + (pending ? 'warning' : 'success');
  badge.textContent = pending ? 'Ожидается согласие' : 'Доступ открыт';
  $('sideStatusText').textContent = pending
    ? 'Загрузите подписанное согласие родителя для публикации.'
    : 'Публикация, продажа и стажировки доступны.';
  const card = $('consentCard');
  if (card) {
    card.className = pending ? 'notice warn' : 'notice';
    card.innerHTML = pending
      ? `<span>⚠</span><div><b>Согласие родителя</b><br><span class="muted">Скачай шаблон, подпиши с родителем и <a href="#" onclick="confirmConsent(event)">подтверди загрузку →</a></span></div>`
      : `<span>✓</span><div><b>Согласие получено</b><br><span class="muted">Полный доступ активен.</span></div>`;
  }
}

async function confirmConsent(e) {
  e.preventDefault();
  await api('/api/consent', { method: 'POST', body: { status: 'confirmed' } });
  state.user.parent_consent = 'confirmed';
  syncConsentUI();
  toast('Согласие подтверждено');
}

function needConsent() {
  if (state.user?.age < 18 && state.user?.parent_consent === 'pending') {
    toast('Нужно согласие родителя');
    return true;
  }
  return false;
}

async function loadWorks() {
  try {
    const { works } = await api('/api/works');
    const box = $('worksGrid');
    if (!box) return;
    box.innerHTML = works.map(w => `
      <article class="card wcard">
        <div class="work-art" style="background:linear-gradient(135deg,var(--lav-soft),var(--sky-soft))">
          <span style="font-size:28px">🎨</span>
        </div>
        <div class="work-body">
          <b>${esc(w.title)}</b>
          <div class="muted">${esc(w.region)} · ${esc(w.direction)}</div>
          <div class="row"><span class="faint">${w.views} просмотров</span><span class="points">+${w.points}</span></div>
        </div>
      </article>`).join('');
  } catch (_) {}
}

async function loadVideos(dir = 'all') {
  const { videos } = await api('/api/videos?direction=' + dir);
  $('videoGrid').innerHTML = videos.map(v => `
    <article class="card video-card">
      <div class="video-wrap">
        <iframe src="${esc(v.embed_url)}" loading="lazy" allowfullscreen title="${esc(v.title)}"></iframe>
      </div>
      <div class="video-body">
        <b>${esc(v.title)}</b>
        <div class="video-meta">
          <span class="platform-tag">${esc(v.platform)}</span>
          <span>${esc(v.author)}</span>
          <span>${fmtNum(v.views)} просм.</span>
          <span>♥ ${fmtNum(v.likes)}</span>
        </div>
      </div>
    </article>`).join('');
}

function filterVideos(el, dir) {
  document.querySelectorAll('#videoFilters .chip').forEach(c => c.classList.remove('on'));
  el.classList.add('on');
  loadVideos(dir);
}

function openUpload() {
  if (needConsent()) return;
  $('uploadModal').classList.add('open');
}

function closeModal(id) { $(id).classList.remove('open'); }

async function submitWork() {
  const title = $('workTitle').value.trim();
  const direction = $('workDir').value;
  if (!title) { toast('Укажи название'); return; }
  try {
    await api('/api/works', { method: 'POST', body: { title, direction, description: $('workDesc').value } });
    closeModal('uploadModal');
    state.user.works_count++;
    state.user.points += 10;
    syncProfile();
    loadWorks();
    toast('Работа отправлена на модерацию');
  } catch (e) { toast(e.message); }
}

function setupAiUpload() {
  const zone = $('aiDrop');
  const input = $('aiFile');
  zone.onclick = () => input.click();
  zone.ondragover = e => { e.preventDefault(); zone.classList.add('drag'); };
  zone.ondragleave = () => zone.classList.remove('drag');
  zone.ondrop = e => {
    e.preventDefault();
    zone.classList.remove('drag');
    if (e.dataTransfer.files[0]) analyzePhoto(e.dataTransfer.files[0]);
  };
  input.onchange = () => { if (input.files[0]) analyzePhoto(input.files[0]); };
}

async function analyzePhoto(file) {
  const fd = new FormData();
  fd.append('photo', file);
  $('aiResult').innerHTML = '<p class="muted">Анализируем изображение…</p>';
  try {
    const { result, preview } = await api('/api/ai/analyze', { method: 'POST', body: fd });
    renderAiResult(result, preview);
    toast('Анализ готов');
  } catch (e) {
    $('aiResult').innerHTML = `<p class="muted">${esc(e.message)}</p>`;
  }
}

function renderAiResult(r, preview) {
  const tags = r.visual_traits.map(t => `<span class="badge">${esc(t)}</span>`).join('');
  const styles = r.styles.map(s => `<span class="chip ${s.name === r.main_style ? 'on' : ''}">${esc(s.name)} ${s.score}%</span>`).join('');
  const hobbies = r.hobbies.map(h => `<span class="badge neutral">${esc(h.name)}</span>`).join('');
  const palette = r.palette.map(c => `<div class="swatch" style="background:${c.hex}" title="${c.hex}"></div>`).join('');
  const clothes = r.clothing.map(c => `<li>${esc(c)}</li>`).join('');

  $('aiResult').innerHTML = `
    ${preview ? `<img class="ai-preview" src="${preview}" alt="Загружено">` : ''}
    <h3>Результат анализа</h3>
    <div class="ai-tags">${tags}</div>
    <p class="muted">Типографика: <b>${esc(r.typography)}</b></p>
    <p>${esc(r.summary)}</p>
    <h4 style="margin:16px 0 8px;font-size:14px">Стили</h4>
    <div class="ai-tags">${styles}</div>
    <h4 style="margin:16px 0 8px;font-size:14px">Увлечения</h4>
    <div class="ai-tags">${hobbies}</div>
    <h4 style="margin:16px 0 8px;font-size:14px">Палитра</h4>
    <div class="palette-row">${palette}</div>
    <h4 style="margin:16px 0 8px;font-size:14px">Одежда и аксессуары</h4>
    <ul style="margin:0;padding-left:18px;line-height:1.7">${clothes}</ul>`;
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function fmtNum(n) {
  return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : n;
}

function openSheet() { $('sheetOverlay').classList.add('open'); }
function closeSheet() { $('sheetOverlay').classList.remove('open'); }
function sheetGo(v) { closeSheet(); go(v); }

function participate() { toast('Челлендж добавлен в план'); }
function applyIntern() { if (!needConsent()) toast('Отклик отправлен'); }

async function init() {
  buildDirPick();
  setupAiUpload();
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => go(b.dataset.view)));

  try {
    const { user, activities } = await api('/api/me');
    if (user) {
      state.user = user;
      if (activities?.length) renderActivities(activities);
      enterApp();
    }
  } catch (_) {}
}

function renderActivities(list) {
  const box = $('activityLog');
  if (!box) return;
  box.innerHTML = list.slice(0, 5).map(a =>
    `<div class="log-item"><div class="log-dot"></div><div><b>${esc(a.action)}</b><br><span class="faint">${a.points ? '+' + a.points + ' баллов' : ''}</span></div></div>`
  ).join('');
}

document.addEventListener('DOMContentLoaded', init);
