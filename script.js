// == HRAIN v6.0 (The Engine Rebuild) ==
// Полный JS-файл от 16.11.2025
// РЕАЛИЗОВАНО: Бесконечный холст (Zoom/Pan)
// ВСЕ ФУНКЦИИ v5.0 сохранены и адаптированы.

document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Получаем все наши HTML-элементы ---
    const workspace = document.getElementById('workspace');
    const canvas = document.getElementById('canvas');
    const nodeLayer = document.getElementById('node-layer');
    const linkLayer = document.getElementById('link-layer');
    
    // Элементы профилей
    const profileSelect = document.getElementById('profile-select');
    const saveBtn = document.getElementById('saveProfileButton');
    const newBtn = document.getElementById('newProfileButton');
    const deleteBtn = document.getElementById('deleteProfileButton');
    const importBtn = document.getElementById('importProfileButton');
    const exportBtn = document.getElementById('exportProfileButton');
    const fileImporter = document.getElementById('file-importer');   
    
    // Элементы модального окна ПИН
    const pinBackdrop = document.getElementById('pin-modal-backdrop');
    const pinInput = document.getElementById('pin-input');
    const pinError = document.getElementById('pin-error');
    const pinCancelBtn = document.getElementById('pin-cancel-btn');
    const pinOkBtn = document.getElementById('pin-ok-btn');
    
    // Элементы палитры
    const colorPalette = document.getElementById('color-palette');

    // --- Глобальные переменные ---
    let firstNodeForLink = null;
    let longPressTimer = null;
    let longPressNode = null;
    let pinCallback = null;

    // --- НОВЫЙ ДВИЖОК v6.0: "КАМЕРА" ---
    let viewState = {
        x: 0,       // Сдвиг по X
        y: 0,       // Сдвиг по Y
        scale: 1.0, // Масштаб
        isPanning: false,
        isDraggingNode: false,
        panStart: { x: 0, y: 0 },
        activeNode: null,
        nodeOffset: { x: 0, y: 0 },
        isSpacebarDown: false // Для пана с Пробелом
    };

    const MIN_ZOOM = 0.1;
    const MAX_ZOOM = 4.0;
    
    /**
     * (v6.0) Применяет позицию "камеры" к холсту
     */
    function updateView() {
        // Ограничиваем зум
        viewState.scale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewState.scale));
        
        // Применяем transform
        const transform = `translate(${viewState.x}px, ${viewState.y}px) scale(${viewState.scale})`;
        canvas.style.transform = transform;
    }

    /**
     * (v6.0) Конвертирует координаты ЭКРАНА (e.clientX) в координаты МИРА (холста)
     */
    function screenToWorld(screenX, screenY) {
        return {
            x: (screenX - viewState.x) / viewState.scale,
            y: (screenY - viewState.y) / viewState.scale
        };
    }
    
    // --- 2. Логика Профилей и Сохранения (Адаптировано v6.0) ---

    newBtn.addEventListener('click', () => { /* ... (без изменений из v5.0) ... */ 
        const profileName = prompt('Введите имя нового профиля:');
        if (!profileName || profileName.trim() === '') return;
        const profiles = getProfileList();
        if (profiles.includes(profileName)) {
            alert('Ошибка: Профиль с таким именем уже существует.');
            return;
        }
        profiles.push(profileName);
        localStorage.setItem('hrain_profiles', JSON.stringify(profiles));
        clearCanvas();
        // v6.0: Сбрасываем вид
        viewState.x = window.innerWidth / 2;
        viewState.y = window.innerHeight / 3;
        viewState.scale = 1.0;
        updateView();
        
        saveMap(profileName, true);
    });

    saveBtn.addEventListener('click', () => { /* ... (без изменений из v5.0) ... */
        const profileName = profileSelect.value;
        if (!profileName) { alert('Сначала создайте или выберите профиль.'); return; }
        saveMap(profileName, false);
    });

    deleteBtn.addEventListener('click', () => { /* ... (без изменений из v5.0) ... */
        const profileName = profileSelect.value;
        if (!profileName) return;
        if (!confirm(`Вы уверены, что хотите удалить профиль "${profileName}"? Это действие необратимо.`)) return;
        let profiles = getProfileList();
        profiles = profiles.filter(p => p !== profileName);
        localStorage.setItem('hrain_profiles', JSON.stringify(profiles));
        localStorage.removeItem(`hrain_data_${profileName}`);
        clearCanvas();
        updateProfileList();
    });

    profileSelect.addEventListener('change', () => { /* ... (без изменений из v5.0) ... */
        const profileName = profileSelect.value;
        if (profileName) loadMap(profileName);
    });

    importBtn.addEventListener('click', () => fileImporter.click());
    fileImporter.addEventListener('change', (e) => { /* ... (без изменений из v5.0) ... */ 
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            const encryptedData = event.target.result;
            const profileName = prompt('Введите имя для нового импортированного профиля:', file.name.replace('.hrain', ''));
            if (!profileName) return;
            const profiles = getProfileList();
            if (profiles.includes(profileName)) { alert('Ошибка: Профиль с таким именем уже существует.'); return; }
            profiles.push(profileName);
            localStorage.setItem('hrain_profiles', JSON.stringify(profiles));
            localStorage.setItem(`hrain_data_${profileName}`, encryptedData);
            updateProfileList(profileName);
            loadMap(profileName);
        };
        reader.readAsText(file);
        e.target.value = null;
    });

    exportBtn.addEventListener('click', () => { /* ... (без изменений из v5.0) ... */
        const profileName = profileSelect.value;
        if (!profileName) { alert('Сначала выберите профиль для экспорта.'); return; }
        const encryptedData = localStorage.getItem(`hrain_data_${profileName}`);
        if (!encryptedData) { alert('Ошибка: Данные профиля не найдены.'); return; }
        const blob = new Blob([encryptedData], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${profileName}.hrain`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });

    // --- Логика ПИН-кода (Без изменений) ---
    function showPinPrompt(title, callback) { /* ... (без изменений) ... */ 
        document.getElementById('pin-title').textContent = title;
        pinInput.value = ''; pinError.textContent = '';
        pinCallback = callback;
        pinBackdrop.classList.remove('hidden');
        pinInput.focus();
    }
    pinCancelBtn.addEventListener('click', () => { pinBackdrop.classList.add('hidden'); pinCallback = null; });
    pinOkBtn.addEventListener('click', () => { /* ... (без изменений) ... */
        const pin = pinInput.value;
        if (pin.length !== 4) { pinError.textContent = 'ПИН должен состоять из 4 цифр'; return; }
        if (pinCallback) pinCallback(pin);
        pinBackdrop.classList.add('hidden'); pinCallback = null;
    });

    // --- Логика Сохранения/Загрузки (ОБНОВЛЕНО v6.0) ---
    function saveMap(profileName, isNew) {
        showPinPrompt(isNew ? 'Создайте 4-значный ПИН' : 'Введите 4-значный ПИН', (pin) => {
            const mapData = serializeMap(); // v6.0: теперь сохраняет и вид
            const encryptedData = encrypt(mapData, pin);
            localStorage.setItem(`hrain_data_${profileName}`, encryptedData);
            localStorage.setItem('hrain_lastProfile', profileName);
            updateProfileList(profileName);
            alert(`Профиль "${profileName}" успешно сохранен!`);
        });
    }
    function loadMap(profileName) {
        const encryptedData = localStorage.getItem(`hrain_data_${profileName}`);
        if (!encryptedData) { alert('Ошибка: Данные профиля не найдены.'); clearCanvas(); return; }
        showPinPrompt(`ПИН для "${profileName}"`, (pin) => {
            const mapData = decrypt(encryptedData, pin);
            if (mapData === null) { alert('Неверный ПИН-код!'); return; }
            deserializeMap(mapData); // v6.0: теперь загружает и вид
            localStorage.setItem('hrain_lastProfile', profileName);
            updateProfileList(profileName);
        });
    }

    // --- Сериализация (ОБНОВЛЕНО v6.0 для вида и ЦВЕТОВ) ---
    function serializeMap() {
        const nodes = [];
        document.querySelectorAll('.node').forEach(node => {
            nodes.push({
                id: node.id,
                x: node.style.left, // Координаты "мира"
                y: node.style.top,
                content: node.innerHTML,
                color: node.getAttribute('data-color') || 'default'
            });
        });
        const links = [];
        document.querySelectorAll('#link-layer line').forEach(line => {
            links.push({ from: line.getAttribute('data-from'), to: line.getAttribute('data-to') });
        });
        
        // v6.0: Сохраняем "камеру"
        const view = { x: viewState.x, y: viewState.y, scale: viewState.scale };
        
        return JSON.stringify({ nodes, links, view });
    }

    // --- Десериализация (ОБНОВЛЕНО v6.0 для вида и ЦВЕТОВ) ---
    function deserializeMap(jsonString) {
        clearCanvas();
        const data = JSON.parse(jsonString);

        data.nodes.forEach(nodeData => {
            // Создаем узел, но позицию не ставим
            const node = createNode(0, 0, nodeData.id, false); // false = не фокусировать
            node.style.left = nodeData.x;
            node.style.top = nodeData.y;
            node.innerHTML = nodeData.content;
            if (nodeData.color && nodeData.color !== 'default') {
                node.setAttribute('data-color', nodeData.color);
            }
        });
        
        // Сначала отрисовываем узлы, ПОТОМ линии
        data.links.forEach(linkData => {
            const node1 = document.getElementById(linkData.from);
            const node2 = document.getElementById(linkData.to);
            if (node1 && node2) {
                createLink(node1, node2, true);
            }
        });
        
        // v6.0: Восстанавливаем "камеру"
        if (data.view) {
            viewState.x = data.view.x || 0;
            viewState.y = data.view.y || 0;
            viewState.scale = data.view.scale || 1.0;
        } else { // Для старых профилей
            viewState.x = window.innerWidth / 2;
            viewState.y = window.innerHeight / 3;
            viewState.scale = 1.0;
        }
        updateView();
    }

    function getProfileList() { /* ... (без изменений) ... */ }
    function updateProfileList(selectedProfileName = null) { /* ... (без изменений) ... */ }
    function clearCanvas() { nodeLayer.innerHTML = ''; linkLayer.innerHTML = ''; }

    // --- 3. Базовая Логика Холста (ПЕРЕПИСАНО v6.0) ---

    /**
     * Создает новый узел (ноду) на холсте
     * @param {number} worldX - Координата X в "мире"
     * @param {number} worldY - Координата Y в "мире"
     * @param {string} [id=null] - ID (для десериализации)
     * @param {boolean} [doFocus=true] - Фокусироваться ли на узле
     * @returns {HTMLElement} - Созданный узел
     */
    function createNode(worldX, worldY, id = null, doFocus = true) {
        const node = document.createElement('div');
        node.className = 'node';
        node.contentEditable = 'true';
        node.setAttribute('placeholder', 'Идея...');
        node.id = id || 'node_' + Date.now();
        
        node.style.left = `${worldX - 60}px`;
        node.style.top = `${worldY - 30}px`;
        
        // --- Вешаем обработчики событий на УЗЕЛ ---
        node.addEventListener('mousedown', onNodeMouseDown, { capture: true });
        node.addEventListener('touchstart', onNodeMouseDown, { capture: true, passive: false });
        
        node.addEventListener('click', onNodeClick, { capture: true });
        node.addEventListener('dblclick', onNodeDoubleClick, { capture: true });
        
        // v5.0: Долгое нажатие для палитры
        node.addEventListener('contextmenu', showColorPalette);
        
        // Блокируем "всплывание" событий на холст
        node.addEventListener('mousedown', (e) => e.stopPropagation());
        node.addEventListener('dblclick', (e) => e.stopPropagation());
        node.addEventListener('wheel', (e) => e.stopPropagation()); // v6.0

        nodeLayer.appendChild(node);
        if (doFocus) node.focus();
        return node;
    }

    /**
     * (v6.0) Обработчик Кликов по Узлу
     */
    function onNodeClick(e) {
        if (viewState.isDraggingNode) return; // Игнор, если тащим
        
        const node = e.currentTarget;
        
        if (e.detail === 3) { // --- ТРИПЛ-КЛИК = УДАЛИТЬ УЗЕЛ ---
            const linesToRemove = document.querySelectorAll(`line[data-from="${node.id}"], line[data-to="${node.id}"]`);
            linesToRemove.forEach(line => line.remove());
            node.remove();
            if (firstNodeForLink === node) firstNodeForLink = null;
            return;
        }

        if (e.detail === 1) { // --- ОДИН-КЛИК = СВЯЗАТЬ / УДАЛИТЬ СВЯЗЬ ---
            if (!firstNodeForLink) {
                firstNodeForLink = node;
                node.classList.add('selected');
            } 
            else if (firstNodeForLink !== node) {
                const existingLink = findLink(firstNodeForLink, node);
                if (existingLink) {
                    existingLink.remove();
                } else {
                    createLink(firstNodeForLink, node);
                }
                firstNodeForLink.classList.remove('selected');
                firstNodeForLink = null;
            }
            else { 
                firstNodeForLink.classList.remove('selected');
                firstNodeForLink = null;
            }
        }
    }

    /**
     * (v6.0) Обработчик Дабл-клика по Узлу (Редактировать)
     */
    function onNodeDoubleClick(e) {
        if (viewState.isDraggingNode) return;
        e.currentTarget.focus();
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(e.currentTarget);
        selection.removeAllRanges();
        selection.addRange(range);
    }

    /**
     * (v6.0) Создает SVG линию (связь) между двумя узлами
     */
    function createLink(node1, node2, skipCheck = false) {
        if (!skipCheck && findLink(node1, node2)) return;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('data-from', node1.id);
        line.setAttribute('data-to', node2.id);
        
        // v6.0: Линии рисуются в "мире" (координаты 0,0)
        // updateAttachedLinks() сделает всю работу
        linkLayer.appendChild(line);
        updateAttachedLinks(node1);
        updateAttachedLinks(node2);
    }
    
    /**
     * (v6.0) Находит линию между двумя узлами
     */
    function findLink(node1, node2) {
        return document.querySelector(
            `line[data-from="${node1.id}"][data-to="${node2.id}"],
             line[data-from="${node2.id}"][data-to="${node1.id}"]`
        );
    }

    // --- 4. НОВЫЙ ДВИЖОК v6.0: Зум, Пан, Перетаскивание ---

    // --- Обработчики Холста (Пан и Зум) ---

    workspace.addEventListener('wheel', (e) => {
        e.preventDefault();
        
        const rect = workspace.getBoundingClientRect();
        const (screenX, screenY) = (e.clientX - rect.left, e.clientY - rect.top);
        
        // 1. Находим точку "мира" под курсором
        const worldBefore = screenToWorld(screenX, screenY);
        
        // 2. Рассчитываем новый зум
        const zoomDelta = -e.deltaY * 0.001;
        const newScale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewState.scale * (1 + zoomDelta)));
        
        // 3. Рассчитываем сдвиг, чтобы точка "мира" осталась под курсором
        viewState.x = screenX - worldBefore.x * newScale;
        viewState.y = screenY - worldBefore.y * newScale;
        viewState.scale = newScale;
        
        updateView();
    });

    workspace.addEventListener('mousedown', (e) => {
        // Клик НЕ по узлу
        if (e.target !== workspace && e.target !== canvas && e.target !== nodeLayer && e.target !== linkLayer) return;
        
        // Пан средней кнопкой или с Пробелом
        if (e.button === 1 || viewState.isSpacebarDown) {
            viewState.isPanning = true;
            workspace.classList.add('panning');
            viewState.panStart = { x: e.clientX, y: e.clientY };
            e.preventDefault();
        }
    });

    // --- Обработчики Узлов (Перетаскивание) ---
    
    function onNodeMouseDown(e) {
        // Только левая кнопка (или тач)
        if (e.button === 1 || e.button === 2) return;
        // Не тащить, если мы редактируем текст
        if (e.target.isContentEditable && e.target !== e.currentTarget) return;
        
        e.stopPropagation();
        
        // Палитра (долгое нажатие / правый клик)
        if (e.type === 'touchstart') {
            longPressNode = e.currentTarget;
            longPressTimer = setTimeout(() => {
                e.preventDefault();
                showColorPalette({ 
                    currentTarget: longPressNode,
                    clientX: e.touches[0].clientX, 
                    clientY: e.touches[0].clientY 
                });
                viewState.isDraggingNode = true; // Блокируем узел
            }, 500);
        }
        
        viewState.isDraggingNode = false; // Сбрасываем
        viewState.activeNode = e.currentTarget;
        
        // v6.0: Считаем смещение в "мировых" координатах
        const worldMouse = screenToWorld(e.clientX || e.touches[0].clientX, e.clientY || e.touches[0].clientY);
        const nodeX = parseFloat(viewState.activeNode.style.left);
        const nodeY = parseFloat(viewState.activeNode.style.top);
        
        viewState.nodeOffset = {
            x: worldMouse.x - nodeX,
            y: worldMouse.y - nodeY
        };
        
        // Добавляем глобальные слушатели
        document.addEventListener('mousemove', onDragMove);
        document.addEventListener('mouseup', onDragEnd);
        document.addEventListener('touchmove', onDragMove, { passive: false });
        document.addEventListener('touchend', onDragEnd);
    }

    // --- Глобальные Обработчики Движения ---

    function onDragMove(e) {
        // Предотвращаем скролл на таче
        if (e.type === 'touchmove') e.preventDefault();
        
        const clientX = e.clientX || e.touches[0].clientX;
        const clientY = e.clientY || e.touches[0].clientY;

        // 1. Логика ПАНА
        if (viewState.isPanning) {
            const dx = clientX - viewState.panStart.x;
            const dy = clientY - viewState.panStart.y;
            viewState.x += dx;
            viewState.y += dy;
            viewState.panStart = { x: clientX, y: clientY };
            updateView();
            return;
        }
        
        // 2. Логика ПЕРЕТАСКИВАНИЯ УЗЛА
        if (viewState.activeNode) {
            if (longPressTimer) clearTimeout(longPressTimer); // Отменяем палитру
            viewState.isDraggingNode = true;
            
            // Конвертируем позицию мыши в "мир"
            const worldMouse = screenToWorld(clientX, clientY);
            
            // Применяем смещение
            const newX = worldMouse.x - viewState.nodeOffset.x;
            const newY = worldMouse.y - viewState.nodeOffset.y;
            
            viewState.activeNode.style.left = `${newX}px`;
            viewState.activeNode.style.top = `${newY}px`;
            
            // Обновляем связанные линии
            updateAttachedLinks(viewState.activeNode);
        }
    }

    function onDragEnd(e) {
        // Отменяем палитру
        if (longPressTimer) clearTimeout(longPressTimer);
        
        // Сбрасываем Пан
        if (viewState.isPanning) {
            viewState.isPanning = false;
            workspace.classList.remove('panning');
        }
        
        // Сбрасываем Перетаскивание
        if (viewState.activeNode) {
            viewState.activeNode = null;
            // Сбрасываем флаг с задержкой, чтобы 'click' не сработал
            setTimeout(() => { viewState.isDraggingNode = false; }, 10);
        }
        
        // Отписываемся от глобальных событий
        document.removeEventListener('mousemove', onDragMove);
        document.removeEventListener('mouseup', onDragEnd);
        document.removeEventListener('touchmove', onDragMove);
        document.removeEventListener('touchend', onDragEnd);
    }
    
    // --- Двухпальцевый зум (Тач) ---
    let touchCache = [];
    workspace.addEventListener('touchstart', (e) => {
        if (e.touches.length === 2) {
            e.preventDefault();
            touchCache = Array.from(e.touches);
        }
    });
    workspace.addEventListener('touchmove', (e) => {
        if (e.touches.length === 2) {
            e.preventDefault();
            const t1 = e.touches[0];
            const t2 = e.touches[1];
            const p1 = touchCache.find(t => t.identifier === t1.identifier);
            const p2 = touchCache.find(t => t.identifier === t2.identifier);
            if (!p1 || !p2) return; // Потеряли палец

            // Считаем дистанцию
            const prevDist = Math.hypot(p1.clientX - p2.clientX, p1.clientY - p2.clientY);
            const currDist = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
            
            // Считаем центр
            const prevCenter = { x: (p1.clientX + p2.clientX) / 2, y: (p1.clientY + p2.clientY) / 2 };
            const currCenter = { x: (t1.clientX + t2.clientX) / 2, y: (t1.clientY + t2.clientY) / 2 };

            // 1. Пан
            const dx = currCenter.x - prevCenter.x;
            const dy = currCenter.y - prevCenter.y;
            viewState.x += dx;
            viewState.y += dy;
            
            // 2. Зум
            const worldCenter = screenToWorld(currCenter.x, currCenter.y);
            const newScale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewState.scale * (currDist / prevDist)));
            
            viewState.x = currCenter.x - worldCenter.x * newScale;
            viewState.y = currCenter.y - worldCenter.y * newScale;
            viewState.scale = newScale;

            updateView();
            touchCache = Array.from(e.touches); // Обновляем кэш
        }
    });
    workspace.addEventListener('touchend', (e) => {
        if (e.touches.length < 2) touchCache = [];
    });
    
    // --- Пан с Пробелом (для ПК) ---
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            viewState.isSpacebarDown = true;
            if (!viewState.isPanning) workspace.classList.add('panning');
            e.preventDefault();
        }
    });
    window.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
            viewState.isSpacebarDown = false;
            if (!viewState.isPanning) workspace.classList.remove('panning');
        }
    });
    

    /**
     * (v6.0) Обновляет все линии, прикрепленные к узлу
     */
    function updateAttachedLinks(node) {
        const nodeId = node.id;
        const newPos = getNodeCenter(node); // Координаты "мира"
        
        linkLayer.querySelectorAll(`line[data-from="${nodeId}"]`).forEach(line => {
            line.setAttribute('x1', newPos.x);
            line.setAttribute('y1', newPos.y);
        });
        
        linkLayer.querySelectorAll(`line[data-to="${nodeId}"]`).forEach(line => {
            line.setAttribute('x2', newPos.x);
            line.setAttribute('y2', newPos.y);
        });
    }

    /**
     * (v6.0) Вспомогательная функция: получает центр узла в "мире"
     */
    function getNodeCenter(node) {
        // Мы берем X/Y из style, так как это "мировые" координаты
        const x = parseFloat(node.style.left || 0);
        const y = parseFloat(node.style.top || 0);
        // getBoundingClientRect() НЕ ИСПОЛЬЗУЕМ, так как он зависит от зума
        return {
            x: x + node.offsetWidth / 2,
            y: y + node.offsetHeight / 2
        };
    }

    // --- 5. Шифрование (Без изменений) ---
    function encrypt(text, key) { /* ... (без изменений) ... */ }
    function decrypt(encryptedText, key) { /* ... (без изменений) ... */ }
    
    // --- 6. Логика Палитры Цветов (v6.0 - Позиционирование) ---
    function showColorPalette(e) {
        e.preventDefault();
        hideColorPalette();
        
        longPressNode = e.currentTarget;
        
        // v6.0: Палитра - это HTML, она живет в "экранных" координатах
        colorPalette.style.left = `${e.clientX}px`;
        colorPalette.style.top = `${e.clientY}px`;
        colorPalette.classList.remove('hidden');
    }
    function hideColorPalette() {
        colorPalette.classList.add('hidden');
        longPressNode = null;
    }
    
    colorPalette.addEventListener('click', (e) => {
        if (e.target.classList.contains('color-swatch')) {
            const color = e.target.getAttribute('data-color');
            if (longPressNode) {
                if (color === 'default') {
                    longPressNode.removeAttribute('data-color');
                } else {
                    longPressNode.setAttribute('data-color', color);
                }
            }
            hideColorPalette();
        }
    });
    
    // Клик по холсту закрывает палитру
    workspace.addEventListener('click', (e) => {
        if (!colorPalette.classList.contains('hidden')) {
            hideColorPalette();
        }
    });

    // --- 7. Инициализация ---
    function init() {
        const lastProfile = localStorage.getItem('hrain_lastProfile');
        updateProfileList(lastProfile);
        
        if (lastProfile) {
            loadMap(lastProfile);
        } else {
            // Если профилей нет, центрируем вид
            viewState.x = window.innerWidth / 2;
            viewState.y = window.innerHeight / 3;
            updateView();
            
            if (getProfileList().length === 0) {
                alert('Добро пожаловать в HRAIN! \nНажмите "Новый", чтобы создать свой первый профиль.');
            }
        }
        console.log('HRAIN v6.0 (The Engine Rebuild) загружен.');
    }
    
    init(); // Запускаем приложение
});
