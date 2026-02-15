// 配線図ビューア: ズーム + パン

let scale = 1;
let panX = 0, panY = 0;
let isDragging = false;
let dragStartX, dragStartY;

const MIN_SCALE = 0.5;
const MAX_SCALE = 4;

function toggleNotes() {
    const el = document.getElementById('haisen-notes');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function openDiagram() {
    const modal = document.getElementById('diagram-modal');
    modal.style.display = 'flex';
    resetDiagram();
}

function closeDiagram() {
    document.getElementById('diagram-modal').style.display = 'none';
}

function zoomDiagram(delta) {
    scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale + delta));
    applyTransform();
}

function resetDiagram() {
    scale = 1;
    panX = 0;
    panY = 0;
    applyTransform();
}

function applyTransform() {
    const img = document.getElementById('diagram-img');
    img.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    document.getElementById('zoom-level').textContent = Math.round(scale * 100) + '%';
}

// マウスホイールでズーム
document.addEventListener('DOMContentLoaded', () => {
    const viewport = document.getElementById('diagram-viewport');
    if (!viewport) return;

    viewport.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.15 : 0.15;
        scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale + delta));
        applyTransform();
    }, { passive: false });

    // ドラッグでパン
    viewport.addEventListener('mousedown', (e) => {
        isDragging = true;
        dragStartX = e.clientX - panX;
        dragStartY = e.clientY - panY;
        viewport.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        panX = e.clientX - dragStartX;
        panY = e.clientY - dragStartY;
        applyTransform();
    });

    window.addEventListener('mouseup', () => {
        isDragging = false;
        const vp = document.getElementById('diagram-viewport');
        if (vp) vp.style.cursor = 'grab';
    });

    // タッチ対応: ピンチズーム + ドラッグ
    let lastTouchDist = 0;
    let lastTouchX = 0, lastTouchY = 0;

    viewport.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) {
            isDragging = true;
            lastTouchX = e.touches[0].clientX - panX;
            lastTouchY = e.touches[0].clientY - panY;
        } else if (e.touches.length === 2) {
            isDragging = false;
            lastTouchDist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
        }
    }, { passive: true });

    viewport.addEventListener('touchmove', (e) => {
        e.preventDefault();
        if (e.touches.length === 1 && isDragging) {
            panX = e.touches[0].clientX - lastTouchX;
            panY = e.touches[0].clientY - lastTouchY;
            applyTransform();
        } else if (e.touches.length === 2) {
            const dist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
            if (lastTouchDist > 0) {
                const delta = (dist - lastTouchDist) * 0.005;
                scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale + delta));
                applyTransform();
            }
            lastTouchDist = dist;
        }
    }, { passive: false });

    viewport.addEventListener('touchend', () => {
        isDragging = false;
        lastTouchDist = 0;
    });

    // Escで閉じる
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeDiagram();
    });
});
