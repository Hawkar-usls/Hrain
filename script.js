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
            panY: panY  
        };
        safeSetItem(stateKey, JSON.stringify(state));
    }
    
    function loadState(profileName) {
        clearWorkspace(); 

        CURRENT_PROFILE_KEY = profileName || CURRENT_PROFILE_KEY;
        
        const savedState = safeGetItem(CURRENT_PROFILE_KEY);
        
        if (!savedState) {
            // Если профиль пуст, создаем начальный узел
            safeSetItem(CURRENT_PROFILE_KEY, JSON.stringify(createInitialState()));
            currentZoom = 1; panX = 0; panY = 0; applyTransform();
            createNode(50, 50, `Карта: ${CURRENT_PROFILE_KEY}`); 
            saveState(); 
            return;
        }
        
        const state = JSON.parse(savedState);
        
        let maxId = 0;
        Object.values(state.nodes || {}).forEach(data => {
            createNode(data.x, data.y, data.text, data.id, data.connections, data.nodeScale); 
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
        
        // Обновляем сферы влияния после загрузки
        document.querySelectorAll('.node').forEach(node => {
            updateNodeInfluence(node.id);
        });
    }
    
    // --- 7. ФУНКЦИИ УЗЛОВ И СВЯЗЕЙ ---
    
    // Новая функция для расчета сферы влияния
    function updateNodeInfluence(nodeId) {
        const node = document.getElementById(nodeId);
        if (!node) return;
        
        // Считаем количество уникальных связей
        const connections = JSON.parse(node.dataset.connections || '[]');
        // Каждая связь хранится как входящая и исходящая, поэтому делим на 2
        const connectionCount = connections.length / 2; 

        // Удаляем старые классы влияния
        node.classList.remove('influence-low', 'influence-medium', 'influence-high');

        // Применяем новые классы в зависимости от количества связей
        if (connectionCount >= 6) {
            node.classList.add('influence-high');
        } else if (connectionCount >= 4) {
            node.classList.add('influence-medium');
        } else if (connectionCount >= 2) {
            node.classList.add('influence-low');
        }
    }
    
    function updateNodeSize(node, scale) {
        node.style.transform = `scale(${scale})`;
        node.dataset.scale = scale;
    }

    function changeNodeScale(nodeId, direction) {
        const node = document.getElementById(nodeId);
        let scale = parseFloat(node.dataset.scale || 1);
        let newScale = scale + direction * nodeScaleStep;
        newScale = Math.max(0.5, Math.min(3.0, newScale));
        newScale = Math.round(newScale * 10) / 10; 
        if (newScale !== scale) {
            updateNodeSize(node, newScale);
            updateAllConnections(nodeId); 
            saveState();
        }
    }
    
    function createNode(x, y, initialText = '', id = null, connections = [], nodeScale = 1) { 
        const nodeId = id || `node-${++nodeIdCounter}`;
        if (!id) nodeIdCounter = parseInt(nodeId.replace('node-', '')); 
        
        const node = document.createElement('div');
        node.className = 'node';
        node.id = nodeId;
        node.style.left = `${x}px`;
        node.style.top = `${y}px`;
        node.dataset.connections = JSON.stringify(connections); 
        node.dataset.scale = nodeScale; 
        
        updateNodeSize(node, nodeScale);
        
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Mind'; 
        input.value = initialText; 
        input.addEventListener('change', saveState); 
        input.addEventListener('blur', saveState);
        node.appendChild(input);
        
        // Кнопки масштаба
        const scaleUpButton = document.createElement('button');
        scaleUpButton.textContent = '+';
        scaleUpButton.className = 'scale-button';
        scaleUpButton.style.position = 'absolute';
        scaleUpButton.style.right = '-25px';
        scaleUpButton.style.top = '0';
        scaleUpButton.onclick = (e) => { e.stopPropagation(); changeNodeScale(nodeId, 1); };
        node.appendChild(scaleUpButton);

        const scaleDownButton = document.createElement('button');
        scaleDownButton.textContent = '-';
        scaleDownButton.className = 'scale-button';
        scaleDownButton.style.position = 'absolute';
        scaleDownButton.style.right = '-25px';
        scaleDownButton.style.bottom = '0';
        scaleDownButton.onclick = (e) => { e.stopPropagation(); changeNodeScale(nodeId, -1); };
        node.appendChild(scaleDownButton);
        
        canvas.appendChild(node);
        
        node.addEventListener('mousedown', startNodeDrag);
        
        // Двойной клик для удаления узла (ПК)
        node.addEventListener('dblclick', (e) => {
            e.stopPropagation(); 
            deleteNodeAndConnections(nodeId);
        });
        
        // Двойной тап для удаления узла (Touch)
        node.addEventListener('touchend', (e) => {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTapNode;
            
            if (tapLength < 500 && tapLength > 50 && e.touches.length === 0) {
                 e.stopPropagation(); 
                 deleteNodeAndConnections(nodeId);
            }
            lastTapNode = currentTime;
        });

        
        // Логика одинарного клика/тапа для соединения
        node.addEventListener('click', (e) => {
            if (isDraggingNode) return; 
            e.stopPropagation(); 
            document.querySelectorAll('.node').forEach(n => n.classList.remove('selected-for-delete'));
            handleNodeConnect(nodeId);
        });
        
        return node;
    }
    
    function handleNodeConnect(nodeId) {
        const node = document.getElementById(nodeId);
        
        document.querySelectorAll('.node').forEach(n => {
            if (n.id !== nodeId) n.classList.remove('selected');
        });

        if (connectingNodeId === null) {
            connectingNodeId = nodeId;
            node.classList.add('selected');
        } else if (connectingNodeId === nodeId) {
            connectingNodeId = null;
            node.classList.remove('selected');
        } else {
            const sourceId = connectingNodeId;
            const targetId = nodeId;
            const sourceNode = document.getElementById(sourceId);
            const targetNode = document.getElementById(targetId);
            
            const sConnections = JSON.parse(sourceNode.dataset.connections);
            const tConnections = JSON.parse(targetNode.dataset.connections);
            
            if (!sConnections.includes(targetId)) {
                createLink(sourceId, targetId);
                
                sConnections.push(targetId);
                sourceNode.dataset.connections = JSON.stringify(sConnections);
                
                tConnections.push(sourceId); 
                targetNode.dataset.connections = JSON.stringify(tConnections);
                
                // Обновляем сферу влияния для обеих сторон
                updateNodeInfluence(sourceId);
                updateNodeInfluence(targetId);
                
                saveState();
            }

            document.getElementById(sourceId).classList.remove('selected');
            connectingNodeId = null;
        }
    }
    
    function findNodeBoundaryPoint(node, targetPoint) {
        const nodeX = node.offsetLeft;
        const nodeY = node.offsetTop;
        const scale = parseFloat(node.dataset.scale || 1);
        const width = node.offsetWidth * scale;
        const height = node.offsetHeight * scale;
        const centerX = nodeX + width / 2;
        const centerY = nodeY + height / 2;
        const dx = targetPoint.x - centerX;
        const dy = targetPoint.y - centerY;
        const absDx = Math.abs(dx);
        const absDy = Math.abs(dy);

        let tx, ty;

        if (absDx / width >= absDy / height) {
            tx = width / 2;
            if (dx < 0) tx = -tx; 
            ty = tx * dy / dx; 
        } else {
            ty = height / 2;
            if (dy < 0) ty = -ty; 
            tx = ty * dx / dy; 
        }

        return { x: centerX + tx, y: centerY + ty };
    }
    
    function createLink(sourceId, targetId) {
        const linkKey = [sourceId, targetId].sort().join('-'); 
        let line = document.getElementById(linkKey);
        
        if (line) line.remove();
        
        const sourceNode = document.getElementById(sourceId);
        const targetNode = document.getElementById(targetId);
        
        if (!sourceNode || !targetNode) return; 

        const sourceScale = parseFloat(sourceNode.dataset.scale || 1);
        const targetScale = parseFloat(targetNode.dataset.scale || 1);
        
        const sourceCenter = {
            x: sourceNode.offsetLeft + (sourceNode.offsetWidth * sourceScale) / 2,
            y: sourceNode.offsetTop + (sourceNode.offsetHeight * sourceScale) / 2
        };
        const targetCenter = {
            x: targetNode.offsetLeft + (targetNode.offsetWidth * targetScale) / 2,
            y: targetNode.offsetTop + (targetNode.offsetHeight * targetScale) / 2
        };

        const p1 = findNodeBoundaryPoint(sourceNode, targetCenter); 
        const p2 = findNodeBoundaryPoint(targetNode, sourceCenter); 

        const length = Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2);
        const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x) * (180 / Math.PI);
        
        line = document.createElement('div');
        line.className = 'link-line';
        line.id = linkKey;
        line.style.width = `${length}px`;
        line.style.left = `${p1.x}px`;
        line.style.top = `${p1.y}px`;
        line.style.transform = `rotate(${angle}deg)`;
        line.dataset.source = sourceId;
        line.dataset.target = targetId;

        const deleteLinkHandler = (e) => {
             e.stopPropagation(); 
             const sId = e.target.dataset.source;
             const tId = e.target.dataset.target;
             if (sId && tId) { deleteLink(sId, tId); }
        };

        line.addEventListener('dblclick', deleteLinkHandler); // ПК
        
        line.addEventListener('touchend', (e) => { // Touch
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTapLink;
            
            if (tapLength < 500 && tapLength > 50 && e.touches.length === 0) {
                 deleteLinkHandler(e);
            }
            lastTapLink = currentTime;
        });

        canvas.appendChild(line);
    }

    function updateAllConnections(movedNodeId) {
        document.querySelectorAll('.link-line').forEach(line => {
            if (line.dataset.source === movedNodeId || line.dataset.target === movedNodeId) {
                createLink(line.dataset.source, line.dataset.target);
            }
        });
    }
    
    function deleteLink(sourceId, targetId) {
        const linkKey = [sourceId, targetId].sort().join('-');
        const line = document.getElementById(linkKey);
        if (!line) return;
        
        const sId = line.dataset.source;
        const tId = line.dataset.target; 
        
        const sourceNode = document.getElementById(sId);
        const targetNode = document.getElementById(tId);

        if (sourceNode) {
            let sConnections = JSON.parse(sourceNode.dataset.connections);
            sourceNode.dataset.connections = JSON.stringify(sConnections.filter(id => id !== tId));
            updateNodeInfluence(sId); // Обновляем сферу влияния
        }

        if (targetNode) {
            let tConnections = JSON.parse(targetNode.dataset.connections);
            targetNode.dataset.connections = JSON.stringify(tConnections.filter(id => id !== sId));
            updateNodeInfluence(tId); // Обновляем сферу влияния
        }
        
        line.remove();
        saveState();
    }

    function deleteNodeAndConnections(nodeId) {
        const node = document.getElementById(nodeId);
        if (!node) return;

        document.querySelectorAll('.link-line').forEach(line => {
            if (line.dataset.source === nodeId || line.dataset.target === nodeId) {
                line.remove();
            }
        });

        document.querySelectorAll('.node').forEach(otherNode => {
            const newConnections = JSON.parse(otherNode.dataset.connections).filter(id => id !== nodeId);
            if (newConnections.length !== JSON.parse(otherNode.dataset.connections).length) {
                otherNode.dataset.connections = JSON.stringify(newConnections);
                updateNodeInfluence(otherNode.id); // Обновляем сферу влияния у соседей
            }
        });
        
        node.remove();
        if (connectingNodeId === nodeId) { connectingNodeId = null; }
        
        saveState(); 
    }


    // --- 8. УНИФИЦИРОВАННЫЕ ФУНКЦИИ ВЗАИМОДЕЙСТВИЯ (МЫШЬ И ТАЧ) ---
    
    function getDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    function getCenter(touches) {
        return {
            x: (touches[0].clientX + touches[1].clientX) / 2,
            y: (touches[0].clientY + touches[1].clientY) / 2
        };
    }
    
    // --- TOUCH HANDLERS ---
    function handleTouchStart(e) {
        activeTouches = Array.from(e.touches);
        
        if (e.target.tagName === 'INPUT' || e.target.classList.contains('scale-button')) return; 
        
        if (activeTouches.length === 1) {
            const touch = activeTouches[0];
            const targetNode = touch.target.closest('.node');

            if (targetNode) {
                e.preventDefault();
                currentDraggedNode = targetNode;
                isDraggingNode = true;
            } else {
                e.preventDefault();
                isPanning = true;
            }
            lastClientX = touch.clientX;
            lastClientY = touch.clientY;
        } else if (activeTouches.length === 2) {
            e.preventDefault();
            initialDistance = getDistance(activeTouches);
            initialZoom = currentZoom;
            isPanning = false; 
            isDraggingNode = false;
        }
        
        document.addEventListener('touchmove', handleTouchMove, { passive: false });
        document.addEventListener('touchend', handleTouchEnd);
        document.addEventListener('touchcancel', handleTouchEnd);
    }

    function handleTouchMove(e) {
        e.preventDefault(); 
        activeTouches = Array.from(e.touches);
        
        if (isDraggingNode && currentDraggedNode && activeTouches.length === 1) {
            // Перетаскивание узла
            const touch = activeTouches[0];
            const dx = touch.clientX - lastClientX;
            const dy = touch.clientY - lastClientY;
            
            let newLeft = currentDraggedNode.offsetLeft + dx / currentZoom;
            let newTop = currentDraggedNode.offsetTop + dy / currentZoom;

            currentDraggedNode.style.top = `${newTop}px`;
            currentDraggedNode.style.left = `${newLeft}px`; 
            
            lastClientX = touch.clientX;
            lastClientY = touch.clientY;
            
            updateAllConnections(currentDraggedNode.id);
        }
        else if (isPanning && !isDraggingNode && activeTouches.length === 1) {
            // Панорамирование холста
            const touch = activeTouches[0];
            const dx = touch.clientX - lastClientX;
            const dy = touch.clientY - lastClientY;
            
            panX += dx;
            panY += dy;
            
            lastClientX = touch.clientX;
            lastClientY = touch.clientY;
            
            applyTransform();
        }
        else if (activeTouches.length === 2) {
            // Зум двумя пальцами (Pinch-to-Zoom)
            const currentDistance = getDistance(activeTouches);
            const scaleFactor = currentDistance / initialDistance;
            let newZoom = initialZoom * scaleFactor;
            
            newZoom = Math.max(minZoom, Math.min(maxZoom, newZoom));
            newZoom = Math.round(newZoom * 100) / 100;
            
            if (newZoom !== currentZoom) {
                const center = getCenter(activeTouches);
                const rect = workspace.getBoundingClientRect();
                const mouseX = center.x - rect.left;
                const mouseY = center.y - rect.top;

                const zoomRatio = newZoom / currentZoom;
                
                panX = mouseX - (mouseX - panX) * zoomRatio;
                panY = mouseY - (mouseY - panY) * zoomRatio;
                
                currentZoom = newZoom;
                applyTransform();
            }
        }
    }

    function handleTouchEnd(e) {
        if (e.touches.length === 0) {
            if (isDraggingNode || isPanning || initialZoom !== currentZoom) { saveState(); }
            
            isDraggingNode = false;
            currentDraggedNode = null;
            isPanning = false;
            activeTouches = [];
            initialDistance = 0;
            initialZoom = 1;
            
            document.removeEventListener('touchmove', handleTouchMove);
            document.removeEventListener('touchend', handleTouchEnd);
            document.removeEventListener('touchcancel', handleTouchEnd);
        }
    }
    
    // --- MOUSE HANDLERS ---
    function startNodeDrag(e) {
        if (e.button !== 0 || e.target.classList.contains('scale-button') || e.target.tagName === 'INPUT') return; 
        if (activeTouches.length > 0) return; 

        e.preventDefault(); 
        isDraggingNode = false;
        currentDraggedNode = e.currentTarget;
        
        lastClientX = e.clientX;
        lastClientY = e.clientY;
        
        document.addEventListener('mousemove', dragNode);
        document.addEventListener('mouseup', stopNodeDrag);
    }
    
    function dragNode(e) {
        if (!currentDraggedNode) return;
        
        const dx = e.clientX - lastClientX;
        const dy = e.clientY - lastClientY;
        isDraggingNode = true; 

        let newLeft = currentDraggedNode.offsetLeft + dx / currentZoom;
        let newTop = currentDraggedNode.offsetTop + dy / currentZoom;

        currentDraggedNode.style.top = `${newTop}px`;
        currentDraggedNode.style.left = `${newLeft}px`; 
        
        lastClientX = e.clientX;
        lastClientY = e.clientY;

        updateAllConnections(currentDraggedNode.id); 
    }
    
    function stopNodeDrag() {
        if (currentDraggedNode) {
            currentDraggedNode = null;
            if (isDraggingNode) { saveState(); }
            isDraggingNode = false; 
        }
        document.removeEventListener('mousemove', dragNode);
        document.removeEventListener('mouseup', stopNodeDrag);
    }

    function startPanning(e) {
        if (e.target.closest('.node') || e.button !== 0 || e.target.tagName === 'INPUT') return; 
        if (activeTouches.length > 0) return; 

        if ((e.code === 'Space' || e.key === ' ' || e.target === workspace || e.target === canvas) && !isPanning) {
            e.preventDefault(); 
            isPanning = true;
            workspace.style.cursor = 'grabbing';
            lastClientX = e.clientX;
            lastClientY = e.clientY;
            
            document.addEventListener('mousemove', panCanvasMouse);
            document.addEventListener('mouseup', stopPanning);
        }
    }
    
    function panCanvasMouse(e) {
        if (!isPanning) return;
        e.preventDefault();
        
        const dx = e.clientX - lastClientX;
        const dy = e.clientY - lastClientY;
        
        panX += dx;
        panY += dy;
        
        lastClientX = e.clientX;
        lastClientY = e.clientY;
        
        applyTransform();
    }
    
    function stopPanning() {
        if (isPanning) {
            isPanning = false;
            workspace.style.cursor = 'default';
            saveState(); 
        }
        document.removeEventListener('mousemove', panCanvasMouse);
        document.removeEventListener('mouseup', stopPanning);
    }
    
    function handleZoom(e) {
        if (activeTouches.length > 0) return; 
        
        e.preventDefault(); 
        
        const delta = e.deltaY > 0 ? -1 : 1;
        let newZoom = currentZoom + delta * zoomStep;
        
        newZoom = Math.max(minZoom, Math.min(maxZoom, newZoom));
        newZoom = Math.round(newZoom * 100) / 100;
        
        const rect = workspace.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const zoomRatio = newZoom / currentZoom;
        
        panX = mouseX - (mouseX - panX) * zoomRatio;
        panY = mouseY - (mouseY - panY) * zoomRatio;
        
        currentZoom = newZoom;
        applyTransform();
        saveState(); 
    }

    // --- 9. ИНИЦИАЛИЗАЦИЯ И РЕГИСТРАЦИЯ ВСЕХ СОБЫТИЙ ---

    function setupEventListeners() {
        profileSelect.addEventListener('change', handleProfileChange);
        newProfileButton.addEventListener('click', handleNewProfile);
        deleteProfileButton.addEventListener('click', handleDeleteProfile);
        saveProfileButton.addEventListener('click', saveState);
        
        // Подсказки
        const toggleHintsButton = document.getElementById('toggleHintsButton');
        const hintsDiv = document.getElementById('hints');
        toggleHintsButton.addEventListener('click', () => {
            hintsDiv.classList.toggle('visible');
            toggleHintsButton.textContent = hintsDiv.classList.contains('visible') ? 'Скрыть подсказки' : 'Подсказки';
        });

        // Создание узла (Двойной клик Мышью)
        workspace.addEventListener('dblclick', (e) => {
            if (e.target !== workspace && e.target !== canvas) return;
            const rect = workspace.getBoundingClientRect();
            const rawX = (e.clientX - rect.left - panX) / currentZoom;
            const rawY = (e.clientY - rect.top - panY) / currentZoom;
            const nodeWidth = 220; const nodeHeight = 90; 
            createNode(rawX - (nodeWidth / 2), rawY - (nodeHeight / 2));
            saveState();
        });

        // Создание узла (Двойной тап Touch)
        workspace.addEventListener('touchend', (e) => {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTapWorkspace;
            
            if (tapLength < 500 && tapLength > 50 && e.touches.length === 0) {
                 if (e.target !== workspace && e.target !== canvas) return;
                
                const rect = workspace.getBoundingClientRect();
                const clientX = e.changedTouches[0].clientX - rect.left;
                const clientY = e.changedTouches[0].clientY - rect.top;
                
                const rawX = (clientX - panX) / currentZoom;
                const rawY = (clientY - panY) / currentZoom;
                const nodeWidth = 220; const nodeHeight = 90; 
                createNode(rawX - (nodeWidth / 2), rawY - (nodeHeight / 2));
                saveState();
            }
            lastTapWorkspace = currentTime;
        }, false);
        
        // Touch events для всех взаимодействий
        workspace.addEventListener('touchstart', handleTouchStart, { passive: false });

        // Панорамирование Мышью
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !isPanning && e.target.tagName !== 'INPUT' && activeTouches.length === 0) { workspace.style.cursor = 'grab'; }
        });

        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space') { workspace.style.cursor = 'default'; isPanning = false; }
        });
        workspace.addEventListener('mousedown', startPanning); 
        
        // Зум колесиком Мыши
        workspace.addEventListener('wheel', handleZoom, { passive: false });
    }

    // --- 10. ПЕРВИЧНАЯ ЗАГРУЗКА ---
    function initialize() {
        setupEventListeners();
        
        const profileList = getProfileList();
        updateProfileSelect(profileList[0].name);
        loadState(profileList[0].name);
    }
    
    initialize(); 
});
