// 静的HTML版 CBT 練習アプリ
// 画像は ../server/static/pages/ を参照（リポジトリを clone してから開くこと）

const STATIC_BASE = '../server/static/';
const STORAGE_KEY = 'denki2-history';
const FLAG_KEY    = 'denki2-flags';

// ---- クイズ状態 ----
let currentQuestions = [];
let currentIndex = 0;
let answers  = {};   // { qIndex: selectedChoice (0-3) }
let lastSettings = {};
let wrongQuestionsForRetry = [];  // finishQuiz() 時点の間違い問題リスト
let tagCounts = {};  // { タグ名: 問題数 }

// ---- 配線図ビューア状態 ----
let dgScale = 1, dgPanX = 0, dgPanY = 0;
let dgDragging = false, dgDragX = 0, dgDragY = 0;
const DG_MIN = 0.5, DG_MAX = 4;

// ---- 画像ズームビューア状態 ----
let izScale = 1, izPanX = 0, izPanY = 0;
let izDragging = false, izDragX = 0, izDragY = 0;
const IZ_MIN = 0.5, IZ_MAX = 5;

// =============================================================
// 初期化
// =============================================================

document.addEventListener('DOMContentLoaded', () => {
  buildYearHalfOptions();
  tagCounts = buildTagOptions();
  showHistory();
  restoreInvert();
  setupDiagramEvents();
  setupImageZoomEvents();
  setupKeyEvents();

  document.getElementById('sel-tag').addEventListener('change', function() {
    const opt = this.options[this.selectedIndex];
    updateCountOptions(opt.value ? parseInt(opt.dataset.count) : 0);
  });
});

function buildYearHalfOptions() {
  const sel = document.getElementById('sel-year-half');
  const seen = new Set();
  for (const q of QUESTIONS) {
    const key = `${q.year}_${q.half}`;
    if (!seen.has(key)) {
      seen.add(key);
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = `${q.year}年 ${q.half === 'upper' ? '上期' : '下期'}`;
      sel.appendChild(opt);
    }
  }
  // 新しい年度が先になるよう options を並べ替え
  const opts = [...sel.options].slice(1).sort((a, b) => b.value.localeCompare(a.value));
  while (sel.options.length > 1) sel.remove(1);
  opts.forEach(o => sel.appendChild(o));
}

function buildTagOptions() {
  const counts = {};
  for (const q of QUESTIONS) {
    for (const tag of (q.tags || [])) {
      counts[tag] = (counts[tag] || 0) + 1;
    }
  }
  const sel = document.getElementById('sel-tag');
  for (const tag of Object.keys(counts).sort()) {
    const opt = new Option(`${tag}（${counts[tag]}問）`, tag);
    opt.dataset.count = counts[tag];
    sel.appendChild(opt);
  }
  return counts;
}

function updateCountOptions(maxCount) {
  const sel = document.getElementById('sel-count');
  sel.innerHTML = '';
  if (!maxCount) {
    for (const [v, label] of [[10,'10問'],[20,'20問'],[30,'30問'],[50,'50問（本番同等）']]) {
      sel.appendChild(new Option(label, v, false, v === 50));
    }
    return;
  }
  for (const n of [5, 10, 20, 30, 50]) {
    if (n < maxCount) sel.appendChild(new Option(`${n}問`, n));
  }
  sel.appendChild(new Option(`全${maxCount}問`, maxCount, true, true));
}

// =============================================================
// 白黒反転モード
// =============================================================

function toggleInvert() {
  document.documentElement.classList.toggle('inverted');
  const on = document.documentElement.classList.contains('inverted');
  localStorage.setItem('denki2-invert', on ? '1' : '');
  document.getElementById('btn-invert').textContent = on ? '反転解除' : '反転';
}

function restoreInvert() {
  if (localStorage.getItem('denki2-invert')) {
    document.documentElement.classList.add('inverted');
    document.getElementById('btn-invert').textContent = '反転解除';
  }
}

// =============================================================
// LocalStorage — 回答履歴
// =============================================================

function getHistory() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
  catch { return {}; }
}

function saveAnswerToHistory(questionId, isCorrect) {
  const data = getHistory();
  data[questionId] = isCorrect;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function getWrongIds() {
  const data = getHistory();
  return new Set(
    Object.entries(data).filter(([, v]) => v === false).map(([k]) => parseInt(k, 10))
  );
}

function showHistory() {
  const data = getHistory();
  const total = Object.keys(data).length;
  const wrong = Object.values(data).filter(v => !v).length;
  const card = document.getElementById('history-card');
  if (total === 0) { card.style.display = 'none'; return; }
  card.style.display = '';
  document.getElementById('history-list').innerHTML = `
    <p>挑戦済み: <strong>${total}</strong> 問 ／ 要復習: <strong>${wrong}</strong> 問</p>
    <button class="btn" onclick="clearHistory()" style="margin-top:0.5rem">履歴をリセット</button>
  `;
}

function clearHistory() {
  if (confirm('学習履歴をすべてクリアしますか？')) {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(FLAG_KEY);
    showHistory();
  }
}

// =============================================================
// LocalStorage — 後で見直すフラグ
// =============================================================

function getFlags() {
  try { return new Set(JSON.parse(localStorage.getItem(FLAG_KEY) || '[]')); }
  catch { return new Set(); }
}

function saveFlags(set) {
  localStorage.setItem(FLAG_KEY, JSON.stringify([...set]));
}

function toggleFlag() {
  const q = currentQuestions[currentIndex];
  const flags = getFlags();
  if (flags.has(q.id)) flags.delete(q.id);
  else flags.add(q.id);
  saveFlags(flags);
  updateFlagButton();
  renderNavDots();
}

function updateFlagButton() {
  const q = currentQuestions[currentIndex];
  const btn = document.getElementById('btn-flag');
  const flagged = getFlags().has(q.id);
  btn.textContent = flagged ? '★ 後で見直す' : '後で見直す';
  btn.classList.toggle('flagged', flagged);
}

// =============================================================
// クイズ開始 / 設定
// =============================================================

function startQuiz() {
  const yearHalf = document.getElementById('sel-year-half').value;
  const tag = document.getElementById('sel-tag').value;
  const count = Math.max(1, parseInt(document.getElementById('sel-count').value, 10) || 30);
  lastSettings = { yearHalf, tag, count };

  let pool = QUESTIONS.slice();
  if (yearHalf) {
    const [year, half] = yearHalf.split('_');
    pool = pool.filter(q => q.year === year && q.half === half);
  }
  if (tag) {
    pool = pool.filter(q => q.tags && q.tags.includes(tag));
  }
  if (pool.length === 0) { alert('該当する問題がありません。'); return; }

  shuffleArray(pool);
  currentQuestions = pool.slice(0, count);
  currentIndex = 0;
  answers = {};
  wrongQuestionsForRetry = [];

  showScreen('quiz');
  renderQuestion();
}

function restartQuiz() {
  if (lastSettings.yearHalf !== undefined) {
    document.getElementById('sel-year-half').value = lastSettings.yearHalf;
    const tagSel = document.getElementById('sel-tag');
    tagSel.value = lastSettings.tag || '';
    const tagOpt = tagSel.options[tagSel.selectedIndex];
    updateCountOptions(tagOpt.value ? parseInt(tagOpt.dataset.count) : 0);
    document.getElementById('sel-count').value = lastSettings.count;
  }
  startQuiz();
}

function retryWrongOnly() {
  console.log('[retryWrongOnly] wrongQuestionsForRetry:', wrongQuestionsForRetry.map(q => `${q.year}${q.half}問${q.number}`));
  if (wrongQuestionsForRetry.length === 0) return;
  currentQuestions = wrongQuestionsForRetry;
  wrongQuestionsForRetry = [];
  currentIndex = 0;
  answers = {};
  showScreen('quiz');
  renderQuestion();
}

function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}

// =============================================================
// 画面切り替え
// =============================================================

function showScreen(name) {
  document.getElementById('screen-setup').style.display = name === 'setup' ? '' : 'none';
  document.getElementById('screen-quiz').style.display  = name === 'quiz'  ? '' : 'none';
  document.getElementById('screen-result').style.display = name === 'result' ? '' : 'none';
}

function goSetup() {
  showScreen('setup');
  showHistory();
}

// =============================================================
// 問題表示
// =============================================================

function renderQuestion() {
  const q = currentQuestions[currentIndex];
  const total = currentQuestions.length;

  // ヘッダー
  document.getElementById('quiz-progress').textContent =
    `問題 ${currentIndex + 1} / ${total}　（${q.year}年 ${q.half === 'upper' ? '上期' : '下期'} 問${q.number}）`;

  // タグ
  const tagsEl = document.getElementById('quiz-tags');
  tagsEl.innerHTML = q.tags.map(t => `<span class="tag">${t}</span>`).join('');

  // 配線図ツール
  const haisenTools = document.getElementById('haisen-tools');
  const haisenNotes = document.getElementById('haisen-notes');
  if (q.is_haisen) {
    haisenTools.style.display = '';
    document.getElementById('diagram-img').src = STATIC_BASE + q.haisen_diagram_path;
    document.getElementById('haisen-notes-img').src = STATIC_BASE + q.haisen_notes_path;
    haisenNotes.style.display = 'none';  // 毎回閉じてリセット
  } else {
    haisenTools.style.display = 'none';
    haisenNotes.style.display = 'none';
  }

  // 問題画像
  const imgEl = document.getElementById('question-image');
  imgEl.src = STATIC_BASE + q.image_path;
  imgEl.alt = `問${q.number}`;
  document.getElementById('image-zoom-img').src = STATIC_BASE + q.image_path;
  document.getElementById('image-zoom-title').textContent =
    `問${q.number}（スクロール: 拡大縮小 / ドラッグ: 移動）`;

  // 問題文
  const textEl = document.getElementById('question-text');
  textEl.textContent = q.question;
  textEl.style.display = q.question.trim() ? '' : 'none';

  // 選択肢
  const labels = ['イ', 'ロ', 'ハ', 'ニ'];
  const choicesEl = document.getElementById('choices');
  choicesEl.innerHTML = '';
  q.choices.forEach((choice, i) => {
    const btn = document.createElement('button');
    btn.className = 'choice-btn';
    btn.dataset.index = i;
    btn.innerHTML = `<span class="choice-label">${labels[i]}</span>`;
    btn.addEventListener('click', () => selectAnswer(i));
    choicesEl.appendChild(btn);
  });

  // フィードバックリセット
  const fb = document.getElementById('feedback');
  fb.style.display = 'none';
  fb.className = 'feedback';

  // 既存回答を復元
  if (answers[currentIndex] !== undefined) {
    applyAnswerUI(answers[currentIndex], q.answer, true);
  }

  updateFlagButton();
  updateNavButtons();
  renderNavDots();
}

function selectAnswer(selected) {
  if (answers[currentIndex] !== undefined) return;
  const q = currentQuestions[currentIndex];
  answers[currentIndex] = selected;
  saveAnswerToHistory(q.id, selected === q.answer);
  applyAnswerUI(selected, q.answer, true);
  renderNavDots();
}

function applyAnswerUI(selected, correct, showFeedback) {
  const labels = ['イ', 'ロ', 'ハ', 'ニ'];
  document.querySelectorAll('.choice-btn').forEach((btn, i) => {
    btn.disabled = true;
    if (i === correct) btn.classList.add('correct');
    else if (i === selected && selected !== correct) btn.classList.add('wrong');
  });
  const btns = document.querySelectorAll('.choice-btn');
  if (btns[selected]) btns[selected].classList.add('selected');

  if (showFeedback) {
    const fb = document.getElementById('feedback');
    const ok = selected === correct;
    fb.textContent = ok ? '正解！' : `不正解。正解は ${labels[correct]} です。`;
    fb.className = `feedback ${ok ? 'correct' : 'wrong'}`;
    fb.style.display = '';
  }
}

// =============================================================
// ナビゲーション
// =============================================================

function navigate(dir) {
  const next = currentIndex + dir;
  if (next < 0 || next >= currentQuestions.length) return;
  currentIndex = next;
  renderQuestion();
}

function updateNavButtons() {
  document.getElementById('btn-prev').disabled = currentIndex === 0;
  const btnNext = document.getElementById('btn-next');
  if (currentIndex === currentQuestions.length - 1) {
    btnNext.textContent = '採点する';
    btnNext.onclick = finishQuiz;
  } else {
    btnNext.textContent = '次へ →';
    btnNext.onclick = () => navigate(1);
  }
}

function renderNavDots() {
  const flags = getFlags();
  const nav = document.getElementById('question-nav');
  nav.innerHTML = '';
  currentQuestions.forEach((q, i) => {
    const el = document.createElement('span');
    el.className = 'q-num';
    el.textContent = i + 1;
    if (i === currentIndex)        el.classList.add('current');
    if (answers[i] !== undefined)  el.classList.add('answered');
    if (flags.has(q.id))           el.classList.add('flagged');
    el.addEventListener('click', () => { currentIndex = i; renderQuestion(); });
    nav.appendChild(el);
  });
}

// =============================================================
// 結果表示
// =============================================================

function finishQuiz() {
  const total = currentQuestions.length;
  // 間違い問題リストを確定（ボタン表示と完全に同じ基準）
  wrongQuestionsForRetry = currentQuestions.filter((q, i) => answers[i] !== q.answer);
  const correct = total - wrongQuestionsForRetry.length;
  console.log('[finishQuiz] total:', total, 'correct:', correct,
    'wrong:', wrongQuestionsForRetry.map(q => `${q.year}${q.half}問${q.number}(ans=${q.answer},選択=${answers[currentQuestions.indexOf(q)]})`));
  const percent = total > 0 ? Math.round(correct / total * 100) : 0;

  document.getElementById('result-score').textContent = `${correct} / ${total}`;
  document.getElementById('result-percent').textContent = `正答率 ${percent}%`;

  const tagStats = {};
  currentQuestions.forEach((q, i) => {
    const ok = answers[i] === q.answer;
    for (const tag of q.tags) {
      if (!tagStats[tag]) tagStats[tag] = { total: 0, correct: 0 };
      tagStats[tag].total++;
      if (ok) tagStats[tag].correct++;
    }
  });

  const tbody = document.getElementById('result-tags');
  tbody.innerHTML = '';
  for (const [tag, stat] of Object.entries(tagStats).sort((a, b) => b[1].total - a[1].total)) {
    const pct = Math.round(stat.correct / stat.total * 100);
    const tr = document.createElement('tr');
    if (pct === 100) tr.className = 'correct';
    else if (stat.correct === 0) tr.className = 'wrong';
    tr.innerHTML = `<td>${tag}</td><td>${stat.correct}/${stat.total}</td><td>${pct}%</td>`;
    tbody.appendChild(tr);
  }

  // 間違えた問題ボタンを表示（リストは finishQuiz() 冒頭で確定済み）
  const wrongCount = wrongQuestionsForRetry.length;
  const btnRetry = document.getElementById('btn-retry-wrong');
  if (wrongCount > 0) {
    btnRetry.textContent = `間違えた ${wrongCount} 問をやり直す`;
    btnRetry.style.display = '';
  } else {
    btnRetry.style.display = 'none';
  }

  showScreen('result');
  showHistory();
}

// =============================================================
// 配線図ビューア
// =============================================================

function toggleNotes() {
  const el = document.getElementById('haisen-notes');
  el.style.display = el.style.display === 'none' ? '' : 'none';
}

function openDiagram() {
  document.getElementById('diagram-modal').style.display = 'flex';
  resetDiagram();
}

function closeDiagram() {
  document.getElementById('diagram-modal').style.display = 'none';
}

function zoomDiagram(delta) {
  dgScale = Math.max(DG_MIN, Math.min(DG_MAX, dgScale + delta));
  applyDiagramTransform();
}

function resetDiagram() {
  dgScale = 1; dgPanX = 0; dgPanY = 0;
  applyDiagramTransform();
}

function applyDiagramTransform() {
  const img = document.getElementById('diagram-img');
  img.style.transform = `translate(${dgPanX}px, ${dgPanY}px) scale(${dgScale})`;
  document.getElementById('zoom-level').textContent = Math.round(dgScale * 100) + '%';
}

function setupDiagramEvents() {
  const vp = document.getElementById('diagram-viewport');
  if (!vp) return;

  vp.addEventListener('wheel', e => {
    e.preventDefault();
    dgScale = Math.max(DG_MIN, Math.min(DG_MAX, dgScale + (e.deltaY > 0 ? -0.15 : 0.15)));
    applyDiagramTransform();
  }, { passive: false });

  vp.addEventListener('mousedown', e => {
    dgDragging = true;
    dgDragX = e.clientX - dgPanX;
    dgDragY = e.clientY - dgPanY;
    vp.style.cursor = 'grabbing';
  });
  window.addEventListener('mousemove', e => {
    if (!dgDragging) return;
    dgPanX = e.clientX - dgDragX;
    dgPanY = e.clientY - dgDragY;
    applyDiagramTransform();
  });
  window.addEventListener('mouseup', () => {
    if (dgDragging) { dgDragging = false; vp.style.cursor = 'grab'; }
  });

  // タッチ: ピンチズーム + ドラッグ
  let lastDist = 0;
  vp.addEventListener('touchstart', e => {
    if (e.touches.length === 1) {
      dgDragging = true;
      dgDragX = e.touches[0].clientX - dgPanX;
      dgDragY = e.touches[0].clientY - dgPanY;
    } else if (e.touches.length === 2) {
      dgDragging = false;
      lastDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                             e.touches[0].clientY - e.touches[1].clientY);
    }
  }, { passive: true });
  vp.addEventListener('touchmove', e => {
    e.preventDefault();
    if (e.touches.length === 1 && dgDragging) {
      dgPanX = e.touches[0].clientX - dgDragX;
      dgPanY = e.touches[0].clientY - dgDragY;
      applyDiagramTransform();
    } else if (e.touches.length === 2) {
      const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                               e.touches[0].clientY - e.touches[1].clientY);
      if (lastDist > 0) {
        dgScale = Math.max(DG_MIN, Math.min(DG_MAX, dgScale + (dist - lastDist) * 0.005));
        applyDiagramTransform();
      }
      lastDist = dist;
    }
  }, { passive: false });
  vp.addEventListener('touchend', () => { dgDragging = false; lastDist = 0; });
}

// =============================================================
// 問題画像ズームビューア
// =============================================================

function openImageZoom() {
  document.getElementById('image-zoom-modal').style.display = 'flex';
  resetImageZoom();
}

function openGenericZoom(src, title) {
  const img = document.getElementById('image-zoom-img');
  img.src = src;
  document.getElementById('image-zoom-title').textContent =
    title + '（スクロール: 拡大縮小 / ドラッグ: 移動）';
  document.getElementById('image-zoom-modal').style.display = 'flex';
  resetImageZoom();
}

function closeImageZoom() {
  document.getElementById('image-zoom-modal').style.display = 'none';
}

function zoomImage(delta) {
  izScale = Math.max(IZ_MIN, Math.min(IZ_MAX, izScale + delta));
  applyImageTransform();
}

function resetImageZoom() {
  izScale = 1; izPanX = 0; izPanY = 0;
  applyImageTransform();
}

function applyImageTransform() {
  const img = document.getElementById('image-zoom-img');
  img.style.transform = `translate(${izPanX}px, ${izPanY}px) scale(${izScale})`;
  document.getElementById('image-zoom-level').textContent = Math.round(izScale * 100) + '%';
}

function setupImageZoomEvents() {
  const vp = document.getElementById('image-zoom-viewport');
  if (!vp) return;

  vp.addEventListener('wheel', e => {
    e.preventDefault();
    izScale = Math.max(IZ_MIN, Math.min(IZ_MAX, izScale + (e.deltaY > 0 ? -0.15 : 0.15)));
    applyImageTransform();
  }, { passive: false });

  vp.addEventListener('mousedown', e => {
    izDragging = true;
    izDragX = e.clientX - izPanX;
    izDragY = e.clientY - izPanY;
    vp.style.cursor = 'grabbing';
  });
  window.addEventListener('mousemove', e => {
    if (!izDragging) return;
    izPanX = e.clientX - izDragX;
    izPanY = e.clientY - izDragY;
    applyImageTransform();
  });
  window.addEventListener('mouseup', () => {
    if (izDragging) { izDragging = false; vp.style.cursor = 'grab'; }
  });

  // タッチ: ピンチズーム + ドラッグ
  let lastDist = 0;
  vp.addEventListener('touchstart', e => {
    if (e.touches.length === 1) {
      izDragging = true;
      izDragX = e.touches[0].clientX - izPanX;
      izDragY = e.touches[0].clientY - izPanY;
    } else if (e.touches.length === 2) {
      izDragging = false;
      lastDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                             e.touches[0].clientY - e.touches[1].clientY);
    }
  }, { passive: true });
  vp.addEventListener('touchmove', e => {
    e.preventDefault();
    if (e.touches.length === 1 && izDragging) {
      izPanX = e.touches[0].clientX - izDragX;
      izPanY = e.touches[0].clientY - izDragY;
      applyImageTransform();
    } else if (e.touches.length === 2) {
      const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                               e.touches[0].clientY - e.touches[1].clientY);
      if (lastDist > 0) {
        izScale = Math.max(IZ_MIN, Math.min(IZ_MAX, izScale + (dist - lastDist) * 0.005));
        applyImageTransform();
      }
      lastDist = dist;
    }
  }, { passive: false });
  vp.addEventListener('touchend', () => { izDragging = false; lastDist = 0; });
}

// =============================================================
// キーボードショートカット
// =============================================================

function setupKeyEvents() {
  window.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeDiagram();
      closeImageZoom();
    }
  });
}
