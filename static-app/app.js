// 静的HTML版 CBT 練習アプリ
// 画像は ../server/static/pages/ を参照（リポジトリを clone してから開くこと）

const STATIC_BASE = '../server/static/';
const STORAGE_KEY = 'denki2-history';

let currentQuestions = [];
let currentIndex = 0;
let answers = {};        // { qIndex: selectedChoice (0-3) }
let lastSettings = {};   // 「もう一度」用に設定を保持

// ---- 初期化 ----

document.addEventListener('DOMContentLoaded', () => {
  buildYearHalfOptions();
  showHistory();
});

function buildYearHalfOptions() {
  const sel = document.getElementById('sel-year-half');
  const seen = new Set();
  const combos = [];
  for (const q of QUESTIONS) {
    const key = `${q.year}_${q.half}`;
    if (!seen.has(key)) {
      seen.add(key);
      combos.push(key);
    }
  }
  combos.sort().reverse();
  for (const combo of combos) {
    const [year, half] = combo.split('_');
    const opt = document.createElement('option');
    opt.value = combo;
    opt.textContent = `${year}年 ${half === 'upper' ? '上期' : '下期'}`;
    sel.appendChild(opt);
  }
}

// ---- LocalStorage ----

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function saveAnswerToHistory(questionId, isCorrect) {
  const data = getHistory();
  data[questionId] = isCorrect;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function getWrongIds() {
  const data = getHistory();
  return new Set(
    Object.entries(data)
      .filter(([, v]) => v === false)
      .map(([k]) => parseInt(k, 10))
  );
}

function showHistory() {
  const data = getHistory();
  const total = Object.keys(data).length;
  const wrong = Object.values(data).filter(v => !v).length;
  const card = document.getElementById('history-card');
  const list = document.getElementById('history-list');
  if (total === 0) {
    card.style.display = 'none';
    return;
  }
  card.style.display = '';
  list.innerHTML = `
    <p>挑戦済み: <strong>${total}</strong> 問 ／ 要復習: <strong>${wrong}</strong> 問</p>
    <button class="btn" onclick="clearHistory()" style="margin-top:0.5rem">履歴をリセット</button>
  `;
}

function clearHistory() {
  if (confirm('学習履歴をすべてクリアしますか？')) {
    localStorage.removeItem(STORAGE_KEY);
    showHistory();
  }
}

// ---- クイズ開始 ----

function startQuiz() {
  const yearHalf = document.getElementById('sel-year-half').value;
  const count = Math.max(1, parseInt(document.getElementById('inp-count').value, 10) || 30);
  const mode = document.getElementById('sel-mode').value;

  lastSettings = { yearHalf, count, mode };

  let pool = QUESTIONS.slice();

  if (yearHalf) {
    const [year, half] = yearHalf.split('_');
    pool = pool.filter(q => q.year === year && q.half === half);
  }

  if (mode === 'review') {
    const wrongIds = getWrongIds();
    if (wrongIds.size === 0) {
      alert('復習すべき間違いがありません。通常モードで挑戦してください。');
      return;
    }
    pool = pool.filter(q => wrongIds.has(q.id));
  }

  if (pool.length === 0) {
    alert('該当する問題がありません。');
    return;
  }

  // シャッフルして count 問選択
  shuffleArray(pool);
  currentQuestions = pool.slice(0, count);
  currentIndex = 0;
  answers = {};

  showScreen('quiz');
  renderQuestion();
}

function restartQuiz() {
  // 前回と同じ設定で再挑戦（DOMの値も復元）
  if (lastSettings.yearHalf !== undefined) {
    document.getElementById('sel-year-half').value = lastSettings.yearHalf;
    document.getElementById('inp-count').value = lastSettings.count;
    document.getElementById('sel-mode').value = lastSettings.mode;
  }
  startQuiz();
}

function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}

// ---- 画面切り替え ----

function showScreen(name) {
  document.getElementById('screen-setup').style.display = name === 'setup' ? '' : 'none';
  document.getElementById('screen-quiz').style.display = name === 'quiz' ? '' : 'none';
  document.getElementById('screen-result').style.display = name === 'result' ? '' : 'none';
}

function goSetup() {
  showScreen('setup');
  showHistory();
}

// ---- 問題表示 ----

function renderQuestion() {
  const q = currentQuestions[currentIndex];
  const total = currentQuestions.length;

  document.getElementById('quiz-progress').textContent =
    `問題 ${currentIndex + 1} / ${total}`;

  // 画像
  const imgEl = document.getElementById('question-image');
  imgEl.src = STATIC_BASE + q.image_path;
  imgEl.alt = `問${q.number}`;

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
    const choiceText = choice ? `<span class="choice-label">${labels[i]}</span><span class="choice-text">${choice}</span>` : `<span class="choice-label">${labels[i]}</span>`;
    btn.innerHTML = choiceText;
    btn.addEventListener('click', () => selectAnswer(i));
    choicesEl.appendChild(btn);
  });

  // フィードバックリセット
  const fb = document.getElementById('feedback');
  fb.style.display = 'none';
  fb.className = 'feedback';
  fb.textContent = '';

  // 既存の回答を復元
  if (answers[currentIndex] !== undefined) {
    applyAnswerUI(answers[currentIndex], q.answer, true);
  }

  updateNavButtons();
  renderNavDots();
}

function selectAnswer(selected) {
  if (answers[currentIndex] !== undefined) return;  // 回答済み

  const q = currentQuestions[currentIndex];
  answers[currentIndex] = selected;
  saveAnswerToHistory(q.id, selected === q.answer);

  applyAnswerUI(selected, q.answer, true);
  renderNavDots();
}

function applyAnswerUI(selected, correct, showFeedback) {
  const btns = document.querySelectorAll('.choice-btn');
  const labels = ['イ', 'ロ', 'ハ', 'ニ'];
  btns.forEach((btn, i) => {
    btn.disabled = true;
    if (i === correct) btn.classList.add('correct');
    else if (i === selected && selected !== correct) btn.classList.add('wrong');
  });
  if (btns[selected]) btns[selected].classList.add('selected');

  if (showFeedback) {
    const fb = document.getElementById('feedback');
    const isCorrect = selected === correct;
    fb.textContent = isCorrect
      ? '正解！'
      : `不正解。正解は ${labels[correct]} です。`;
    fb.className = `feedback ${isCorrect ? 'correct' : 'wrong'}`;
    fb.style.display = '';
  }
}

// ---- ナビゲーション ----

function navigate(dir) {
  const next = currentIndex + dir;
  if (next < 0 || next >= currentQuestions.length) return;
  currentIndex = next;
  renderQuestion();
}

function updateNavButtons() {
  const total = currentQuestions.length;
  document.getElementById('btn-prev').disabled = currentIndex === 0;

  const btnNext = document.getElementById('btn-next');
  if (currentIndex === total - 1) {
    btnNext.textContent = '採点する';
    btnNext.onclick = finishQuiz;
  } else {
    btnNext.textContent = '次へ →';
    btnNext.onclick = () => navigate(1);
  }
}

function renderNavDots() {
  const nav = document.getElementById('question-nav');
  nav.innerHTML = '';
  currentQuestions.forEach((_, i) => {
    const el = document.createElement('span');
    el.className = 'q-num';
    el.textContent = i + 1;
    if (i === currentIndex) el.classList.add('current');
    if (answers[i] !== undefined) el.classList.add('answered');
    el.addEventListener('click', () => {
      currentIndex = i;
      renderQuestion();
    });
    nav.appendChild(el);
  });
}

// ---- 結果表示 ----

function finishQuiz() {
  const total = currentQuestions.length;
  const correct = currentQuestions.filter((q, i) => answers[i] === q.answer).length;
  const percent = total > 0 ? Math.round(correct / total * 100) : 0;

  document.getElementById('result-score').textContent = `${correct} / ${total}`;
  document.getElementById('result-percent').textContent = `正答率 ${percent}%`;

  // タグ別集計
  const tagStats = {};
  currentQuestions.forEach((q, i) => {
    const isCorrect = answers[i] === q.answer;
    for (const tag of q.tags) {
      if (!tagStats[tag]) tagStats[tag] = { total: 0, correct: 0 };
      tagStats[tag].total++;
      if (isCorrect) tagStats[tag].correct++;
    }
  });

  const tbody = document.getElementById('result-tags');
  tbody.innerHTML = '';
  const sorted = Object.entries(tagStats).sort((a, b) => b[1].total - a[1].total);
  for (const [tag, stat] of sorted) {
    const pct = Math.round(stat.correct / stat.total * 100);
    const tr = document.createElement('tr');
    if (pct === 100) tr.className = 'correct';
    else if (stat.correct === 0) tr.className = 'wrong';
    tr.innerHTML = `<td>${tag}</td><td>${stat.correct}/${stat.total}</td><td>${pct}%</td>`;
    tbody.appendChild(tr);
  }

  showScreen('result');
  showHistory();
}
