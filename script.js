// ... (в разделе ГЛОБАЛЬНЫЕ)
// ...
// let selectedTarget = null; // Старая строка
let selectedTarget = null;
const STR_COST = 100; // Базовая стоимость STR/DEF
const SPOIL_CRYSTAL_COST = 5; // Стоимость улучшения спойла
// ...

// ... (в классе Player, внутри конструктора)
// ...
class Player extends Unit {
    constructor() { super(160, 160, 'player', '⚒️', '#ff6b6b', 250, 16, 9); } 
    
    // Переопределяем параметры для возможности изменения
    setStr(val) { this.str = val; log(`Сила: ${this.str}`, '#ff6b6b'); }
    setDef(val) { this.def = val; log(`Защита: ${this.def}`, '#00ff88'); }
    
    // Метод лечения, используется при покупке
    heal(amount) {
        this.hp = Math.min(this.maxHp, this.hp + amount);
        log(`Лечение +${amount} HP.`, '#44ff44');
    }
// ...
}


// ... (в конце скрипта, перед init() и loop())
// === СИСТЕМА УЛУЧШЕНИЙ ===
document.getElementById('buyStr').addEventListener('click', () => {
    const cost = STR_COST * player.str; // Увеличение стоимости
    if (pet.adena >= cost) {
        pet.adena -= cost;
        player.setStr(player.str + 1);
        player.heal(player.maxHp * 0.2); // Лечение на 20% при покупке
        document.getElementById('buyStr').textContent = `STR (+1) [${STR_COST * (player.str + 1)} A]`;
        checkLevel();
    } else {
        log(`Недостаточно адены (нужно ${cost} A)!`, '#ff0000');
    }
});

document.getElementById('buyDef').addEventListener('click', () => {
    const cost = STR_COST * player.def; // Увеличение стоимости
    if (pet.adena >= cost) {
        pet.adena -= cost;
        player.setDef(player.def + 1);
        player.heal(player.maxHp * 0.2); // Лечение на 20% при покупке
        document.getElementById('buyDef').textContent = `DEF (+1) [${STR_COST * (player.def + 1)} A]`;
        checkLevel();
    } else {
        log(`Недостаточно адены (нужно ${cost} A)!`, '#ff0000');
    }
});

document.getElementById('upgradeSpoil').addEventListener('click', () => {
    if (pet.crystals >= SPOIL_CRYSTAL_COST) {
        pet.crystals -= SPOIL_CRYSTAL_COST;
        // Мгновенное повышение уровня спойла (без EXP)
        pet.spoilLevel++;
        log(`Уровень спойла: ${pet.spoilLevel}!`, '#ffd700');
        checkLevel();
    } else {
        log(`Недостаточно пудр (нужно ${SPOIL_CRYSTAL_COST} C)!`, '#ff0000');
    }
});
// === КОНЕЦ СИСТЕМЫ УЛУЧШЕНИЙ ===

init();
loop();
