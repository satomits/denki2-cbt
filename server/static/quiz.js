// --- 後で見直すフラグ ---
function getFlagKey() {
    return `flags_${SESSION_ID}`;
}

function getFlags() {
    try {
        return JSON.parse(localStorage.getItem(getFlagKey()) || '[]');
    } catch { return []; }
}

function saveFlags(flags) {
    localStorage.setItem(getFlagKey(), JSON.stringify(flags));
}

function toggleFlag() {
    let flags = getFlags();
    const idx = flags.indexOf(Q_INDEX);
    if (idx >= 0) {
        flags.splice(idx, 1);
    } else {
        flags.push(Q_INDEX);
    }
    saveFlags(flags);
    updateFlagUI();
}

function updateFlagUI() {
    const flags = getFlags();
    const isFlagged = flags.includes(Q_INDEX);

    // ボタン表示更新
    const btn = document.getElementById('flag-btn');
    if (btn) {
        btn.classList.toggle('flagged', isFlagged);
        btn.textContent = isFlagged ? '見直し解除' : '後で見直す';
    }

    // 問題番号ナビのフラグ表示
    document.querySelectorAll('.q-num[data-qindex]').forEach(el => {
        const qi = parseInt(el.dataset.qindex);
        el.classList.toggle('flagged', flags.includes(qi));
    });
}

document.addEventListener('DOMContentLoaded', updateFlagUI);

// --- 回答処理 ---
async function selectAndSubmit(index) {
    selectedIndex = index;

    // ボタンのハイライト更新
    document.querySelectorAll('.choice-btn').forEach(btn => {
        btn.classList.toggle('selected', parseInt(btn.dataset.index) === index);
    });

    // 回答を保存
    await fetch('/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: SESSION_ID,
            question_id: QUESTION_ID,
            selected: selectedIndex,
        }),
    });

    // 問題番号ナビの回答済みマークを更新
    const navLinks = document.querySelectorAll('.q-num');
    if (navLinks[Q_INDEX]) {
        navLinks[Q_INDEX].classList.add('answered');
    }

    // 少し待ってから次の問題へ自動遷移
    if (NEXT_URL) {
        setTimeout(() => { window.location.href = NEXT_URL; }, 300);
    }
}
