// == HRAIN v2.5 (Core Functional Build) ==
// Полный JS-файл от 16.11.2025
// Реализовано: Создание, Удаление, Перетаскивание, Связи, Аналитика.
// НЕ реализовано: Зум, Профили, Сохранение.

document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Получаем все наши HTML-элементы ---
    const canvas = document.getElementById('canvas');
    const linkLayer = document.getElementById('link-layer');
    
    // Панели
    const hintsPanel = document.getElementById('hints');
    const analyticsPanel = document.getElementById('analytics');
    const toggleHintsBtn = document.getElementById('toggleHintsButton');
    const toggleAnalyticsBtn = document.getElementById('toggleAnalyticsButton');
    
    // Элементы аналитики
    const nodeCountEl = document.getElementById('node-count');
    const linkCountEl = document.getElementById('link-count');
    const dominantNodesList = document.getElementById('dominant-nodes');

    // Переменная для создания связей
    let firstNodeForLink = null;
    // Флаг, чтобы отделить клик от перетаскивания
    let isDragging = false; 

    // --- 2. Логика боковых панелей ---
    toggleHintsBtn.addEventListener('click', () => hintsPanel.classList.toggle('visible'));
    toggleAnalyticsBtn.addEventListener('click', () => analyticsPanel.classList.toggle('visible'));

    // --- 3. Логика Холста (Создание узлов) ---
    canvas.addEventListener('dblclick', (e) => {
        // Убедимся, что кликнули именно на холст, а не на узел
        if (e.target === canvas) {
            // Отменяем выделение узла, если кликнули по фону
            if (firstNodeForLink) {
                firstNodeForLink.classList.remove('selected');
                firstNodeForLink = null;
            }
            createNode(e.clientX, e.clientY);
        }
    });

    /**
     * Создает новый узел (ноду) на холсте
     */
    function createNode(x, y) {
        const node = document.createElement('div');
        node.className = 'node';
        node.contentEditable = 'true';
        node.setAttribute('placeholder', 'Идея...');
        
        // Каждому узлу даем уникальный ID. Это КРИТИЧЕСКИ ВАЖНО для связей.
        node.id = 'node_' + Date.now();
        
        node.style.left = `${x - 60}px`;
        node.style.top = `${y - 30}px`;
        
        // --- Вешаем обработчики событий на УЗЕЛ ---
        
        // 1. Логика Перетаскивания
        makeDraggable(node);
        
        // 2. Логика Кликов (Создание связей И Удаление)
        node.addEventListener('click', (e) => onNodeClick(e, node));
        node.addEventListener('dblclick', (e) => onNodeDoubleClick(e, node));
        
        // 3. Не даем "всплыть" клику на холст
        node.addEventListener('mousedown', (e) => e.stopPropagation());
        node.addEventListener('dblclick', (e) => e.stopPropagation());

        canvas.appendChild(node);
        node.focus(); // Сразу ставим курсор
        
        updateAnalytics(); // Обновляем счетчик
    }

    /**
     * Обработчик ОДИНАРНОГО клика по узлу (Логика связей)
     */
    function onNodeClick(e, node) {
        // Если мы только что перетащили, это не клик.
        if (isDragging) return;

        // Это 1-й узел для связи?
        if (!firstNodeForLink) {
            firstNodeForLink = node;
            node.classList.add('selected');
        } 
        // Это 2-й узел для связи?
        else if (firstNodeForLink !== node) {
            createLink(firstNodeForLink, node);
            firstNodeForLink.classList.remove('selected');
            firstNodeForLink = null;
        }
        // Это клик по тому же самому узлу? (Отмена)
        else {
            firstNodeForLink.classList.remove('selected');
            firstNodeForLink = null;
        }
    }

    /**
     * Обработчик ДВОЙНОГО клика по узлу (Логика удаления)
     */
    function onNodeDoubleClick(e, node) {
        // Нам нужно удалить узел И все связанные с ним линии
        
        // Находим все линии, подключенные к этому узлу
        const linesToRemove = document.querySelectorAll(
            `line[data-from="${node.id}"], line[data-to="${node.id}"]`
        );
        
        linesToRemove.forEach(line => line.remove());
        
        // Удаляем сам узел
        node.remove();
        
        // Если мы удалили узел, который был выбран для связи
        if (firstNodeForLink === node) {
            firstNodeForLink = null;
        }
        
        updateAnalytics(); // Обновляем счетчики
    }

    /**
     * Создает SVG линию (связь) между двумя узлами
     */
    function createLink(node1, node2) {
        // Проверяем, нет ли уже такой связи
        const existingLink = document.querySelector(
            `line[data-from="${node1.id}"][data-to="${node2.id}"],
             line[data-from="${node2.id}"][data-to="${node1.id}"]`
        );
        
        if (existingLink) return; // Такая связь уже есть

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        
        // Сохраняем, какие узлы эта линия соединяет
        line.setAttribute('data-from', node1.id);
        line.setAttribute('data-to', node2.id);
        
        // Получаем координаты центров узлов
        const pos1 = getNodeCenter(node1);
        const pos2 = getNodeCenter(node2);
        
        line.setAttribute('x1', pos1.x);
        line.setAttribute('y1', pos1.y);
        line.setAttribute('x2', pos2.x);
        line.setAttribute('y2', pos2.y);
        
        linkLayer.appendChild(line);
        updateAnalytics();
    }

    /**
     * Делает узел перетаскиваемым (работает и с мышью, и с тачем)
     */
    function makeDraggable(element) {
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        
        // Начинаем перетаскивание
        const dragStart = (e) => {
            // Не тащить, если мы редактируем текст
            if (e.target.isContentEditable) return;
            
            e = e || window.event;
            // e.preventDefault(); // Не нужно для mousedown
            
            isDragging = false; // Сбрасываем флаг

            // Получаем позицию курсора/пальца
            if (e.type === 'touchstart') {
                pos3 = e.touches[0].clientX;
                pos4 = e.touches[0].clientY;
            } else {
                pos3 = e.clientX;
                pos4 = e.clientY;
            }
            
            document.onmouseup = dragEnd;
            document.onmousemove = dragMove;
            document.ontouchend = dragEnd;
            document.ontouchmove = dragMove;
            
            element.style.cursor = 'grabbing';
            element.style.zIndex = '1000';
        };

        // Двигаем
        const dragMove = (e) => {
            isDragging = true; // Мы начали тащить
            
            e = e || window.event;
            // Предотвращаем прокрутку страницы на мобильных
            if (e.type === 'touchmove') e.preventDefault(); 
            
            let clientX, clientY;
            if (e.type === 'touchmove') {
                clientX = e.touches[0].clientX;
                clientY = e.touches[0].clientY;
            } else {
                clientX = e.clientX;
                clientY = e.clientY;
            }
            
            // Считаем новое положение
            pos1 = pos3 - clientX;
            pos2 = pos4 - clientY;
            pos3 = clientX;
            pos4 = clientY;
            
            // Устанавливаем новую позицию узла
            element.style.top = (element.offsetTop - pos2) + "px";
            element.style.left = (element.offsetLeft - pos1) + "px";
            
            // ОБНОВЛЯЕМ ЛИНИИ
            updateAttachedLinks(element);
        };

        // Заканчиваем перетаскивание
        const dragEnd = () => {
            document.onmouseup = null;
            document.onmousemove = null;
            document.ontouchend = null;
            document.ontouchmove = null;
            
            element.style.cursor = 'grab';
            element.style.zIndex = '10';
            
            // Сбрасываем флаг (с небольшой задержкой, чтобы 'click' не сработал)
            setTimeout(() => { isDragging = false; }, 0);
        };
        
        // Вешаем стартовый обработчик
        element.onmousedown = dragStart;
        element.ontouchstart = dragStart;
    }

    /**
     * Обновляет все линии, прикрепленные к узлу
     */
    function updateAttachedLinks(node) {
        const nodeId = node.id;
        const newPos = getNodeCenter(node);
        
        // Ищем линии, где он 'from'
        linkLayer.querySelectorAll(`line[data-from="${nodeId}"]`).forEach(line => {
            line.setAttribute('x1', newPos.x);
            line.setAttribute('y1', newPos.y);
        });
        
        // Ищем линии, где он 'to'
        linkLayer.querySelectorAll(`line[data-to="${nodeId}"]`).forEach(line => {
            line.setAttribute('x2', newPos.x);
            line.setAttribute('y2', newPos.y);
        });
    }

    /**
     * Вспомогательная функция: получает центр узла
     */
    function getNodeCenter(node) {
        const rect = node.getBoundingClientRect();
        // ВАЖНО: Мы не учитываем зум/пан, поэтому getBoundingClientRect - это то, что нам нужно.
        // Если бы был зум, тут была бы сложная математика.
        return {
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2
        };
    }

    /**
     * Обновляет панель аналитики
     */
    function updateAnalytics() {
        const nodes = document.querySelectorAll('.node');
        const links = document.querySelectorAll('#link-layer line');
        
        nodeCountEl.textContent = nodes.length;
        linkCountEl.textContent = links.length;
        
        // Простая аналитика доминирования
        const dominance = new Map();
        nodes.forEach(n => dominance.set(n.id, 0));
        
        links.forEach(l => {
            const from = l.dataset.from;
            const to = l.dataset.to;
            if (dominance.has(from)) dominance.set(from, dominance.get(from) + 1);
            if (dominance.has(to)) dominance.set(to, dominance.get(to) + 1);
        });
        
        // Сортируем и берем топ-3
        const sorted = [...dominance.entries()].sort((a, b) => b[1] - a[1]);
        
        dominantNodesList.innerHTML = ''; // Очищаем список
        
        if (sorted.length === 0 || sorted[0][1] === 0) {
            dominantNodesList.innerHTML = '<li>Нет данных</li>';
            return;
        }

        for (let i = 0; i < Math.min(sorted.length, 3); i++) {
            const [nodeId, count] = sorted[i];
            const node = document.getElementById(nodeId);
            if (node) {
                let text = node.textContent.substring(0, 20) || "[Пустой узел]";
                if (node.textContent.length > 20) text += "...";
                
                const li = document.createElement('li');
                li.textContent = `${text} (Связей: ${count})`;
                dominantNodesList.appendChild(li);
            }
        }
    }
    
    // Первичный запуск
    updateAnalytics();
    console.log('HRAIN v2.5 (Core) загружен.');
    console.log('TODO: Зум, Панорамирование, Сохранение, Профили.');
});

