// 問題画像ズームビューア: ズーム + パン

let imgScale = 1;
let imgPanX = 0, imgPanY = 0;
let imgIsDragging = false;
let imgDragStartX, imgDragStartY;

const IMG_MIN_SCALE = 0.5;
const IMG_MAX_SCALE = 5;

function openImageZoom() {
    document.getElementById('image-zoom-modal').style.display = 'flex';
    resetImageZoom();
}

function openGenericZoom(src, title) {
    const img = document.getElementById('image-zoom-img');
    const modal = document.getElementById('image-zoom-modal');
    img.src = src;
    modal.querySelector('.diagram-modal-header span').textContent =
        title + '（スクロール: 拡大縮小 / ドラッグ: 移動）';
    modal.style.display = 'flex';
    resetImageZoom();
}

function closeImageZoom() {
    document.getElementById('image-zoom-modal').style.display = 'none';
}

function zoomImage(delta) {
    imgScale = Math.max(IMG_MIN_SCALE, Math.min(IMG_MAX_SCALE, imgScale + delta));
    applyImageTransform();
}

function resetImageZoom() {
    imgScale = 1;
    imgPanX = 0;
    imgPanY = 0;
    applyImageTransform();
}

function applyImageTransform() {
    const img = document.getElementById('image-zoom-img');
    img.style.transform = `translate(${imgPanX}px, ${imgPanY}px) scale(${imgScale})`;
    document.getElementById('image-zoom-level').textContent = Math.round(imgScale * 100) + '%';
}

document.addEventListener('DOMContentLoaded', () => {
    const viewport = document.getElementById('image-zoom-viewport');
    if (!viewport) return;

    // マウスホイールでズーム
    viewport.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.15 : 0.15;
        imgScale = Math.max(IMG_MIN_SCALE, Math.min(IMG_MAX_SCALE, imgScale + delta));
        applyImageTransform();
    }, { passive: false });

    // ドラッグでパン
    viewport.addEventListener('mousedown', (e) => {
        imgIsDragging = true;
        imgDragStartX = e.clientX - imgPanX;
        imgDragStartY = e.clientY - imgPanY;
        viewport.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
        if (!imgIsDragging) return;
        imgPanX = e.clientX - imgDragStartX;
        imgPanY = e.clientY - imgDragStartY;
        applyImageTransform();
    });

    window.addEventListener('mouseup', () => {
        if (imgIsDragging) {
            imgIsDragging = false;
            const vp = document.getElementById('image-zoom-viewport');
            if (vp) vp.style.cursor = 'grab';
        }
    });

    // タッチ対応: ピンチズーム + ドラッグ
    let imgLastTouchDist = 0;
    let imgLastTouchX = 0, imgLastTouchY = 0;

    viewport.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) {
            imgIsDragging = true;
            imgLastTouchX = e.touches[0].clientX - imgPanX;
            imgLastTouchY = e.touches[0].clientY - imgPanY;
        } else if (e.touches.length === 2) {
            imgIsDragging = false;
            imgLastTouchDist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
        }
    }, { passive: true });

    viewport.addEventListener('touchmove', (e) => {
        e.preventDefault();
        if (e.touches.length === 1 && imgIsDragging) {
            imgPanX = e.touches[0].clientX - imgLastTouchX;
            imgPanY = e.touches[0].clientY - imgLastTouchY;
            applyImageTransform();
        } else if (e.touches.length === 2) {
            const dist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
            if (imgLastTouchDist > 0) {
                const delta = (dist - imgLastTouchDist) * 0.005;
                imgScale = Math.max(IMG_MIN_SCALE, Math.min(IMG_MAX_SCALE, imgScale + delta));
                applyImageTransform();
            }
            imgLastTouchDist = dist;
        }
    }, { passive: false });

    viewport.addEventListener('touchend', () => {
        imgIsDragging = false;
        imgLastTouchDist = 0;
    });

    // Escで閉じる
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeImageZoom();
    });
});
