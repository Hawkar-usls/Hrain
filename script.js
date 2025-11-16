// Ждем, пока весь HTML-документ загрузится
document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Получаем все наши HTML-элементы ---
    const canvas = document.getElementById('canvas');
    const hintsPanel = document.getElementById('hints');
    const analyticsPanel = document.getElementById('analytics');
    const toggleHintsBtn = document.getElementById('toggleHintsButton');
    const toggleAnalyticsBtn = document.getElementById('toggleAnalyticsButton');
    
    // --- 2. Логика боковых панелей ---
    
    // Показываем/скрываем Подсказки
    toggleHintsBtn.addEventListener('click', () => {
        hintsPanel.classList.toggle('visible');
    });

    // Показываем/скрываем Аналитику
    toggleAnalyticsBtn.addEventListener('click', () => {
        analyticsPanel.classList.toggle('visible');
    });

    // --- 3. Базовая логика узлов ---
    
    // Создаем узел по дабл-клику на холсте
    // (Пока без учета зума и панорамирования)
    canvas.addEventListener('dblclick', (e) => {
        // Убедимся, что кликнули именно на холст, а не на узел
        if (e.target === canvas) {
            createNode(e.clientX, e.clientY);
        }
    });

    /**
     * Создает новый узел (ноду) на холсте
     * @param {number} x - Координата X
     * @param {number} y - Координата Y
     */
    function createNode(x, y) {
        const node = document.createElement('div');
        node.className = 'node';
        node.contentEditable = 'true'; // Делаем текст редактируемым
        node.textContent = 'Новая идея...';
        
        // Позиционируем узел
        // (ВАЖНО: пока это координаты относительно ОКНА, 
        // а не относительно "мира". Для зума это придется усложнить)
        node.style.left = `${x - 60}px`; // -60px чтобы клик был в центре
        node.style.top = `${y - 30}px`;  // -30px
        
        // Добавляем узел на холст
        canvas.appendChild(node);
        
        // Сразу выделяем текст для удобства
        selectText(node);

        // TODO: Добавить логику перетаскивания (makeDraggable)
        // TODO: Добавить логику удаления (двойной клик по узлу)
        // TODO: Добавить логику соединения (одиночный клик)
    }

    /**
     * Вспомогательная функция для выделения текста в новом узле
     */
    function selectText(element) {
        const range = document.createRange();
        range.selectNodeContents(element);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }
    
    console.log('HRAIN v2.0-Alpha (Мини-версия) загружена.');
    console.log('TODO: Перетаскивание, Зум, SVG-Линии, Сохранение.');

}); // Конец DOMContentLoaded
