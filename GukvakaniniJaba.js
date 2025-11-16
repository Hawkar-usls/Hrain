// == HRAIN v6.2 (FATAL BUG HOTFIX) ==
// Полный JS-файл от 16.11.2025
// ИСПРАВЛЕНО: Фатальная ошибка синтаксиса в v6.1, которая "убивала" весь скрипт.
// ИСПРАВЛЕНО: Полностью переписана логика пана/зума/создания, чтобы убрать баги.

// --- v6.2: "Страховка" от ошибок ---
try {

document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Получаем все наши HTML-элементы ---
    const workspace = document.getElementById('workspace');
    const canvas = document.getElementById('canvas');
    const nodeLayer = document.getElementById('node-layer');
    const linkLayer = document.getElementById('link-layer');
    
    // ... (все остальные getElementById без изменений) ...
    const profileSelect = document.getElementById('profile-select');
    const saveBtn = document.getElementById('saveProfileButton');
    const newBtn = document.getElementById('newProfileButton');
    const deleteBtn = document.getElementById('deleteProfileButton');
    const importBtn = document.getElementById('importProfileButton');
    const exportBtn = document.getElementById('exportProfileButton');
    const fileImporter = document.getElementById('file-importer');   
    const pinBackdrop = document.getElementById('pin-modal-backdrop');
    const pinInput = document.getElementById('pin-input');
    const pinError = document.getElementById('pin-error');
    const pinCancelBtn = document.getElementById('pin-cancel-btn');
    const pinOkBtn = document.getElementById('pin-ok-btn');
    const colorPalette = document.getElementById('color-palette');

    // --- Глобальные переменные ---
    let firstNodeForLink = null;
    let longPressTimer = null;
    let longPressNode = null;
    let pinCallback = null;
    let lastTapTime = 0; // v6.2 Для дабл-тапа

    // --- ДВИЖОК v6.2: "КАМЕРА" ---
    let viewState = {
        x: 0, y: 0, scale: 1.0,
        isPanning: false,
        isDraggingNode: false,
        panStart: { x: 0, y: 0 },
        activeNode: null,
        nodeOffset: { x: 0, y: 0 },
        isSpacebarDown: false
    };

    const MIN_ZOOM = 0.1;
    const MAX_ZOOM = 4.0;
    
    function updateView() {
        viewState.scale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewState.scale));
        const transform = `translate(${viewState.x}px, ${viewState.y}px) scale(${viewState.scale})`;
        canvas.style.transform = transform;
    }

    function screenToWorld(screenX, screenY) {
        return {
            x: (screenX - viewState.x) / viewState.scale,
            y: (screenY - viewState.y) / viewState.scale
        };
    }
    
    // --- 2. Логика Профилей и Сохранения (Без изменений) ---
    // (Этот блок кода полностью рабочий, мы его не трогаем)

    newBtn.addEventListener('click', () => {
        const profileName = prompt('Введите имя нового профиля:');
        if (!profileName || profileName.trim() === '') return;
        const profiles = getProfileList();
        if (profiles.includes(profileName)) {
            alert('Ошибка: Профиль с таким именем уже существует.'); return;
        }
        profiles.push(profileName);
        localStorage.setItem('hrain_profiles', JSON.stringify(profiles));
        clearCanvas();
        viewState.x = window.innerWidth / 2; viewState.y = window.innerHeight / 3; viewState.scale = 1.0;
        updateView();
        saveMap(profileName, true);
    });
    saveBtn.addEventListener('click', () => {
        const profileName = profileSelect.value;
        if (!profileName) { alert('Сначала создайте или выберите профиль.'); return; }
        saveMap(profileName, false);
    });
    deleteBtn.addEventListener('click', () => {
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
    profileSelect.addEventListener('change', () => {
        const profileName = profileSelect.value;
        if (profileName) loadMap(profileName);
    });
    importBtn.addEventListener('click', () => fileImporter.click());
    fileImporter.addEventListener('change', (e) => {
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
    exportBtn.addEventListener('click', () => {
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
    function showPinPrompt(title, callback) { 
        document.getElementById('pin-title').textContent = title;
        pinInput.value = ''; pinError.textContent = '';
        pinCallback = callback;
        pinBackdrop.classList.remove('hidden');
        pinInput.focus();
    }
    pinCancelBtn.addEventListener('click', () => { pinBackdrop.classList.add('hidden'); pinCallback = null; });
    pinOkBtn.addEventListener('click', () => {
        const pin = pinInput.value;
        if (pin.length !== 4) { pinError.textContent = 'ПИН должен состоять из 4 цифр'; return; }
        if (pinCallback) pinCallback(pin);
        pinBackdrop.classList.add('hidden'); pinCallback = null;
    });
    function saveMap(profileName, isNew) {
        showPinPrompt(isNew ? 'Создайте 4-значный ПИН' : 'Введите 4-значный ПИН', (pin) => {
            const mapData = serializeMap();
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
            deserializeMap(mapData);
            localStorage.setItem('hrain_lastProfile', profileName);
            updateProfileList(profileName);
        });
    }
    function serializeMap() {
        const nodes = [];
        document.querySelectorAll('.node').forEach(node => {
            nodes.push({
                id: node.id, x: node.style.left, y: node.style.top,
                content: node.innerHTML, color: node.getAttribute('data-color') || 'default'
            });
        });
        const links = [];
        document.querySelectorAll('#link-layer line').forEach(line => {
            links.push({ from: line.getAttribute('data-from'), to: line.getAttribute('data-to') });
        });
        const view = { x: viewState.x, y: viewState.y, scale: viewState.scale };
        return JSON.stringify({ nodes, links, view });
    }
    function deserializeMap(jsonString) {
        clearCanvas();
        const data = JSON.parse(jsonString);
        data.nodes.forEach(nodeData => {
            const node = createNode(0, 0, nodeData.id, false);
            node.style.left = nodeData.x; node.style.top = nodeData.y;
            node.innerHTML = nodeData.content;
            if (nodeData.color && nodeData.color !== 'default') {
                node.setAttribute('data-color', nodeData.color);
            }
        });
        data.links.forEach(linkData => {
            const node1 = document.getElementById(linkData.from);
            const node2 = document.getElementById(linkData.to);
            if (node1 && node2) createLink(node1, node2, true);
        });
        if (data.view) {
            viewState.x = data.view.x || 0; viewState.y = data.view.y || 0; viewState.scale = data.view.scale || 1.0;
        } else {
            viewState.x = window.innerWidth / 2; viewState.y = window.innerHeight / 3; viewState.scale = 1.0;
        }
        updateView();
    }
    function getProfileList() { 
        const profiles = localStorage.getItem('hrain_profiles');
        return profiles ? JSON.parse(profiles) : [];
    }
    function updateProfileList(selectedProfileName = null) { 
        profileSelect.innerHTML = '';
        const profiles = getProfileList();
        if (profiles.length === 0) {
            const option = document.createElement('option');
            option.value = ''; option.textContent = 'Нет профилей';
            profileSelect.appendChild(option); return;
        }
        profiles.forEach(name => {
            const option = document.createElement('option');
            option.value = name; option.textContent = name;
            if (name === selectedProfileName) option.selected = true;
            profileSelect.appendChild(option);
        });
    }
    function clearCanvas() { nodeLayer.innerHTML = ''; linkLayer.innerHTML = ''; }

    // --- 3. Базовая Логика Холста (Без изменений) ---

    function createNode(worldX, worldY, id = null, doFocus = true) {
        const node = document.createElement('div');
        node.className = 'node';
        node.contentEditable = 'true';
        node.setAttribute('placeholder', 'Идея...');
        node.id = id || 'node_' + Date.now();
        node.style.left = `${worldX - 60}px`;
        node.style.top = `${worldY - 30}px`;
        
        node.addEventListener('mousedown', onNodeMouseDown); // Изменено
        node.addEventListener('touchstart', onNodeMouseDown, { passive: false }); // Изменено
        
        node.addEventListener('click', onNodeClick); // Изменено
        node.addEventListener('dblclick', onNodeDoubleClick); // Изменено
        
        node.addEventListener('contextmenu', showColorPalette);
        node.addEventListener('wheel', (e) => e.stopPropagation());

        nodeLayer.appendChild(node);
        if (doFocus) node.focus();
        return node;
    }
    function onNodeClick(e) {
        e.stopPropagation(); // v6.2
        if (viewState.isDraggingNode) return;
        const node = e.currentTarget;
        if (e.detail === 3) { // ТРИПЛ-КЛИК = УДАЛИТЬ УЗЕЛ
            const linesToRemove = document.querySelectorAll(`line[data-from="${node.id}"], line[data-to="${node.id}"]`);
            linesToRemove.forEach(line => line.remove());
            node.remove();
            if (firstNodeForLink === node) firstNodeForLink = null;
            return;
        }
        if (e.detail === 1) { // ОДИН-КЛИК = СВЯЗАТЬ / УДАЛИТЬ СВЯЗЬ
            if (!firstNodeForLink) {
                firstNodeForLink = node; node.classList.add('selected');
            } 
            else if (firstNodeForLink !== node) {
                const existingLink = findLink(firstNodeForLink, node);
                if (existingLink) { existingLink.remove(); }
                else { createLink(firstNodeForLink, node); }
                firstNodeForLink.classList.remove('selected');
                firstNodeForLink = null;
            }
            else { 
                firstNodeForLink.classList.remove('selected');
                firstNodeForLink = null;
            }
        }
    }
    function onNodeDoubleClick(e) {
        e.stopPropagation(); // v6.2
        if (viewState.isDraggingNode) return;
        e.currentTarget.focus();
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(e.currentTarget);
        selection.removeAllRanges();
        selection.addRange(range);
    }
    function createLink(node1, node2, skipCheck = false) {
        if (!skipCheck && findLink(node1, node2)) return;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('data-from', node1.id);
        line.setAttribute('data-to', node2.id);
        linkLayer.appendChild(line);
        updateAttachedLinks(node1);
        updateAttachedLinks(node2);
    }
    function findLink(node1, node2) {
        return document.querySelector(
            `line[data-from="${node1.id}"][data-to="${node2.id}"],
             line[data-from="${node2.id}"][data-to="${node1.id}"]`
        );
    }
    function updateAttachedLinks(node) {
        const nodeId = node.id;
        const newPos = getNodeCenter(node);
        linkLayer.querySelectorAll(`line[data-from="${nodeId}"]`).forEach(line => {
            line.setAttribute('x1', newPos.x); line.setAttribute('y1', newPos.y);
        });
        linkLayer.querySelectorAll(`line[data-to="${nodeId}"]`).forEach(line => {
            line.setAttribute('x2', newPos.x); line.setAttribute('y2', newPos.y);
        });
    }
    function getNodeCenter(node) {
        const x = parseFloat(node.style.left || 0);
        const y = parseFloat(node.style.top || 0);
        return { x: x + node.offsetWidth / 2, y: y + node.offsetHeight / 2 };
    }


    // --- 4. ДВИЖОК v6.2: Зум, Пан, Перетаскивание (НОВАЯ, ЧИСТАЯ ЛОГИКА) ---

    // --- Зум (Колесико) ---
    workspace.addEventListener('wheel', (e) => {
        e.preventDefault();
        
        // --- ЭТО БЫЛ ФАТАЛЬНЫЙ БАГ v6.1 ---
        // const (screenX, screenY) = (e.clientX - rect.left, e.clientY - rect.top);
        // --- ИСПРАВЛЕНИЕ v6.2 ---
        const rect = workspace.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        // --- КОНЕЦ ИСПРАВЛЕНИЯ ---

        const worldBefore = screenToWorld(screenX, screenY);
        const zoomDelta = -e.deltaY * 0.001;
        const newScale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewState.scale * (1 + zoomDelta)));
        
        viewState.x = screenX - worldBefore.x * newScale;
        viewState.y = screenY - worldBefore.y * newScale;
        viewState.scale = newScale;
        
        updateView();
    });

    // --- Создание Узла (Дабл-клик ПК) ---
    workspace.addEventListener('dblclick', (e) => {
        if (e.target !== workspace && e.target !== canvas && e.target !== nodeLayer && e.target !== linkLayer) return;
        if (viewState.isSpacebarDown) return; // Не создавать при панорамировании

        const worldPos = screenToWorld(e.clientX, e.clientY);
        createNode(worldPos.x, worldPos.y);
    });

    // --- Пан (ПК: Пробел, Колесико) ---
    workspace.addEventListener('mousedown', (e) => {
        if (e.target !== workspace && e.target !== canvas && e.target !== nodeLayer && e.target !== linkLayer) return;
        
        // Пан ТОЛЬКО средней кнопкой или с Пробелом
        if (e.button === 1 || viewState.isSpacebarDown) {
            viewState.isPanning = true;
            workspace.classList.add('panning');
            viewState.panStart = { x: e.clientX, y: e.clientY };
            e.preventDefault();
            
            document.addEventListener('mousemove', onDragMove);
            document.addEventListener('mouseup', onDragEnd);
        }
    });
    
    // --- Перетаскивание Узла (ПК) ---
    function onNodeMouseDown(e) {
        // e.button не существует в 'touchstart', поэтому проверяем тип
        if (e.type === 'mousedown' && (e.button === 1 || e.button === 2)) return; 
        if (e.target.isContentEditable && e.target !== e.currentTarget) return;
        
        e.stopPropagation();
        
        const clientX = e.clientX ?? e.touches[0].clientX;
        const clientY = e.clientY ?? e.touches[0].clientY;

        // Палитра (Долгое нажатие)
        if (e.type === 'touchstart') {
            longPressNode = e.currentTarget;
            longPressTimer = setTimeout(() => {
                e.preventDefault();
                showColorPalette({ 
                    currentTarget: longPressNode,
                    clientX: clientX, 
                    clientY: clientY 
                });
                viewState.isDraggingNode = true; // Блокируем узел
            }, 500);
        }
        
        viewState.isDraggingNode = false;
        viewState.activeNode = e.currentTarget;
        
        const worldMouse = screenToWorld(clientX, clientY);
        const nodeX = parseFloat(viewState.activeNode.style.left);
        const nodeY = parseFloat(viewState.activeNode.style.top);
        
        viewState.nodeOffset = { x: worldMouse.x - nodeX, y: worldMouse.y - nodeY };
        
        document.addEventListener('mousemove', onDragMove);
        document.addEventListener('mouseup', onDragEnd);
        document.addEventListener('touchmove', onDragMove, { passive: false }); // v6.2
        document.addEventListener('touchend', onDragEnd); // v6.2
    }
    
    // --- Логика Тач-скрина (Пан, Зум, Дабл-тап) ---
    workspace.addEventListener('touchstart', (e) => {
        // Клик по узлу? (onNodeMouseDown уже повешен на узел, он сработает сам)
        if (e.target.closest('.node')) {
            return;
        }

        // Клик по холсту
        e.preventDefault();

        if (e.touches.length === 1) {
            // --- Логика Дабл-тапа v6.2 ---
            const currentTime = new Date().getTime();
            const tapTimeDiff = currentTime - lastTapTime;
            
            if (tapTimeDiff < 300 && tapTimeDiff > 0) {
                // Это ДАБЛ-ТАП = Создать узел
                const worldPos = screenToWorld(e.touches[0].clientX, e.touches[0].clientY);
                createNode(worldPos.x, worldPos.y);
                lastTapTime = 0; // Сбрасываем
                viewState.isPanning = false; // Отменяем пан
            } else {
                // Это ОДИН ТАП = Начать ПАН
                viewState.isPanning = true;
                workspace.classList.add('panning');
                viewState.panStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
            }
            lastTapTime = currentTime; // Запоминаем время
            
        } else if (e.touches.length === 2) {
            // --- Логика ЗУМА ---
            touchCache = Array.from(e.touches);
            viewState.isPanning = false; // Отменяем пан
        }

        // Вешаем глобальные слушатели (onNodeMouseDown их тоже вешает)
        document.addEventListener('touchmove', onDragMove, { passive: false });
        document.addEventListener('touchend', onDragEnd);

    }, { passive: false });


    // --- Глобальные Обработчики Движения (Мышь + Тач) ---
    function onDragMove(e) {
        if (e.type === 'touchmove') e.preventDefault();
        
        const clientX = e.clientX ?? e.touches[0].clientX;
        const clientY = e.clientY ?? e.touches[0].clientY;

        // --- Двухпальцевый ЗУМ (только Тач) ---
        if (e.touches && e.touches.length === 2) {
            const t1 = e.touches[0];
            const t2 = e.touches[1];
            const p1 = touchCache.find(t => t.identifier === t1.identifier);
            const p2 = touchCache.find(t => t.identifier === t2.identifier);
            if (!p1 || !p2) { touchCache = Array.from(e.touches); return; }

            const prevDist = Math.hypot(p1.clientX - p2.clientX, p1.clientY - p2.clientY);
            const currDist = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
            const prevCenter = { x: (p1.clientX + p2.clientX) / 2, y: (p1.clientY + p2.clientY) / 2 };
            const currCenter = { x: (t1.clientX + t2.clientX) / 2, y: (t1.clientY + t2.clientY) / 2 };

            const dx = currCenter.x - prevCenter.x;
            const dy = currCenter.y - prevCenter.y;
            viewState.x += dx; viewState.y += dy;
            
            const worldCenter = screenToWorld(currCenter.x, currCenter.y);
            const newScale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewState.scale * (currDist / prevDist)));
            
            viewState.x = currCenter.x - worldCenter.x * newScale;
            viewState.y = currCenter.y - worldCenter.y * newScale;
            viewState.scale = newScale;

            updateView();
            touchCache = Array.from(e.touches);
            return;
        }
        
        // --- ПАН (Мышь + Тач 1 палец) ---
        if (viewState.isPanning) {
            const dx = clientX - viewState.panStart.x;
            const dy = clientY - viewState.panStart.y;
            viewState.x += dx; viewState.y += dy;
            viewState.panStart = { x: clientX, y: clientY };
            updateView();
            return;
        }
        
        // --- ПЕРЕТАСКИВАНИЕ УЗЛА (Мышь + Тач 1 палец) ---
        if (viewState.activeNode) {
            if (longPressTimer) clearTimeout(longPressTimer);
            viewState.isDraggingNode = true;
            
            const worldMouse = screenToWorld(clientX, clientY);
            const newX = worldMouse.x - viewState.nodeOffset.x;
            const newY = worldMouse.y - viewState.nodeOffset.y;
            
            viewState.activeNode.style.left = `${newX}px`;
            viewState.activeNode.style.top = `${newY}px`;
            
            updateAttachedLinks(viewState.activeNode);
        }
    }

    function onDragEnd(e) {
        if (longPressTimer) clearTimeout(longPressTimer);
        
        if (viewState.isPanning) {
            viewState.isPanning = false;
            workspace.classList.remove('panning');
        }
        
        if (viewState.activeNode) {
            viewState.activeNode = null;
            setTimeout(() => { viewState.isDraggingNode = false; }, 10);
        }
        
        if (e.touches && e.touches.length < 2) touchCache = [];
        
        document.removeEventListener('mousemove', onDragMove);
        document.removeEventListener('mouseup', onDragEnd);
        document.removeEventListener('touchmove', onDragMove);
        document.removeEventListener('touchend', onDragEnd);
    }
    
    // --- Пан с Пробелом (для ПК) ---
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && !e.repeat && !e.target.isContentEditable) {
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
    
    // --- 5. Шифрование (Без изменений) ---
    function encrypt(text, key) {
        let result = '';
        for (let i = 0; i < text.length; i++) {
            result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
        }
        return btoa(result);
    }
    function decrypt(encryptedText, key) {
        try {
            let text = atob(encryptedText); 
            let result = '';
            for (let i = 0; i < text.length; i++) {
                result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
            }
            return result;
        } catch (e) { return null; }
    }
    
    // --- 6. Логика Палитры Цветов (Без изменений) ---
    function showColorPalette(e) {
        e.preventDefault();
        hideColorPalette();
        longPressNode = e.currentTarget;
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
            viewState.x = window.innerWidth / 2;
            viewState.y = window.innerHeight / 3;
            updateView();
            if (getProfileList().length === 0) {
                alert('Добро пожаловать в HRAIN! \nНажмите "Новый", чтобы создать свой первый профиль.');
            }
        }
        console.log('HRAIN v6.2 (Event Fix) загружен.');
    }
    
    init(); // Запускаем приложение
});

// --- v6.2: "Страховка" от ошибок ---
} catch (e) {
    // Если что-то пошло не так, показываем ошибку
    alert('КРИТИЧЕСКАЯ ОШИБКА HRAIN:\n\n' + e.message + '\n\nПожалуйста, сообщи об этом разработчику.');
    // Визуально показываем, что всё сломалось
    const logo = document.getElementById('hrain-logo');
    if (logo) {
        logo.textContent = '🧠 HRAIN [FAILED]';
        logo.style.color = '#F44336';
    }
}
