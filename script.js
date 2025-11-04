document.addEventListener('DOMContentLoaded', (event) => {
    
    // --- 1. Константы и элементы интерфейса ---
    const UNIQUE_PROFILE_KEY = 'hrain_user_data'; // Единый ключ для всех данных
    
    const workspace = document.getElementById('workspace');
    const canvas = document.getElementById('canvas');
    const saveProfileButton = document.getElementById('saveProfileButton');
    
    // --- 2. Глобальные переменные ---
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
    let lastMouseX = 0;
    let lastMouseY = 0;

    // --- 3. ФУНКЦИИ БЕЗОПАСНОГО ВЗАИМОДЕЙСТВИЯ С ХРАНИЛИЩЕМ ---
    
    function safeGetItem(key) {
        try {
            return localStorage.getItem(key);
        } catch (e) {
            console.error("localStorage заблокирован или недоступен:", e);
            return null;
        }
    }

    function safeSetItem(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (e) {
            console.error("localStorage заблокирован или недоступен:", e);
            return false;
        }
    }

    // --- 4. ФУНКЦИИ ТРАНСФОРМАЦИИ И СОХРАНЕНИЯ ---

    function applyTransform() {
        canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
    }

    function clearWorkspace() {
        canvas.innerHTML = '';
        nodeIdCounter = 0; 
        connectingNodeId = null;
        currentZoom = 1;
        panX = 0;
        panY = 0;
        
        applyTransform();
    }
    
    function createInitialState() {
        return {
            nodes: {},
            links: [],
            zoom: 1,
            panX: 0, 
            panY: 0
        };
    }

    function saveState() {
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
        safeSetItem(UNIQUE_PROFILE_KEY, JSON.stringify(state));
    }
    
    function loadState() {
        clearWorkspace(); 

        const savedState = safeGetItem(UNIQUE_PROFILE_KEY);
        
        if (!savedState) {
            // Инициализация, если данных нет
            const initialState = createInitialState();
            safeSetItem(UNIQUE_PROFILE_KEY, JSON.stringify(initialState));
            
            // Создаем и сохраняем начальный узел
            createNode(50, 50, "Начало работы"); 
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
    }

    // --- 5. ФУНКЦИИ УЗЛОВ И СВЯЗЕЙ ---
    
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
        
        // Двойной клик для НЕМЕДЛЕННОГО удаления узла (облака)
        node.addEventListener('dblclick', (e) => {
            e.stopPropagation(); 
            // Снимаем все выделения
            document.querySelectorAll('.node').forEach(n => n.classList.remove('selected-for-delete', 'selected'));
            connectingNodeId = null; 
            
            // Выполняем удаление
            deleteNodeAndConnections(nodeId);
        });
        
        // Логика одинарного клика для соединения
        node.addEventListener('click', (e) => {
            if (isDraggingNode) return; 
            e.stopPropagation(); 
            
            // Снимаем выделение для удаления со всех
            document.querySelectorAll('.node').forEach(n => n.classList.remove('selected-for-delete'));
            
            // Обработка соединения
            handleNodeConnect(nodeId);
        });
        
        return node;
    }
    
    function handleNodeConnect(nodeId) {
        const node = document.getElementById(nodeId);
        
        // Снимаем режим соединения со всех, кроме текущего
        document.querySelectorAll('.node').forEach(n => {
            if (n.id !== nodeId) n.classList.remove('selected');
        });

        if (connectingNodeId === null) {
            // Активируем режим соединения (первый клик)
            connectingNodeId = nodeId;
            node.classList.add('selected');
        } else if (connectingNodeId === nodeId) {
            // Отменяем режим соединения (клик по себе же)
            connectingNodeId = null;
            node.classList.remove('selected');
        } else {
            // Завершаем соединение (второй клик)
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
                
                saveState();
            }

            document.getElementById(sourceId).classList.remove('selected');
            connectingNodeId = null;
        }
    }
    
    // --- НОВАЯ ФУНКЦИЯ createLink С ИСПРАВЛЕННОЙ ГЕОМЕТРИЕЙ ---
    function createLink(sourceId, targetId) {
        const linkKey = [sourceId, targetId].sort().join('-'); 
        let line = document.getElementById(linkKey);
        
        // Удаляем старую линию, если она уже существует
        if (line) line.remove();
        
        const sourceNode = document.getElementById(sourceId);
        const targetNode = document.getElementById(targetId);
        
        if (!sourceNode || !targetNode) return; 

        // --- 1. Функция для нахождения точки на границе узла ---
        function findNodeBoundaryPoint(node, targetPoint) {
            
            // Получаем позицию узла относительно canvas (не экрана)
            const nodeX = node.offsetLeft;
            const nodeY = node.offsetTop;
            
            // Получаем размеры узла (учитывая его scale)
            const scale = parseFloat(node.dataset.scale || 1);
            const width = node.offsetWidth * scale;
            const height = node.offsetHeight * scale;

            // Координаты центра узла
            const centerX = nodeX + width / 2;
            const centerY = nodeY + height / 2;

            // Вектор от центра узла до целевой точки
            const dx = targetPoint.x - centerX;
            const dy = targetPoint.y - centerY;

            // Углы и радиусы для расчета
            const absDx = Math.abs(dx);
            const absDy = Math.abs(dy);

            let tx, ty;

            // Ищем точку пересечения с границами
            if (absDx / width >= absDy / height) {
                // Пересечение происходит по горизонтали (слева или справа)
                tx = width / 2;
                if (dx < 0) tx = -tx; 
                
                ty = tx * dy / dx; 
            } else {
                // Пересечение происходит по вертикали (сверху или снизу)
                ty = height / 2;
                if (dy < 0) ty = -ty; 
                
                tx = ty * dx / dy; 
            }

            return {
                x: centerX + tx,
                y: centerY + ty
            };
        }
        // --- Конец findNodeBoundaryPoint ---

        // --- 2. Определяем центры узлов для расчета направления ---
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

        // --- 3. Находим точки на границах узлов ---
        // Точка выхода из Source (граница) - использует центр Target для направления
        const p1 = findNodeBoundaryPoint(sourceNode, targetCenter); 
        // Точка входа в Target (граница) - использует центр Source для направления
        const p2 = findNodeBoundaryPoint(targetNode, sourceCenter); 


        // --- 4. Расчет длины и угла для линии ---
        const length = Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2);
        const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x) * (180 / Math.PI);
        
        line = document.createElement('div');
        line.className = 'link-line';
        line.id = linkKey;
        line.style.width = `${length}px`;
        // Линия начинается от точки p1
        line.style.left = `${p1.x}px`;
        line.style.top = `${p1.y}px`;
        line.style.transform = `rotate(${angle}deg)`;
        line.dataset.source = sourceId;
        line.dataset.target = targetId;

        // Двойной клик для удаления связи
        line.addEventListener('dblclick', (e) => {
            e.stopPropagation(); 
            const sId = e.target.dataset.source;
            const tId = e.target.dataset.target;
            
            if (sId && tId) {
                 deleteLink(sId, tId);
            }
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
        }

        if (targetNode) {
            let tConnections = JSON.parse(targetNode.dataset.connections);
            targetNode.dataset.connections = JSON.stringify(tConnections.filter(id => id !== sId));
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
            const otherId = otherNode.id;
            if (otherId === nodeId) return; 

            let connections = JSON.parse(otherNode.dataset.connections);
            const newConnections = connections.filter(id => id !== nodeId);
            
            if (newConnections.length !== connections.length) {
                otherNode.dataset.connections = JSON.stringify(newConnections);
            }
        });
        
        node.remove();
        if (connectingNodeId === nodeId) {
            connectingNodeId = null;
        }
        
        saveState(); 
    }


    // --- 6. ОБРАБОТЧИКИ DRAG & DROP, ПАНОРАМИРОВАНИЯ И ЗУМА ---
    
    function startNodeDrag(e) {
        if (e.button !== 0 || e.target.classList.contains('scale-button')) return; 
        if (e.target.tagName === 'INPUT') return; 
        
        e.preventDefault(); 
        isDraggingNode = false;
        currentDraggedNode = e.currentTarget;
        
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
        
        document.addEventListener('mousemove', dragNode);
        document.addEventListener('mouseup', stopNodeDrag);
        
        currentDraggedNode.classList.remove('selected-for-delete'); 
    }
    
    function dragNode(e) {
        if (!currentDraggedNode) return;
        
        const dx = e.clientX - lastMouseX;
        const dy = e.clientY - lastMouseY;
        
        isDraggingNode = true; 

        let newLeft = currentDraggedNode.offsetLeft + dx / currentZoom;
        let newTop = currentDraggedNode.offsetTop + dy / currentZoom;

        // Корректное обновление позиции
        currentDraggedNode.style.top = `${newTop}px`;
        currentDraggedNode.style.left = `${newLeft}px`; 
        
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;

        updateAllConnections(currentDraggedNode.id); 
    }
    
    function stopNodeDrag() {
        if (currentDraggedNode) {
            currentDraggedNode = null;
            if (isDraggingNode) {
                saveState(); 
            }
            isDraggingNode = false; 
        }
        document.removeEventListener('mousemove', dragNode);
        document.removeEventListener('mouseup', stopNodeDrag);
    }

    function startPanning(e) {
        if (e.target.closest('.node') || e.button !== 0 || e.target.tagName === 'INPUT') return; 
        
        if ((e.code === 'Space' || e.key === ' ' || e.target === workspace || e.target === canvas) && !isPanning) {
            e.preventDefault(); 
            isPanning = true;
            workspace.style.cursor = 'grabbing';
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
            
            document.addEventListener('mousemove', panCanvas);
            document.addEventListener('mouseup', stopPanning);
        }
    }
    
    function panCanvas(e) {
        if (!isPanning) return;
        e.preventDefault();
        
        const dx = e.clientX - lastMouseX;
        const dy = e.clientY - lastMouseY;
        
        panX += dx;
        panY += dy;
        
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
        
        applyTransform();
    }
    
    function stopPanning() {
        if (isPanning) {
            isPanning = false;
            workspace.style.cursor = 'default';
            saveState(); 
        }
        document.removeEventListener('mousemove', panCanvas);
        document.removeEventListener('mouseup', stopPanning);
    }
    
    function handleZoom(e) {
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
    
    // --- 7. ИНИЦИАЛИЗАЦИЯ И РЕГИСТРАЦИЯ ВСЕХ СОБЫТИЙ ---

    function setupEventListeners() {
        // Сохранение
        saveProfileButton.addEventListener('click', saveState);
        
        // Кнопка подсказок
        const toggleHintsButton = document.getElementById('toggleHintsButton');
        const hintsDiv = document.getElementById('hints');

        toggleHintsButton.addEventListener('click', () => {
            hintsDiv.classList.toggle('visible');
            
            if (hintsDiv.classList.contains('visible')) {
                toggleHintsButton.textContent = 'Скрыть подсказки';
            } else {
                toggleHintsButton.textContent = 'Подсказки';
            }
        });

        // Создание узла (Двойной клик)
        workspace.addEventListener('dblclick', (e) => {
            // Проверяем, что клик был на пустом пространстве
            if (e.target !== workspace && e.target !== canvas) return;
            
            const rect = workspace.getBoundingClientRect();
            const clientX = e.clientX - rect.left;
            const clientY = e.clientY - rect.top;
            
            // Преобразование координат с учетом зума и панорамирования
            const rawX = (clientX - panX) / currentZoom;
            const rawY = (clientY - panY) / currentZoom;
            
            const nodeWidth = 220; 
            const nodeHeight = 90; 
            const x = rawX - (nodeWidth / 2); 
            const y = rawY - (nodeHeight / 2);
            
            createNode(x, y);
            saveState();
        });
        
        // Панорамирование
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !isPanning && e.target.tagName !== 'INPUT') {
                workspace.style.cursor = 'grab';
            }
        });

        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space') {
                workspace.style.cursor = 'default';
                isPanning = false;
            }
        });
        workspace.addEventListener('mousedown', startPanning); 
        
        // Зум
        workspace.addEventListener('wheel', handleZoom);
    }

    // --- 8. ПЕРВИЧНАЯ ЗАГРУЗКА ---
    setupEventListeners();
    loadState(); 
});