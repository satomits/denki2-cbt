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
