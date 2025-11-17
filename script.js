// === ИНИТ & СПАВН ===
function init() {
    entities = [];
    player = new Player();
    
    // 1. Установка игрока в центр первой комнаты
    const c = player.getRoomCenter(0);
    player.x = c.x;
    player.y = c.y;

    // 2. Установка начального положения камеры на игрока
    camera.x = player.x - canvas.width / (2 * CONFIG.ZOOM);
    camera.y = player.y - canvas.height / (2 * CONFIG.ZOOM);
    camera.targetX = camera.x;
    camera.targetY = camera.y;

    for (let i = 0; i < 4; i++) {
        const mobLvl = 10 + i * 5; 
        for (let j = 0; j < 5; j++) spawnMob(i, mobLvl);
    }
    
    if (mobSpawnInterval) clearInterval(mobSpawnInterval);
    mobSpawnInterval = setInterval(spawnMob, CONFIG.MOB_RESPAWN_TIME);
    
    checkLevel();
}

// === КЛАСС Player (ВАЖНОЕ ИЗМЕНЕНИЕ) ===
class Player extends Unit {
    constructor() { 
        super(160, 160, 'player', '⚒️', '#ff6b6b', 250, 16, 9, 0); 
        this.maxHp = 250;
    }
    
    // ... (функция heal остается без изменений) ...

    update() {
        // ESSENCE STYLE: Персонаж ВСЕГДА стоит в центре своей комнаты (статика)
        const room = Math.floor(this.x / CONFIG.ROOM_SIZE) + Math.floor(this.y / CONFIG.ROOM_SIZE) * 2;
        const center = this.getRoomCenter(room);
        
        // Перемещаем игрока только если он почему-то оказался в другой комнате
        if (this.x !== center.x || this.y !== center.y) {
           this.x = center.x;
           this.y = center.y;
        }

        // 1. АВТО-ФАРМ ЛОГИКА (ВСЕГДА АКТИВНА)
        if (!selectedTarget || selectedTarget.hp <= 0) {
            selectedTarget = entities
                .filter(e => e.type === 'mob' && e.hp > 0 && dist(this, e) < CONFIG.ATTACK_RANGE * 2) // Увеличенный радиус поиска
                .sort((a,b) => dist(player,a) - dist(player,b))[0];
        } else if (selectedTarget && selectedTarget.hp <= 0) {
            selectedTarget = null;
        }

        // 2. Атака по цели
        if (selectedTarget && selectedTarget.hp > 0) {
            this.attack(selectedTarget);
        }
    }
}

// === ОБНОВЛЕНИЕ КАМЕРЫ ===
function updateCamera() {
    // В Essence-стиле камера должна быть строго центрирована на игроке, без сглаживания
    camera.targetX = player.x - canvas.width/(2*CONFIG.ZOOM);
    camera.targetY = player.y - canvas.height/(2*CONFIG.ZOOM);
    
    // Мгновенное обновление камеры (без сглаживания для AFK)
    camera.x = camera.targetX;
    camera.y = camera.targetY;
    
    const maxCamX = CONFIG.ROOM_SIZE*2 - canvas.width/CONFIG.ZOOM;
    const maxCamY = CONFIG.ROOM_SIZE*2 - canvas.height/CONFIG.ZOOM;
    
    camera.x = Math.max(0, Math.min(camera.x, maxCamX));
    camera.y = Math.max(0, Math.min(camera.y, maxCamY));
}
