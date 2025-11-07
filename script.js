document.addEventListener('DOMContentLoaded', (event) => {
    
    // --- 1. АВАРИЙНАЯ ПРОВЕРКА LOCAL STORAGE (Удалены try/catch для диагностики!) ---
    function isLocalStorageAvailable() {
        try {
            const testKey = 'test_hrain_storage';
            localStorage.setItem(testKey, testKey);
            localStorage.removeItem(testKey);
            return true;
        } catch (e) {
            console.error("Local Storage IS BLOCKED:", e);
            alert("КРИТИЧЕСКАЯ ОШИБКА: Local Storage недоступен. Профили, карты и настройки НЕ БУДУТ сохраняться. Проверьте: 1. Вы не в режиме 'Приватный просмотр'. 2. В настройках разрешено сохранение данных/cookies.");
            return false;
        }
    }
    
    // Проверяем доступность при старте
    if (!isLocalStorageAvailable()) {
        // Продолжаем, но с ошибкой.
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
    // ---

    // --- 4. ФУНКЦИИ ВЗАИМОДЕЙСТВИЯ С ХРАНИЛИЩЕМ (Без try/catch!) ---
    // Если Local Storage заблокирован, эти функции будут бросать ошибку,
    // которую мы обработаем в консоли и в isLocalStorageAvailable.
    function safeGetItem(key) {
         return localStorage.getItem(key); 
    }
    function safeSetItem(key, value) {
         localStorage.setItem(key, value); 
         return true;
    }

    // --- 5. УПРАВЛЕНИЕ ПРОФИЛЯМИ С ПАРОЛЕМ ---
    
    function getProfileList() {
        const listJson = safeGetItem(PROFILE_LIST_KEY);
        let list;
        
        try {
             // Пытаемся распарсить, если не можем, список пуст.
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

        // Гарантируем "Default"
        if (!convertedList.find(p => p.name === 'Default')) {
            convertedList.unshift({ name: 'Default', password: null });
        }
        
        const defaultProfile = convertedList.find(p => p.name === 'Default');
        if (defaultProfile) defaultProfile.password = null;

        return convertedList;
    }

    function saveProfileList(list) {
        if (isLocalStorageAvailable()) {
            safeSetItem(PROFILE_LIST_KEY, JSON.stringify(list));
        } else {
            console.warn("Saving profile list skipped due to blocked Local Storage.");
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
        
        // Кнопка удаления доступна, только если профилей > 1
        document.getElementById('deleteProfileButton').disabled = profileList.length <= 1;
    }
    
    // ... (handleNewProfile, handleDeleteProfile, handleProfileChange - Логика не меняется) ...
    function handleNewProfile() { 
         // ... (Проверка имени, логика пароля) ...
         const newProfile = { name: newName, password: password };
         profileList.push(newProfile);
         saveProfileList(profileList); // ЭТО ДОЛЖНО РАБОТАТЬ
         safeSetItem(newName, JSON.stringify(createInitialState())); // ЭТО ДОЛЖНО РАБОТАТЬ
         updateProfileSelect(newName);
         loadState(newName);
    }
    
    function handleDeleteProfile() { /* ... */ }
    function handleProfileChange() { /* ... */ }


    // --- 6. ФУНКЦИИ СОХРАНЕНИЯ/ЗАГРУЗКИ ---
    function applyTransform() {
        canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
        svgLayer.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`; 
        svgLayer.style.transformOrigin = '0 0';
    }
    
    function createInitialState() {
        return { nodes: {}, links: [], zoom: 1, panX: 0, panY: 0, influenceType: 'importance' };
    }
    
    function clearWorkspace() {
        canvas.innerHTML = '';
        svgLayer.innerHTML = ''; 
        nodeIdCounter = 0; 
        connectingNodeId = null;
    }
    
    function saveState() {
        if (!isLocalStorageAvailable()) {
            console.warn("Saving map state skipped due to blocked Local Storage.");
            return;
        }
        // ... (логика сохранения узлов, связей и настроек) ...
        const stateKey = CURRENT_PROFILE_KEY;
        // ... (сбор данных) ...
        const state = { /* ... */ };
        safeSetItem(stateKey, JSON.stringify(state));
    }
    
    function loadState(profileName) {
        clearWorkspace(); 

        CURRENT_PROFILE_KEY = profileName || 'Default';
        
        const savedState = safeGetItem(CURRENT_PROFILE_KEY);
        
        if (!savedState) {
            // Если профиль пуст или не найден, создаем начальное состояние
            const initialState = createInitialState();
            
            // Пытаемся сохранить, но даже если не удастся (Local Storage заблокирован),
            // мы продолжим работать с текущим состоянием в памяти.
            safeSetItem(CURRENT_PROFILE_KEY, JSON.stringify(initialState)); 

            currentZoom = 1; panX = 0; panY = 0; applyTransform();
            createNode(50, 50, `Карта: ${CURRENT_PROFILE_KEY}`); 
            influenceTypeSelect.value = initialState.influenceType;
            saveState(); 
            return;
        }
        
        const state = JSON.parse(savedState);
        
        // ... (логика загрузки узлов, связей, зума) ...
        
        applyTransform();
        updateProfileSelect(CURRENT_PROFILE_KEY);
        
        // ... (обновление влияния и аналитики) ...
    }
    
    // --- 7. ФУНКЦИИ УЗЛОВ, СВЯЗЕЙ И ВЛИЯНИЯ ---
    // ... (Логика не меняется) ...

    // --- 8. ФУНКЦИИ АНАЛИТИКИ И СТАТИСТИКИ ---
    // ... (Логика не меняется) ...


    // --- 9. УНИФИЦИРОВАННЫЕ ФУНКЦИИ ВЗАИМОДЕЙСТВИЯ (МЫШЬ И ТАЧ) ---
    // ... (Логика не меняется) ...

    // --- 10. ИНИЦИАЛИЗАЦИЯ И РЕГИСТРАЦИЯ ВСЕХ СОБЫТИЙ ---

    function setupEventListeners() {
        
        // ... (События Профилей) ...

        // НОВЫЕ ОБРАБОТЧИКИ ПАНЕЛЕЙ
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
        
        // ... (Остальные обработчики) ...
    }

    // --- 11. ПЕРВИЧНАЯ ЗАГРУЗКА (КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ЗАГРУЗКИ ПРОФИЛЕЙ) ---
    function initialize() {
        
        // КРИТИЧЕСКИЙ ШАГ: Если Local Storage заблокирован, мы не сможем работать с профилями.
        if (!isLocalStorageAvailable()) {
            // В этом случае, мы загружаем пустое начальное состояние,
            // но пользователь не сможет сохранить его или создать новый профиль.
            setupEventListeners();
            clearWorkspace();
            const initialState = createInitialState();
            currentZoom = 1; panX = 0; panY = 0; applyTransform();
            createNode(50, 50, `Карта: ${CURRENT_PROFILE_KEY} (СОХРАНЕНИЕ ВЫКЛЮЧЕНО!)`);
            updateProfileSelect(CURRENT_PROFILE_KEY);
            document.getElementById('saveProfileButton').disabled = true;
            document.getElementById('newProfileButton').disabled = true;
            document.getElementById('deleteProfileButton').disabled = true;
            return; // Завершаем инициализацию
        }
        
        // Если Local Storage доступен:
        setupEventListeners();
        
        // Принудительная инициализация списка профилей, если он пуст/поврежден
        let profileList = getProfileList();
        if (profileList.length === 0) {
            const defaultProfile = { name: 'Default', password: null };
            profileList.push(defaultProfile);
            saveProfileList(profileList);
            safeSetItem('Default', JSON.stringify(createInitialState())); 
        }

        const activeProfileName = profileList.length > 0 ? profileList[0].name : 'Default'; 
        
        updateProfileSelect(activeProfileName);
        loadState(activeProfileName);
    }
    
    initialize(); 
});
