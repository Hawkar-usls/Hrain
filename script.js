document.addEventListener('DOMContentLoaded', (event) => {
    
    // --- 1. АВАРИЙНАЯ ПРОВЕРКА LOCAL STORAGE ---
    function isLocalStorageAvailable() {
        try {
            const testKey = 'test_hrain_storage';
            localStorage.setItem(testKey, testKey);
            localStorage.removeItem(testKey);
            return true;
        } catch (e) {
            return false;
        }
    }
    
    if (!isLocalStorageAvailable()) {
        alert("Внимание: Ваш браузер блокирует сохранение данных (Local Storage)! Работа в 'Приватном просмотре' невозможна.");
    }
    
    // --- 2. КОНСТАНТЫ И ЭЛЕМЕНТЫ ИНТЕРФЕЙСА ---
    const PROFILE_LIST_KEY = 'hrain_profiles_list'; 
    let CURRENT_PROFILE_KEY = 'Default'; 
    
    const workspace = document.getElementById('workspace');
    const canvas = document.getElementById('canvas');
    const svgLayer = document.getElementById('link-layer'); // НОВЫЙ ЭЛЕМЕНТ SVG
    const profileSelect = document.getElementById('profile-select');
    
    // Элементы Аналитики
    const nodeCountSpan = document.getElementById('node-count');
    const linkCountSpan = document.getElementById('link-count');
    const dominantNodesList = document.getElementById('dominant-nodes');
    const influenceTypeSelect = document.getElementById('influence-type-select');

    // --- 3. ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
    let nodeIdCounter = 0;
    let connectingNodeId = null; 
    let currentZoom = 1; 
    let panX = 0; 
    let panY = 0; 
    
    const zoomStep = 0.1; 
    const minZoom = 0.5;  
    const maxZoom = 3.0; 
    const nodeScaleStep = 0.2; 
    
    // ... (Остальные переменные для Мыши/Touch/Тапа - ОСТАВЛЯЕМ КАК БЫЛО) ...
    let isPanning = false; 
    let isDraggingNode = false; 
    let currentDraggedNode = null;
    let lastClientX = 0; 
    let lastClientY = 0; 
    let activeTouches = []; 
    let initialDistance = 0; 
    let initialZoom = 1;
    let lastTapWorkspace = 0;
    let lastTapNode = 0;
    let lastTapLink = 0;
    // ---

    // --- 4. ФУНКЦИИ БЕЗОПАСНОГО ВЗАИМОДЕЙСТВИЯ С ХРАНИЛИЩЕМ ---
    function safeGetItem(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
    }
    function safeSetItem(key, value) {
        try { localStorage.setItem(key, value); return true; } catch (e) { return false; }
    }

    // --- 5. УПРАВЛЕНИЕ ПРОФИЛЯМИ С ПАРОЛЕМ ---
    
    function getProfileList() {
        const listJson = safeGetItem(PROFILE_LIST_KEY);
        let list;
        
        try {
             list = listJson ? JSON.parse(listJson) : [];
             if (!Array.isArray(list)) list = []; 
        } catch (e) {
             list = []; 
        }

        let convertedList = list.map(item => {
            if (typeof item === 'string') {
                return { name: item, password: null };
            }
            return item;
        });

        if (!convertedList.find(p => p.name === 'Default')) {
            convertedList.unshift({ name: 'Default', password: null });
        }
        
        const defaultProfile = convertedList.find(p => p.name === 'Default');
        if (defaultProfile) defaultProfile.password = null;

        return convertedList;
    }

    function saveProfileList(list) {
        safeSetItem(PROFILE_LIST_KEY, JSON.stringify(list));
    }

    function updateProfileSelect(activeProfileName) {
        const profileList = getProfileList();
        profileSelect.innerHTML = ''; 
        
        profileList.forEach(p => {
            const option = document.createElement('option');
            option.textContent = p.password ? `${p.name} 🔒` : p.name;
            option.value = p.name; 
            if (p.name === activeProfileName) {
                option.selected = true;
                CURRENT_PROFILE_KEY = p.name; 
            }
            profileSelect.appendChild(option);
        });
        
        document.getElementById('deleteProfileButton').disabled = profileList.length <= 1;
    }
    
    // ... (handleNewProfile, handleDeleteProfile, handleProfileChange - ОСТАВЛЯЕМ КАК БЫЛО) ...
    function handleNewProfile() { /* ... */ }
    function handleDeleteProfile() { /* ... */ }
    function handleProfileChange() { /* ... */ }

    // --- 6. ФУНКЦИИ СОХРАНЕНИЯ/ЗАГРУЗКИ ---
    function applyTransform() {
        // Применяем transform к canvas
        canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
        
        // Применяем zoom к SVG слою, но не pan (он уже привязан к top:0, left:0)
        svgLayer.style.transform = `scale(${currentZoom})`;
        svgLayer.style.transformOrigin = '0 0';
        
        // Смещаем SVG, чтобы компенсировать pan на рабочем пространстве
        svgLayer.style.left = `${panX}px`;
        svgLayer.style.top = `${panY}px`;
    }
    
    function createInitialState() {
        return { 
            nodes: {}, 
            links: [], 
            zoom: 1, 
            panX: 0, 
            panY: 0,
            influenceType: 'importance' // НОВАЯ ПЕРЕМЕННАЯ
        };
    }
    
    function clearWorkspace() {
        canvas.innerHTML = '';
        svgLayer.innerHTML = ''; // Очищаем SVG
        nodeIdCounter = 0; 
        connectingNodeId = null;
    }
    
    function saveState() {
        const stateKey = CURRENT_PROFILE_KEY;
        
        const nodesData = {};
        document.querySelectorAll('.node').forEach(nodeEl => {
            const id = nodeEl.id;
            nodesData[id] = {
                id: id,
                text: nodeEl.querySelector('input').value,
                x: nodeEl.offsetLeft,
                y: nodeEl.offsetTop,
                connections: JSON.parse(nodeEl.dataset.connections),
                nodeScale: parseFloat(nodeEl.dataset.scale || 1),
                // НОВОЕ: сохраняем цвет влияния
                influenceColor: nodeEl.dataset.influenceColor || 'default' 
            };
        });

        const linksData = [];
        const uniqueLinks = new Set();
        document.querySelectorAll('.node').forEach(nodeEl => {
            const sourceId = nodeEl.id;
            const targetIds = JSON.parse(nodeEl.dataset.connections);
            targetIds.forEach(targetId => {
                const linkKey = [sourceId, targetId].sort().join('-');
                if (!uniqueLinks.has(linkKey)) {
                    linksData.push({ source: sourceId, target: targetId });
                    uniqueLinks.add(linkKey);
                }
            });
        });

        const state = {
            nodes: nodesData,
            links: linksData,
            zoom: currentZoom,
            panX: panX, 
            panY: panY,
            influenceType: influenceTypeSelect.value // НОВОЕ: сохраняем тип влияния
        };
        safeSetItem(stateKey, JSON.stringify(state));
    }
    
    function loadState(profileName) {
        clearWorkspace(); 

        CURRENT_PROFILE_KEY = profileName || CURRENT_PROFILE_KEY;
        
        const savedState = safeGetItem(CURRENT_PROFILE_KEY);
        
        if (!savedState) {
            // Если профиль пуст
            const initialState = createInitialState();
            safeSetItem(CURRENT_PROFILE_KEY, JSON.stringify(initialState));
            currentZoom = 1; panX = 0; panY = 0; applyTransform();
            createNode(50, 50, `Карта: ${CURRENT_PROFILE_KEY}`); 
            influenceTypeSelect.value = initialState.influenceType;
            saveState(); 
            return;
        }
        
        const state = JSON.parse(savedState);
        
        influenceTypeSelect.value = state.influenceType || 'importance'; // НОВОЕ
        
        let maxId = 0;
        Object.values(state.nodes || {}).forEach(data => {
            // НОВОЕ: передаем influenceColor при создании
            createNode(data.x, data.y, data.text, data.id, data.connections, data.nodeScale, data.influenceColor); 
            const currentIdNum = parseInt(data.id.replace('node-', ''));
            if (currentIdNum > maxId) maxId = currentIdNum;
        });

        nodeIdCounter = maxId;

        (state.links || []).forEach(link => {
            if (document.getElementById(link.source) && document.getElementById(link.target)) {
                createLink(link.source, link.target);
            }
        });
        
        currentZoom = state.zoom || 1;
        panX = state.panX || 0;
        panY = state.panY || 0;
        
        applyTransform();
        updateProfileSelect(CURRENT_PROFILE_KEY);
        
        // Обновляем сферы влияния и аналитику после загрузки
        document.querySelectorAll('.node').forEach(node => {
            updateNodeInfluence(node.id);
        });
        updateAnalytics();
    }
    
    // --- 7. ФУНКЦИИ УЗЛОВ, СВЯЗЕЙ И ВЛИЯНИЯ ---
    
    // Новая функция для расчета и применения сферы влияния
    function updateNodeInfluence(nodeId) {
        const node = document.getElementById(nodeId);
        if (!node) return;
        
        const connections = JSON.parse(node.dataset.connections || '[]');
        const connectionCount = connections.length / 2; // Количество уникальных связей
        const influenceType = influenceTypeSelect.value;
        const influenceColor = node.dataset.influenceColor || 'default'; // Текущий цвет

        // 1. Убираем ВСЕ классы влияния и цвета
        node.classList.remove('influence-importance-low', 'influence-importance-medium', 'influence-importance-high', 
                                'flow-color', 'emotion-color', 'custom-color');

        // 2. Применяем КЛАСС ВЛИЯНИЯ (зависит от количества связей)
        if (connectionCount >= 6) {
            node.classList.add(`influence-importance-high`);
        } else if (connectionCount >= 4) {
            node.classList.add(`influence-importance-medium`);
        } else if (connectionCount >= 2) {
            node.classList.add(`influence-importance-low`);
        }

        // 3. Применяем КЛАСС ЦВЕТА (зависит от выбранного типа)
        if (influenceType === 'flow') {
            node.classList.add('flow-color');
        } else if (influenceType === 'emotion') {
            node.classList.add('emotion-color');
        }
        
        // Обновляем аналитику после изменения влияния
        updateAnalytics();
    }
    
    // ... (updateNodeSize, changeNodeScale - ОСТАВЛЯЕМ КАК БЫЛО) ...
    function updateNodeSize(node, scale) { /* ... */ }
    function changeNodeScale(nodeId, direction) { /* ... */ }
    
    function createNode(x, y, initialText = '', id = null, connections = [], nodeScale = 1, influenceColor = 'default') { 
        // ... (Создание узла, ID, позиции, input и scale-buttons - ОСТАВЛЯЕМ КАК БЫЛО) ...
        const nodeId = id || `node-${++nodeIdCounter}`;
        if (!id) nodeIdCounter = parseInt(nodeId.replace('node-', '')); 
        
        const node = document.createElement('div');
        node.className = 'node';
        node.id = nodeId;
        node.style.left = `${x}px`;
        node.style.top = `${y}px`;
        node.dataset.connections = JSON.stringify(connections); 
        node.dataset.scale = nodeScale; 
        node.dataset.influenceColor = influenceColor; // НОВОЕ: сохранение цвета
        
        updateNodeSize(node, nodeScale);
        
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Mind'; 
        input.value = initialText; 
        input.addEventListener('change', saveState); 
        input.addEventListener('blur', saveState);
        // НОВОЕ: Автомасштабирование шрифта
        function updateFontSize() {
            const scale = parseFloat(node.dataset.scale || 1);
            input.style.fontSize = `${1.1 * Math.sqrt(scale)}em`; // Нелинейный рост
        }
        input.addEventListener('input', updateFontSize);
        node.appendChild(input);
        updateFontSize(); 

        const scaleUpButton = document.createElement('button');
        scaleUpButton.textContent = '+';
        scaleUpButton.className = 'scale-button';
        scaleUpButton.style.position = 'absolute';
        scaleUpButton.style.right = '-25px';
        scaleUpButton.style.top = '0';
        scaleUpButton.onclick = (e) => { e.stopPropagation(); changeNodeScale(nodeId, 1); updateFontSize(); };
        node.appendChild(scaleUpButton);

        const scaleDownButton = document.createElement('button');
        scaleDownButton.textContent = '-';
        scaleDownButton.className = 'scale-button';
        scaleDownButton.style.position = 'absolute';
        scaleDownButton.style.right = '-25px';
        scaleDownButton.style.bottom = '0';
        scaleDownButton.onclick = (e) => { e.stopPropagation(); changeNodeScale(nodeId, -1); updateFontSize(); };
        node.appendChild(scaleDownButton);
        
        canvas.appendChild(node);
        
        // ... (Остальные обработчики событий - ОСТАВЛЯЕМ КАК БЫЛО) ...
        node.addEventListener('mousedown', startNodeDrag);
        node.addEventListener('dblclick', (e) => { e.stopPropagation(); deleteNodeAndConnections(nodeId); });
        node.addEventListener('touchend', (e) => { /* ... */ });
        node.addEventListener('click', (e) => {
            if (isDraggingNode) return; 
            e.stopPropagation(); 
            document.querySelectorAll('.node').forEach(n => n.classList.remove('selected-for-delete'));
            handleNodeConnect(nodeId);
        });
        
        return node;
    }
    
    // ... (handleNodeConnect, findNodeBoundaryPoint - ОСТАВЛЯЕМ КАК БЫЛО) ...
    function handleNodeConnect(nodeId) { /* ... */ }
    function findNodeBoundaryPoint(node, targetPoint) { /* ... */ return point; }
    
    
    /**
     * НОВАЯ ФУНКЦИЯ: Рисует изогнутую линию Безье с маркером-стрелкой.
     * Использует SVG вместо DIV.
     */
    function createLink(sourceId, targetId) {
        // Уникальный ключ для линии
        const linkKey = [sourceId, targetId].sort().join('-'); 
        
        // Удаляем старые элементы
        document.querySelectorAll(`#${linkKey}, .${linkKey}-arrow`).forEach(el => el.remove());
        
        const sourceNode = document.getElementById(sourceId);
        const targetNode = document.getElementById(targetId);
        
        if (!sourceNode || !targetNode) return; 

        // Центры узлов
        const getCenterCoords = (node) => {
            const scale = parseFloat(node.dataset.scale || 1);
            return {
                x: node.offsetLeft + (node.offsetWidth * scale) / 2,
                y: node.offsetTop + (node.offsetHeight * scale) / 2
            };
        };

        const sourceCenter = getCenterCoords(sourceNode);
        const targetCenter = getCenterCoords(targetNode);
        
        // Находим точки на границах узлов
        const p1 = findNodeBoundaryPoint(sourceNode, targetCenter); 
        const p2 = findNodeBoundaryPoint(targetNode, sourceCenter); 
        
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        
        // Расчет контрольной точки для кривой Безье
        const midX = (p1.x + p2.x) / 2;
        const midY = (p1.y + p2.y) / 2;
        
        // Смещение: 25% от расстояния, перпендикулярно линии
        const offset = Math.sqrt(dx * dx + dy * dy) * 0.25; 
        
        // Перпендикулярное смещение
        const cx = midX + dy * offset / Math.sqrt(dx * dx + dy * dy);
        const cy = midY - dx * offset / Math.sqrt(dx * dx + dy * dy);
        
        // Путь SVG (Quadratic Bezier Curve)
        const pathData = `M${p1.x},${p1.y} Q${cx},${cy} ${p2.x},${p2.y}`;
        
        // --- 1. Создаем Path (Кривая) ---
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', pathData);
        path.setAttribute('class', 'link-path');
        path.setAttribute('id', linkKey);
        path.setAttribute('data-source', sourceId);
        path.setAttribute('data-target', targetId);
        path.setAttribute('data-id', linkKey);
        svgLayer.appendChild(path);

        // --- 2. Создаем Стрелку (Треугольник) ---
        
        // Функция для получения точки на пути (для размещения стрелки)
        const getPointOnPath = (path, t) => {
            const Bx = (1 - t) * p1.x + t * cx;
            const By = (1 - t) * p1.y + t * cy;
            const Cx = (1 - t) * cx + t * p2.x;
            const Cy = (1 - t) * cy + t * p2.y;
            return {
                x: (1 - t) * Bx + t * Cx,
                y: (1 - t) * By + t * Cy
            };
        };
        
        // Стрелка будет на 90% пути
        const arrowPoint = getPointOnPath(path, 0.9);
        const tangentPoint = getPointOnPath(path, 0.89); 
        const angle = Math.atan2(arrowPoint.y - tangentPoint.y, arrowPoint.x - tangentPoint.x) * (180 / Math.PI);
        
        const arrowSize = 6;
        
        const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        arrow.setAttribute('class', `link-arrow ${linkKey}-arrow`);
        arrow.setAttribute('points', `0,0 ${arrowSize * 2},${arrowSize} 0,${arrowSize * 2}`);
        arrow.setAttribute('transform', 
            `translate(${arrowPoint.x - arrowSize}, ${arrowPoint.y - arrowSize}) rotate(${angle})`
        );
        svgLayer.appendChild(arrow);
        
        // --- 3. Обработчики для удаления (добавляем к path) ---
        const deleteLinkHandler = (e) => {
             e.stopPropagation(); 
             // На SVG элементе data-source и data-target уже есть
             const sId = path.dataset.source;
             const tId = path.dataset.target;
             if (sId && tId) { deleteLink(sId, tId); }
        };

        path.addEventListener('dblclick', deleteLinkHandler); // ПК
        
        path.addEventListener('touchend', (e) => { // Touch
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTapLink;
            
            if (tapLength < 500 && tapLength > 50 && e.touches.length === 0) {
                 deleteLinkHandler(e);
            }
            lastTapLink = currentTime;
        });
        
        // Важно: обновляем аналитику
        updateAnalytics();
    }

    function updateAllConnections(movedNodeId) {
        // Находим все узлы, которые связаны с перемещенным
        const connectedNodes = [];
        document.querySelectorAll('.node').forEach(node => {
            if (JSON.parse(node.dataset.connections).includes(movedNodeId)) {
                connectedNodes.push(node.id);
            }
        });
        
        // Перерисовываем связи для перемещенного узла
        connectedNodes.forEach(otherNodeId => {
            createLink(movedNodeId, otherNodeId);
        });
        
        // Перерисовываем связи, исходящие из него
        JSON.parse(document.getElementById(movedNodeId).dataset.connections).forEach(targetId => {
             createLink(movedNodeId, targetId);
        });

        // Так как createLink удаляет старую линию, это безопасно.
    }
    
    function deleteLink(sourceId, targetId) {
        const linkKey = [sourceId, targetId].sort().join('-');
        const line = document.getElementById(linkKey);
        if (!line) return;
        
        const sId = line.dataset.source;
        const tId = line.dataset.target; 
        
        // Удаляем SVG элементы
        document.getElementById(linkKey)?.remove();
        document.querySelector(`.${linkKey}-arrow`)?.remove();

        const sourceNode = document.getElementById(sId);
        const targetNode = document.getElementById(tId);

        // Обновляем connections
        if (sourceNode) {
            let sConnections = JSON.parse(sourceNode.dataset.connections);
            sourceNode.dataset.connections = JSON.stringify(sConnections.filter(id => id !== tId));
            updateNodeInfluence(sId); 
        }

        if (targetNode) {
            let tConnections = JSON.parse(targetNode.dataset.connections);
            targetNode.dataset.connections = JSON.stringify(tConnections.filter(id => id !== sId));
            updateNodeInfluence(tId); 
        }
        
        saveState();
    }

    function deleteNodeAndConnections(nodeId) {
        // ... (Старая логика удаления узла - ОСТАВЛЯЕМ КАК БЫЛО) ...
        const node = document.getElementById(nodeId);
        if (!node) return;

        // Удаляем SVG линии, связанные с узлом
        document.querySelectorAll('.link-path').forEach(path => {
            if (path.dataset.source === nodeId || path.dataset.target === nodeId) {
                const linkKey = path.getAttribute('id');
                document.querySelector(`#${linkKey}`)?.remove();
                document.querySelector(`.${linkKey}-arrow`)?.remove();
            }
        });

        document.querySelectorAll('.node').forEach(otherNode => {
            const newConnections = JSON.parse(otherNode.dataset.connections).filter(id => id !== nodeId);
            if (newConnections.length !== JSON.parse(otherNode.dataset.connections).length) {
                otherNode.dataset.connections = JSON.stringify(newConnections);
                updateNodeInfluence(otherNode.id); 
            }
        });
        
        node.remove();
        if (connectingNodeId === nodeId) { connectingNodeId = null; }
        
        updateAnalytics();
        saveState(); 
    }
    
    // --- 8. ФУНКЦИИ АНАЛИТИКИ И СТАТИСТИКИ ---
    
    function updateAnalytics() {
        const nodes = document.querySelectorAll('.node');
        const links = document.querySelectorAll('.link-path');
        
        nodeCountSpan.textContent = nodes.length;
        linkCountSpan.textContent = links.length;
        
        const influenceData = [];
        
        nodes.forEach(node => {
            const connections = JSON.parse(node.dataset.connections || '[]');
            const connectionCount = connections.length / 2;
            
            // Собираем данные для топа доминирования
            influenceData.push({
                id: node.id,
                text: node.querySelector('input').value || `Узел ${node.id.replace('node-', '')}`,
                count: connectionCount
            });
        });
        
        // Сортируем и выбираем Топ-3
        influenceData.sort((a, b) => b.count - a.count);
        const dominant = influenceData.slice(0, 3).filter(item => item.count > 0);
        
        dominantNodesList.innerHTML = '';
        if (dominant.length === 0) {
            dominantNodesList.innerHTML = '<li>Нет связей</li>';
        } else {
            dominant.forEach(item => {
                const li = document.createElement('li');
                li.textContent = `${item.text} (${item.count} с.)`;
                dominantNodesList.appendChild(li);
            });
        }
    }

    // --- 9. УНИФИЦИРОВАННЫЕ ФУНКЦИИ ВЗАИМОДЕЙСТВИЯ (МЫШЬ И ТАЧ) ---
    
    // ... (Все функции drag, pan, zoom - ОСТАВЛЯЕМ КАК БЫЛО, но с поправкой на applyTransform) ...
    function getDistance(touches) { /* ... */ }
    function getCenter(touches) { /* ... */ }
    function handleTouchStart(e) { /* ... */ }
    function handleTouchMove(e) { 
        // Если перетаскиваем, обновляем связи
        if (isDraggingNode && currentDraggedNode) {
            // ... (логика drag) ...
            updateAllConnections(currentDraggedNode.id); 
        }
        // ... (логика pan и zoom) ...
        applyTransform();
    }
    function handleTouchEnd(e) { /* ... */ }
    function startNodeDrag(e) { /* ... */ }
    function dragNode(e) { 
        // ... (логика drag) ...
        updateAllConnections(currentDraggedNode.id); 
    }
    function stopNodeDrag() { /* ... */ }
    function startPanning(e) { /* ... */ }
    function panCanvasMouse(e) { /* ... */ applyTransform(); }
    function stopPanning() { /* ... */ }
    function handleZoom(e) { /* ... */ applyTransform(); saveState(); }


    // --- 10. ИНИЦИАЛИЗАЦИЯ И РЕГИСТРАЦИЯ ВСЕХ СОБЫТИЙ ---

    function setupEventListeners() {
        // ... (События Профилей и Подсказок - ОСТАВЛЯЕМ КАК БЫЛО) ...
        document.getElementById('profile-select').addEventListener('change', handleProfileChange);
        document.getElementById('newProfileButton').addEventListener('click', handleNewProfile);
        document.getElementById('deleteProfileButton').addEventListener('click', handleDeleteProfile);
        document.getElementById('saveProfileButton').addEventListener('click', saveState);

        // НОВОЕ: Обработка смены типа влияния
        influenceTypeSelect.addEventListener('change', () => {
            document.querySelectorAll('.node').forEach(node => updateNodeInfluence(node.id));
            saveState();
        });
        
        // ... (События Создания Узлов, Touch, Pan, Zoom - ОСТАВЛЯЕМ КАК БЫЛО) ...
        workspace.addEventListener('dblclick', (e) => { /* ... */ });
        workspace.addEventListener('touchend', (e) => { /* ... */ }, false);
        workspace.addEventListener('touchstart', handleTouchStart, { passive: false });
        document.addEventListener('keydown', (e) => { /* ... */ });
        document.addEventListener('keyup', (e) => { /* ... */ });
        workspace.addEventListener('mousedown', startPanning); 
        workspace.addEventListener('wheel', handleZoom, { passive: false });
    }

    // --- 11. ПЕРВИЧНАЯ ЗАГРУЗКА ---
    function initialize() {
        setupEventListeners();
        
        const profileList = getProfileList();
        updateProfileSelect(profileList[0].name);
        loadState(profileList[0].name);
    }
    
    initialize(); 
});
