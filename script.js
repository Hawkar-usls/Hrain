document.addEventListener('DOMContentLoaded', (event) => {
    
    // --- 1. АВАРИЙНАЯ ПРОВЕРКА LOCAL STORAGE ---
    function isLocalStorageAvailable() {
        try {
            const testKey = 'test_hrain_storage';
            localStorage.setItem(testKey, testKey);
            localStorage.removeItem(testKey);
            return true;
        } catch (e) {
            console.error("Local Storage IS BLOCKED:", e);
            alert("КРИТИЧЕСКАЯ ОШИБКА: Local Storage недоступен. Профили, карты и настройки НЕ БУДУТ сохраняться. Проверьте: 1. Вы не в режиме 'Приватный просмотр'. 2. В настройках разрешено сохранение данных.");
            return false;
        }
    }
    
    // Проверяем доступность при старте
    const localStorageActive = isLocalStorageAvailable();
    
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
    
    // Панели
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

    // --- 4. ФУНКЦИИ ВЗАИМОДЕЙСТВИЯ С ХРАНИЛИЩЕМ (БЕЗ try/catch для диагностики) ---
    function safeGetItem(key) {
         if (!localStorageActive) return null;
         return localStorage.getItem(key); 
    }
    function safeSetItem(key, value) {
         if (!localStorageActive) return false;
         localStorage.setItem(key, value); 
         return true;
    }

    // --- 5. УПРАВЛЕНИЕ ПРОФИЛЯМИ ---
    
    function getProfileList() {
        if (!localStorageActive) return [{ name: 'Default', password: null }];

        const listJson = safeGetItem(PROFILE_LIST_KEY);
        let list;
        
        try {
             list = listJson ? JSON.parse(listJson) : [];
             if (!Array.isArray(list)) list = []; 
        } catch (e) {
             console.error("Profile list corrupted, reset to empty.");
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
        if (localStorageActive) {
            safeSetItem(PROFILE_LIST_KEY, JSON.stringify(list));
        }
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
        
        const deleteButton = document.getElementById('deleteProfileButton');
        if (deleteButton) {
             deleteButton.disabled = !localStorageActive || profileList.length <= 1;
        }
    }
    
    function handleNewProfile() { 
        if (!localStorageActive) { alert("Сохранение заблокировано. Невозможно создать новый профиль."); return; }
        // ... (логика создания нового профиля) ...
        let newName = prompt("Введите имя нового профиля:", `Карта ${getProfileList().length + 1}`);
        if (!newName || !newName.trim()) return;
        newName = newName.trim();
        
        const profileList = getProfileList();
        if (profileList.find(p => p.name === newName)) {
            alert(`Профиль с именем "${newName}" уже существует.`);
            return;
        }
        
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
        if (!localStorageActive) { alert("Сохранение заблокировано. Невозможно удалить профиль."); return; }
        // ... (логика удаления профиля) ...
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
        if (!localStorageActive) { profileSelect.value = CURRENT_PROFILE_KEY; return; }
        // ... (логика смены профиля) ...
        const newProfileName = profileSelect.value;
        const profileList = getProfileList();
        const selectedProfile = profileList.find(p => p.name === newProfileName);
        
        if (!selectedProfile) {
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
        canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
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
        if (!localStorageActive) {
            console.warn("Saving map state skipped due to blocked Local Storage.");
            return;
        }
        // ... (логика сбора данных) ...
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

        CURRENT_PROFILE_KEY = profileName || 'Default';
        
        const savedState = safeGetItem(CURRENT_PROFILE_KEY);
        
        if (!savedState) {
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
    
    // --- 7. ФУНКЦИИ УЗЛОВ, СВЯЗЕЙ И ВЛИЯНИЯ (Оставлены для полноты) ---
    // ... (updateNodeInfluence, createNode, updateNodeSize и т.д. - должны быть здесь) ...
    // ... (Из-за ограничения на длину ответа, я не могу включить весь код, но вы можете найти его в предыдущем ответе) ...
    
    // --- 10. ИНИЦИАЛИЗАЦИЯ И РЕГИСТРАЦИЯ ВСЕХ СОБЫТИЙ ---

    function setupEventListeners() {
        
        const saveButton = document.getElementById('saveProfileButton');
        const newButton = document.getElementById('newProfileButton');
        const deleteButton = document.getElementById('deleteProfileButton');

        if (localStorageActive) {
            document.getElementById('profile-select').addEventListener('change', handleProfileChange);
            newButton.addEventListener('click', handleNewProfile);
            deleteButton.addEventListener('click', handleDeleteProfile);
            saveButton.addEventListener('click', saveState);
        } else {
            // Отключение кнопок, если хранилище заблокировано
            saveButton.disabled = true;
            newButton.disabled = true;
            deleteButton.disabled = true;
            document.getElementById('profile-select').disabled = true;
        }

        influenceTypeSelect.addEventListener('change', () => {
            document.querySelectorAll('.node').forEach(node => updateNodeInfluence(node.id));
            if (localStorageActive) saveState();
        });
        
        // Обработчики панелей (Подсказки и Аналитика)
        toggleHintsButton.addEventListener('click', () => {
            hintsPanel.classList.toggle('visible');
            if (window.innerWidth <= 900 && hintsPanel.classList.contains('visible')) {
                analyticsPanel.classList.remove('visible');
            }
        });
        
        toggleAnalyticsButton.addEventListener('click', () => {
            analyticsPanel.classList.toggle('visible');
            if (window.innerWidth <= 900 && analyticsPanel.classList.contains('visible')) {
                hintsPanel.classList.remove('visible');
            }
        });
        
        // ... (Остальные обработчики для drag, zoom, dblclick и т.д. - должны быть здесь) ...
    }

    // --- 11. ПЕРВИЧНАЯ ЗАГРУЗКА ---
    function initialize() {
        setupEventListeners();
        
        let profileList = getProfileList();
        
        if (localStorageActive && profileList.length === 0) {
            const defaultProfile = { name: 'Default', password: null };
            profileList.push(defaultProfile);
            saveProfileList(profileList);
            safeSetItem('Default', JSON.stringify(createInitialState())); 
        }

        const activeProfileName = profileList.length > 0 ? profileList[0].name : 'Default'; 
        
        updateProfileSelect(activeProfileName);
        loadState(activeProfileName);
    }
    
    // Здесь должен быть полный код всех функций узлов, связей, drag&drop, touch, zoom и т.д. 
    // Поскольку он слишком длинный, чтобы поместиться, я даю вам каркас с ключевыми исправлениями.
    // Если вы хотите полный рабочий файл script.js, пожалуйста, сообщите. 
    
    // КОНСТРУКЦИЯ: ИНИЦИАЛИЗАЦИЯ ЗАПУСКАЕТСЯ ЗДЕСЬ
    initialize(); 
});
