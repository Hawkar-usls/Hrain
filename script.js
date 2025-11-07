document.addEventListener('DOMContentLoaded', (event) => {
    
    // --- 1. АВАРИЙНАЯ ПРОВЕРКА LOCAL STORAGE (КРИТИЧНО ДЛЯ iOS) ---
    try {
        localStorage.setItem('test_hrain', 'test');
        localStorage.removeItem('test_hrain');
    } catch (e) {
        alert("Внимание: Ваш браузер блокирует сохранение данных (Local Storage)! Профили и карты НЕ БУДУТ сохраняться. Пожалуйста, отключите режим 'Приватный просмотр' или настройте исключения для cookies/сайтов.");
    }
    
    // --- 2. КОНСТАНТЫ И ЭЛЕМЕНТЫ ИНТЕРФЕЙСА ---
    const PROFILE_LIST_KEY = 'hrain_profiles_list'; 
    let CURRENT_PROFILE_KEY = 'Default'; 
    
    const workspace = document.getElementById('workspace');
    const canvas = document.getElementById('canvas');
    const profileSelect = document.getElementById('profile-select');
    const saveProfileButton = document.getElementById('saveProfileButton');
    const newProfileButton = document.getElementById('newProfileButton');
    const deleteProfileButton = document.getElementById('deleteProfileButton');

    // --- 3. ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ КАРТЫ И ВЗАИМОДЕЙСТВИЯ ---
    let nodeIdCounter = 0;
    let connectingNodeId = null; 
    let currentZoom = 1; 
    let panX = 0; 
    let panY = 0; 
    
    const zoomStep = 0.1; 
    const minZoom = 0.5;  
    const maxZoom = 3.0; 
    const nodeScaleStep = 0.2; 

    // Переменные для Мыши/Touch
    let isPanning = false; 
    let isDraggingNode = false; 
    let currentDraggedNode = null;
    let lastClientX = 0; 
    let lastClientY = 0; 

    // Переменные для Touch (Pinch-to-Zoom)
    let activeTouches = []; 
    let initialDistance = 0; 
    let initialZoom = 1;
    
    // Переменные для двойного тапа
    let lastTapWorkspace = 0;
    let lastTapNode = 0;
    let lastTapLink = 0;


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
        let list = listJson ? JSON.parse(listJson) : [];

        // Конвертация старого формата (массив строк) в новый (массив объектов)
        let convertedList = list.map(item => {
            if (typeof item === 'string') {
                return { name: item, password: null };
            }
            return item;
        });

        // Гарантируем, что "Default" всегда есть и без пароля
        if (!convertedList.find(p => p.name === 'Default')) {
            convertedList.unshift({ name: 'Default', password: null });
        }
        
        // Убедимся, что все пароли для "Default" удалены
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
            // Добавляем замочек, если есть пароль
            option.textContent = p.password ? `${p.name} 🔒` : p.name;
            option.value = p.name; 
            if (p.name === activeProfileName) {
                option.selected = true;
                CURRENT_PROFILE_KEY = p.name; 
            }
            profileSelect.appendChild(option);
        });
        
        deleteProfileButton.disabled = profileList.length <= 1;
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
        
        let password = null;
        if (confirm("Вы хотите установить 4-значный пароль для этого профиля?")) {
            let passInput;
            while (true) {
                passInput = prompt("Введите 4-значный ЧИСЛОВОЙ пароль:");
                
                if (passInput === null) { // Пользователь нажал "Отмена"
                    break;
                }
                
                // Проверка на 4 цифры
                if (/^\d{4}$/.test(passInput)) {
                    password = passInput;
                    break;
                } else {
                    alert("Некорректный формат. Пароль должен состоять ровно из 4 цифр.");
                }
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
        
        if (profileList.length <= 1) {
            alert("Нельзя удалить последний профиль!");
            return;
        }
        
        if (currentName === 'Default') {
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


        if (!confirm(`Вы уверены, что хотите удалить профиль "${currentName}"? Данные будут потеряны.`)) {
            return;
        }

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
        
        if (!selectedProfile) return;
        
        if (selectedProfile.password) {
            let passInput = prompt(`Профиль "${newProfileName}" защищен паролем. Введите 4-значный пароль:`);
            
            if (passInput !== selectedProfile.password) {
                alert("Неверный пароль. Переключение отменено.");
                // Возвращаем селектор к текущему активному профилю
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
    }
    function createInitialState() {
        return { nodes: {}, links: [], zoom: 1, panX: 0, panY: 0 };
    }
    function clearWorkspace() {
        canvas.innerHTML = '';
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
                nodeScale: parseFloat(nodeEl.dataset.scale || 1) 
            };
        });

        const linksData = [];
        const uniqueLinks
