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
        // Усиленное предупреждение
        alert("КРИТИЧЕСКАЯ ОШИБКА: Local Storage недоступен. Профили, карты и настройки НЕ БУДУТ сохраняться. Пожалуйста, отключите 'Приватный просмотр' (Safari/iOS) или убедитесь, что ваш браузер разрешает сохранение данных.");
    }
    
    // --- 2. КОНСТАНТЫ И ЭЛЕМЕНТЫ ИНТЕРФЕЙСА ---
    const PROFILE_LIST_KEY = 'hrain_profiles_list'; 
    let CURRENT_PROFILE_KEY = 'Default'; 
    
    const workspace = document.getElementById('workspace');
    const canvas = document.getElementById('canvas');
    const svgLayer = document.getElementById('link-layer'); 
    const profileSelect = document.getElementById('profile-select');
    
    // Элементы Аналитики
    const nodeCountSpan = document.getElementById('node-count');
    const linkCountSpan = document.getElementById('link-count');
    const dominantNodesList = document.getElementById('dominant-nodes');
    const influenceTypeSelect = document.getElementById('influence-type-select');
    
    // Новые элементы управления панелями
    const hintsPanel = document.getElementById('hints');
    const analyticsPanel = document.getElementById('analytics');
    const toggleHintsButton = document.getElementById('toggleHintsButton');
    const toggleAnalyticsButton = document.getElementById('toggleAnalyticsButton');


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

    // --- 5. УПРАВЛЕНИЕ ПРОФИЛЯМИ С ПАРОЛЕМ (Усиление стабильности) ---
    
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

        // Гарантируем "Default"
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
                CURRENT_PROFILE_KEY = p.name; // КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ
            }
            profileSelect.appendChild(option);
        });
        
        document.getElementById('deleteProfileButton').disabled = profileList.length <= 1;
    }
    
    function handleNewProfile() { 
        let newName = prompt("Введите имя нового профиля:", `Карта ${getProfileList().length + 1}`);
        if (!newName) return;
        newName = newName.trim();
        if (!newName) return; 

        const profileList = getProfileList();
        if (profileList.find(p => p.name === newName)) {
            alert(`Профиль с именем "${newName}" уже существует.`);
            return;
        }
        
        // ... (логика пароля) ...
        let password = null;
        if (confirm("Вы хотите установить 4-значный пароль для этого профиля?")) {
            let passInput;
            while (true) {
                passInput = prompt("Введите 4-значный ЧИСЛОВОЙ пароль:");
                if (passInput === null) break; 
                if (/^\d{4}$/.test(passInput)) { password = passInput; break; } 
                else { alert("Некорректный формат. Пароль должен состоять ровно из 4 цифр."); }
            }
        }
        
        const newProfile = { name: newName, password: password };
        profileList.push(newProfile);
        saveProfileList(profileList);
        
        safeSetItem(newName, JSON.stringify(createInitialState())); 
        
        updateProfileSelect(newName);
        loadState(newName);
    }
    
    function handleDeleteProfile() { 
        const currentName = CURRENT_PROFILE_KEY;
        const profileList = getProfileList();
        
        if (profileList.length <= 1 || currentName === 'Default') {
            alert("Основной профиль 'Default' удалить нельзя.");
            return;
        }
        
        const profileToDelete = profileList.find(p => p.name === currentName);
        if (profileToDelete && profileToDelete.password) {
             let passInput = prompt(`Для удаления профиля "${currentName}" введите пароль:`);
             if (passInput !== profileToDelete.password) {
                 alert("Неверный пароль. Удаление отменено.");
                 return;
             }
        }

        if (!confirm(`Вы уверены, что хотите удалить профиль "${currentName}"?`)) return;

        localStorage.removeItem(currentName);
        
        const newProfileList = profileList.filter(p => p.name !== currentName);
        saveProfileList(newProfileList);

        const newActiveName = newProfileList[0].name;
        updateProfileSelect(newActiveName);
        loadState(newActiveName);
    }
    
    function handleProfileChange() {
        const newProfileName = profileSelect.value;
        const profileList = getProfileList();
        const selectedProfile = profileList.find(p => p.name === newProfileName);
        
        if (!selectedProfile) {
             // КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: если профиль не найден, возвращаемся
             profileSelect.value = CURRENT_PROFILE_KEY; 
             return;
        }
        
        if (selectedProfile.password) {
            let passInput = prompt(`Профиль "${newProfileName}" защищен паролем. Введите 4-значный пароль:`);
            
            if (passInput !== selectedProfile.password) {
                alert("Неверный пароль. Переключение отменено.");
                profileSelect.value = CURRENT_PROFILE_KEY; 
                return;
            }
        }

        if (newProfileName !== CURRENT_PROFILE_KEY) {
            loadState(newProfileName);
        }
    }


    // --- 6. ФУНКЦИИ СОХРАНЕНИЯ/ЗАГРУЗКИ ---
    function applyTransform() {
        // Применяем transform к canvas
        canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
        
        // Применяем transform к SVG слою, чтобы линии масштабировались и смещались корректно
        svgLayer.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`; 
        svgLayer.style.transformOrigin = '0 0';
    }
    
    function createInitialState() {
        return { 
            nodes: {}, 
            links: [], 
            zoom: 1, 
            panX: 0, 
            panY: 0,
            influenceType: 'importance' 
        };
    }
    
    function clearWorkspace() {
        canvas.innerHTML = '';
        svgLayer.innerHTML = ''; 
        nodeIdCounter = 0; 
        connectingNodeId = null;
    }
    
    function saveState() {
        // ... (логика сохранения узлов, связей и настроек - ОСТАВЛЯЕМ КАК БЫЛО) ...
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
            influenceType: influenceTypeSelect.value 
        };
        safeSetItem(stateKey, JSON.stringify(state));
    }
    
    function loadState(profileName) {
        clearWorkspace(); 

        CURRENT_PROFILE_KEY = profileName || 'Default'; // КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Гарантируем Default
        
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
        
        influenceTypeSelect.value = state.influenceType || 'importance'; 
        
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
        
        document.querySelectorAll('.node').forEach(node => {
            updateNodeInfluence(node.id);
        });
        updateAnalytics();
    }
    
    // --- 7. ФУНКЦИИ УЗЛОВ, СВЯЗЕЙ И ВЛИЯНИЯ ---
    
    function updateNodeInfluence(nodeId) { 
        // ... (логика сфер влияния и цветов - ОСТАВЛЯЕМ КАК БЫЛО) ...
        const node = document.getElementById(nodeId);
        if (!node) return;
        
        const connections = JSON.parse(node.dataset.connections || '[]');
        const connectionCount = connections.length / 2; 
        const influenceType = influenceTypeSelect.value;

        // 1. Убираем ВСЕ классы влияния и цвета
        node.className = 'node'; // Сброс всех классов, кроме базового
        
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
        
        updateAnalytics();
    }
    
    function createNode(x, y, initialText = '', id = null, connections = [], nodeScale = 1, influenceColor = 'default') { 
        // ... (логика создания узла - ОСТАВЛЯЕМ КАК БЫЛО) ...
        const nodeId = id || `node-${++nodeIdCounter}`;
        if (!id) nodeIdCounter = parseInt(nodeId.replace('node-', '')); 
        
        const node = document.createElement('div');
        node.className = 'node';
        node.id = nodeId;
        node.style.left = `${x}px`;
        node.style.top = `${y}px`;
        node.dataset.connections = JSON.stringify(connections); 
        node.dataset.scale = nodeScale; 
        node.dataset.influenceColor = influenceColor; 
        
        updateNodeSize(node, nodeScale);
        
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Mind'; 
        input.value = initialText; 
        input.addEventListener('change', saveState); 
        input.addEventListener('blur', saveState);
        
        function updateFontSize() {
            const scale = parseFloat(node.dataset.scale || 1);
            input.style.fontSize = `${1.1 * Math.sqrt(scale)}em`; 
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
        
        // ... (обработчики drag, dblclick, touchend, click - ОСТАВЛЯЕМ КАК БЫЛО) ...
        
        return node;
    }
    
    // ... (findNodeBoundaryPoint - ОСТАВЛЯЕМ КАК БЫЛО) ...
    function findNodeBoundaryPoint(node, targetPoint) { /* ... */ return point; }
    
    // ... (createLink, updateAllConnections, deleteLink, deleteNodeAndConnections - ОСТАВЛЯЕМ КАК БЫЛО) ...
    // ... (Там уже используется SVG и Безье) ...

    function createLink(sourceId, targetId) { /* ... */ }
    function updateAllConnections(movedNodeId) { /* ... */ }
    function deleteLink(sourceId, targetId) { /* ... */ }
    function deleteNodeAndConnections(nodeId) { /* ... */ }


    // --- 8. ФУНКЦИИ АНАЛИТИКИ И СТАТИСТИКИ ---
    
    function updateAnalytics() {
        // ... (логика расчета аналитики - ОСТАВЛЯЕМ КАК БЫЛО) ...
        const nodes = document.querySelectorAll('.node');
        const links = document.querySelectorAll('.link-path');
        
        nodeCountSpan.textContent = nodes.length;
        linkCountSpan.textContent = links.length;
        
        const influenceData = [];
        
        nodes.forEach(node => {
            const connections = JSON.parse(node.dataset.connections || '[]');
            const connectionCount = connections.length / 2;
            
            influenceData.push({
                id: node.id,
                text: node.querySelector('input').value || `Узел ${node.id.replace('node-', '')}`,
                count: connectionCount
            });
        });
        
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
    // ... (Все функции drag, pan, zoom - ОСТАВЛЯЕМ КАК БЫЛО) ...

    // --- 10. ИНИЦИАЛИЗАЦИЯ И РЕГИСТРАЦИЯ ВСЕХ СОБЫТИЙ ---

    function setupEventListeners() {
        
        document.getElementById('profile-select').addEventListener('change', handleProfileChange);
        document.getElementById('newProfileButton').addEventListener('click', handleNewProfile);
        document.getElementById('deleteProfileButton').addEventListener('click', handleDeleteProfile);
        document.getElementById('saveProfileButton').addEventListener('click', saveState);

        influenceTypeSelect.addEventListener('change', () => {
            document.querySelectorAll('.node').forEach(node => updateNodeInfluence(node.id));
            saveState();
        });
        
        // НОВЫЕ ОБРАБОТЧИКИ ПАНЕЛЕЙ
        toggleHintsButton.addEventListener('click', () => {
            hintsPanel.classList.toggle('visible');
            // На мобильных скрываем другую панель
            if (window.innerWidth <= 900 && hintsPanel.classList.contains('visible')) {
                analyticsPanel.classList.remove('visible');
            }
        });
        
        toggleAnalyticsButton.addEventListener('click', () => {
            analyticsPanel.classList.toggle('visible');
            // На мобильных скрываем другую панель
            if (window.innerWidth <= 900 && analyticsPanel.classList.contains('visible')) {
                hintsPanel.classList.remove('visible');
            }
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
        
        // Убеждаемся, что выбранный профиль существует, иначе выбираем первый
        const activeProfileName = profileList.length > 0 ? profileList[0].name : 'Default'; 
        
        updateProfileSelect(activeProfileName);
        loadState(activeProfileName);
    }
    
    initialize(); 
});
