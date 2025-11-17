// === ГЛОБАЛЬНЫЕ ===
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const logEl = document.getElementById('log');

let entities = [];
let player, pet = { 
    level:1, exp:0, expToNext:100, 
    spoilLevel:1, spoilExp:0, spoilToNext:100, 
    adena:0, crystals:0, mats:0,
    weaponLevel: 0, armorLevel: 0,
    crystalChanceLevel: 0,
    spoilBonusLevel: 0, 
    farmSpeedLevel: 0, 
    hpRegenRate: 0, 
};
let camera = { x:0, y:0 }; 
let selectedTarget = null;
let mobSpawnInterval;

const CONFIG = {
  ROOM_SIZE: 320,
  ATTACK_RANGE: 300, 
  ATTACK_SPEED_BASE: 1000, 
  SPEED_REDUCTION_PER_LEVEL: 0.05, 
  SPOIL_CHANCE_BASE: 0.35, 
  CHANCE_PER_SPOIL_LEVEL: 0.05, 
  CRYSTAL_CHANCE_BASE: 0.10, 
  CRYSTAL_CHANCE_PER_LEVEL: 0.05,
  MOB_RESPAWN_TIME: 4000, 
  ZOOM: 1.7,
};

// === СТОИМОСТЬ МАГАЗИНА ===
const SHOP_COST = {
    WEAPON_BASE_A: 500,
    ARMOR_BASE_A: 500,
    FARM_SPEED_C: 10,
    HP_REGEN_M: 10,
    CRYSTAL_CHANCE_M: 15,
    SPOIL_CHANCE_C: 15
};

// === РЕСАЙЗ ===
function resize() {
  // КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Используем clientWidth/Height для синхронизации с CSS
  canvas.width = canvas.clientWidth;
  canvas.height = canvas.clientHeight; 
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  
  // КРИТИЧЕСКАЯ ПЕРЕЦЕНТРОВКА КАМЕРЫ ПОСЛЕ РЕСАЙЗА
  if (player) {
      const c = player.getRoomCenter(0);
      player.x = c.x;
      player.y = c.y;
      camera.x = player.x - canvas.width / (2 * CONFIG.ZOOM);
      camera.y = player.y - canvas.height / (2 * CONFIG.ZOOM);
  }
}
window.addEventListener('resize', resize);

// === АВТОКРИСТАЛЛИЗАЦИЯ ===
function autoCrystallize() {
    if (pet.mats <= 0) return;
    const chance = CONFIG.CRYSTAL_CHANCE_BASE + pet.crystalChanceLevel * CONFIG.CRYSTAL_CHANCE_PER_LEVEL;
    pet.mats--; 
    if (Math.random() < chance) {
        pet.crystals += 1; 
        log(`[CRYSTAL] +1 C`, '#00ffff');
    } 
    checkLevel();
}

// === ТИК РЕГЕНЕРАЦИИ ===
function regenerationTick() {
    if (player && player.hp > 0 && pet.hpRegenRate > 0) {
        player.heal(pet.hpRegenRate * 1); 
    }
    if (pet.mats > 0) {
         autoCrystallize();
    }
}
setInterval(regenerationTick, 1000); 

// === КЛАССЫ ===
class Unit {
  constructor(x, y, type, symbol, color, hp, str, def, mobLvl=1) {
    this.x = x; this.y = y; this.type = type; this.symbol = symbol;
    this.color = color; this.hp = hp; this.maxHp = hp;
    this.baseStr = str; this.baseDef = def; 
    this.mobLvl = mobLvl; 
    this.target = null;
    this.spoiled = false; 
    this.lastAttack = 0; 
    entities.push(this);
  }
  
  get str() {
      if (this.type === 'player') return this.baseStr + pet.weaponLevel;
      return this.baseStr;
  }
  
  get def() {
      if (this.type === 'player') return this.baseDef + pet.armorLevel;
      return this.baseDef;
  }
  
  distTo(t) { return Math.hypot(this.x - t.x, this.y - t.y); }
  
  moveTo(tx, ty, s) { return true; } 
  
  attack(t) {
    const now = Date.now();
    let attackDelay = CONFIG.ATTACK_SPEED_BASE;
    
    if (this.type === 'player') {
         attackDelay *= (1 - pet.farmSpeedLevel * CONFIG.SPEED_REDUCTION_PER_LEVEL);
    }

    if (!t || t.hp <= 0 || this.distTo(t) > CONFIG.ATTACK_RANGE || now - this.lastAttack < attackDelay) return;
    
    this.lastAttack = now;

    if (this.type === 'player') {
        this.autoSpoil(t);
    }
    
    const dmg = Math.max(1, this.str - t.def + (Math.random()*3|0)); 
    t.hp -= dmg;
    log(`${this.symbol} → ${t.symbol}: -${dmg}`, this.color);
    
    if (t.hp <= 0) { 
        this.onKill(t); 
        t.die(); 
        this.target = null;
    }
  }
  
  autoSpoil(t) {
    if (t.spoiled || t.type !== 'mob' || t.hp <= 0) return;
    
    const globalSpoilBonus = pet.spoilBonusLevel * CONFIG.CHANCE_PER_SPOIL_LEVEL;
    const chance = CONFIG.SPOIL_CHANCE_BASE + (pet.spoilLevel-1) * CONFIG.CHANCE_PER_SPOIL_LEVEL + globalSpoilBonus;
    
    if (Math.random() < chance) {
      t.spoiled = true;
      log(`[SPOIL] УСПЕХ`, '#ffd700');
      addEffect(t.x, t.y, `SPOIL!`);
    }
  }
  
  autoSweep(t) {
      if (t.type !== 'mob' || !t.spoiled || t.hp > 0) return;
      
      const chance = CONFIG.SPOIL_CHANCE_BASE + (pet.spoilLevel-1) * CONFIG.CHANCE_PER_SPOIL_LEVEL;
      
      if (Math.random() < chance) {
          let dropType, amount;
          
          if (Math.random() < 0.5) { 
              dropType = 'Crystal: D';
              amount = 1 + (Math.random()*4|0);
              pet.crystals += amount;
          } else {
              const items = ['Animal Bone', 'Iron Ore', 'Craft Leather', 'Bone Dust'];
              dropType = items[Math.floor(Math.random()*items.length)];
              amount = 2 + (Math.random()*5|0);
              pet.mats += amount;
          }
          
          log(`[SWEEP] +${dropType} x${amount}`, '#00ff00');
          addEffect(t.x, t.y, `+${dropType}`);
          
          pet.spoilExp += 20 * amount; 
          checkLevel();
      } else {
          log(`[SWEEP] ПРОВАЛ.`, '#ff0000');
      }
  }

  onKill(t) {
    if (t.spoiled) {
         this.autoSweep(t);
    } else {
         pet.adena += 100 + (Math.random()*150|0);
         pet.exp += 30;
    }
    checkLevel();
  }
  
  die() {
    if (this.type === 'player') { /* ... */ }
    if (selectedTarget === this) selectedTarget = null;
    if (this.type === 'mob') {
        entities = entities.filter(e => e !== this);
        const room = this.getRoom();
        setTimeout(() => spawnMob(room), CONFIG.MOB_RESPAWN_TIME);
    }
  }
  
  getRoomCenter(r) {
    const rx = r % 2, ry = Math.floor(r / 2);
    return { x: rx * CONFIG.ROOM_SIZE + CONFIG.ROOM_SIZE/2, y: ry * CONFIG.ROOM_SIZE + CONFIG.ROOM_SIZE/2 };
  }

  aiTick() {
    if (this.hp <= 0) return;
    if (this.type === 'mob') {
      const nearest = entities.find(e => e.type === 'player' && dist(this, e) < CONFIG.ATTACK_RANGE * 2);
      if (nearest) this.target = nearest;

      if (this.target) {
        this.attack(this.target);
      }
    }
  }
}

class Player extends Unit {
  constructor() { 
      super(160, 160, 'player', '⚒️', '#ff6b6b', 250, 16, 9, 0); 
      this.maxHp = 250;
  }
  
  heal(amount) { 
      this.hp = Math.min(this.maxHp, this.hp + amount); 
  }
  
  update() {
    // ESSENCE STYLE: Персонаж ВСЕГДА стоит в центре своей комнаты (статика)
    const room = Math.floor(this.x / CONFIG.ROOM_SIZE) + Math.floor(this.y / CONFIG.ROOM_SIZE) * 2;
    const center = this.getRoomCenter(room);
    this.x = center.x;
    this.y = center.y;

    // 1. АВТО-ФАРМ ЛОГИКА
    if (!selectedTarget || selectedTarget.hp <= 0) {
        selectedTarget = entities
            .filter(e => e.type === 'mob' && e.hp > 0 && dist(this, e) < CONFIG.ATTACK_RANGE * 2) 
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

// === ФУНКЦИИ ===
function addEffect(x, y, text) {
  const el = document.createElement('div');
  el.className = 'spoil-effect';
  el.textContent = text;
  el.style.left = (x * CONFIG.ZOOM - camera.x * CONFIG.ZOOM) + 'px';
  el.style.top = (y * CONFIG.ZOOM - camera.y * CONFIG.ZOOM) + 'px';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1000);
}

function dist(a,b) { return Math.hypot(a.x-b.x, a.y-b.y); }

function log(msg, color='#fff') {
  const d = document.createElement('div');
  d.textContent = msg;
  d.style.color = color;
  logEl.prepend(d);
  while (logEl.children.length > 30) { logEl.removeChild(logEl.lastChild); }
}

// === CHECKLEVEL & UI UPDATE ===
function checkLevel() {
  if (pet.exp >= pet.expToNext) { 
    pet.level++; 
    pet.exp = pet.exp - pet.expToNext;
    pet.expToNext = Math.floor(pet.expToNext * 1.5 + 100); 
    player.maxHp = Math.floor(player.maxHp * 1.2); 
    player.heal(player.maxHp);
    log(`УРОВЕНЬ ${pet.level} UP! HP Max: ${player.maxHp}`, '#00ff00'); 
  }
  if (pet.spoilExp >= pet.spoilToNext) { 
    pet.spoilLevel++; 
    pet.spoilExp = pet.spoilExp - pet.spoilToNext; 
    pet.spoilToNext = Math.floor(pet.spoilToNext * 1.5 + 50); 
    log(`СПОЙЛ УРОВЕНЬ ${pet.spoilLevel} UP!`, '#ffd700'); 
  }
  
  document.getElementById('level').textContent = pet.level;
  document.getElementById('str').textContent = player.str;
  document.getElementById('def').textContent = player.def;
  document.getElementById('expBar').style.width = (pet.exp / pet.expToNext * 100) + '%';
  
  document.getElementById('spoilLevel').textContent = pet.spoilLevel;
  document.getElementById('spoilBar').style.width = (pet.spoilExp / pet.spoilToNext * 100) + '%';
  
  document.getElementById('adena').textContent = pet.adena;
  document.getElementById('crystals').textContent = pet.crystals;
  document.getElementById('mats').textContent = pet.mats;
  
  document.getElementById('allySpoilBonus').textContent = (pet.spoilBonusLevel * CONFIG.CHANCE_PER_SPOIL_LEVEL * 100) + '%';
  document.getElementById('hpReg').textContent = pet.hpRegenRate;
  document.getElementById('crystalChance').textContent = (CONFIG.CRYSTAL_CHANCE_BASE * 100 + pet.crystalChanceLevel * CONFIG.CRYSTAL_CHANCE_PER_LEVEL * 100) + '%';
  
  const hpWidth = (player.hp / player.maxHp * 100);
  canvas.style.boxShadow = `0 0 30px ${hpWidth < 20 ? '#ff0000' : '#330000'} inset`;
  
  document.getElementById('buyWeapon').textContent = `Оружие +${pet.weaponLevel+1} [${SHOP_COST.WEAPON_BASE_A * (pet.weaponLevel + 1)} A]`;
  document.getElementById('buyArmor').textContent = `Броня +${pet.armorLevel+1} [${SHOP_COST.ARMOR_BASE_A * (pet.armorLevel + 1)} A]`;
  document.getElementById('upgradeSpd').textContent = `FARM SPD (+${pet.farmSpeedLevel+1}%) [${SHOP_COST.FARM_SPEED_C * (pet.farmSpeedLevel + 1)} C]`;
  document.getElementById('buyHpReg').textContent = `HP REG (+1/s) [${SHOP_COST.HP_REGEN_M * (pet.hpRegenRate + 1)} M]`;
}

function checkSpoil() { checkLevel(); } 
function reset() { /* ... */ init(); }

// === ИНИТ & СПАВН ===
function init() {
  entities = [];
  player = new Player();
  
  const c = player.getRoomCenter(0);
  player.x = c.x;
  player.y = c.y;
  
  // КРИТИЧЕСКАЯ ИНИЦИАЛИЗАЦИЯ КАМЕРЫ
  resize(); 
  camera.x = player.x - canvas.width / (2 * CONFIG.ZOOM);
  camera.y = player.y - canvas.height / (2 * CONFIG.ZOOM);

  for (let i = 0; i < 4; i++) {
    const mobLvl = 10 + i * 5; 
    for (let j = 0; j < 5; j++) spawnMob(i, mobLvl); 
  }
  
  if (mobSpawnInterval) clearInterval(mobSpawnInterval);
  mobSpawnInterval = setInterval(spawnMob, CONFIG.MOB_RESPAWN_TIME);
  
  checkLevel();
}

function spawnMob(room = Math.floor(Math.random()*4), mobLvl = 10 + room * 5) {
  const mobsInRoom = entities.filter(e => e.type === 'mob' && e.getRoom() === room).length;
  if (mobsInRoom >= 7) return; 

  const c = player.getRoomCenter(room);
  new Unit(
    c.x + Math.random()*150-75, 
    c.y + Math.random()*150-75, 
    'mob', 
    Math.random() > 0.5 ? '💀' : '👹', 
    '#ff4444', 
    90 + mobLvl*5, 
    9 + Math.floor(mobLvl/5), 
    5 + Math.floor(mobLvl/10), 
    mobLvl
  );
}

// === ЛОГИКА МАГАЗИНА ===
document.getElementById('buyWeapon').addEventListener('click', () => {
    const cost = SHOP_COST.WEAPON_BASE_A * (pet.weaponLevel + 1);
    if (pet.adena >= cost) {
        pet.adena -= cost;
        pet.weaponLevel++;
        log(`Куплено: Оружие +${pet.weaponLevel}. STR: +1`, '#ff6b6b');
        checkLevel();
    } else { log(`Недостаточно адены (нужно ${cost} A)!`, '#ff0000'); }
});

document.getElementById('buyArmor').addEventListener('click', () => {
    const cost = SHOP_COST.ARMOR_BASE_A * (pet.armorLevel + 1);
    if (pet.adena >= cost) {
        pet.adena -= cost;
        pet.armorLevel++;
        log(`Куплено: Броня +${pet.armorLevel}. DEF: +1`, '#00ff88');
        checkLevel();
    } else { log(`Недостаточно адены (нужно ${cost} A)!`, '#ff0000'); }
});

document.getElementById('upgradeSpd').addEventListener('click', () => {
    const cost = SHOP_COST.FARM_SPEED_C * (pet.farmSpeedLevel + 1);
    if (pet.crystals >= cost) {
        pet.crystals -= cost;
        pet.farmSpeedLevel++;
        log(`Скорость фарма +${pet.farmSpeedLevel}!`, '#00ff88');
        checkLevel();
    } else { log(`Недостаточно пудр (нужно ${cost} C)!`, '#ff0000'); }
});

document.getElementById('buyHpReg').addEventListener('click', () => {
    const cost = SHOP_COST.HP_REGEN_M * (pet.hpRegenRate + 1);
    if (pet.mats >= cost) {
        pet.mats -= cost;
        pet.hpRegenRate++;
        log(`Реген HP +1/s!`, '#ff0000');
        checkLevel();
    } else { log(`Недостаточно материалов (нужно ${cost} M)!`, '#ff0000'); }
});

document.getElementById('upgradeCrystal').addEventListener('click', () => {
    const cost = SHOP_COST.CRYSTAL_CHANCE_M;
    if (pet.mats >= cost) {
        pet.mats -= cost;
        pet.crystalChanceLevel++; 
        log(`Шанс кристаллизации увеличен!`, '#00ffff');
        checkLevel();
    } else { log(`Недостаточно материалов (нужно ${cost} M)!`, '#ff0000'); }
});

document.getElementById('upgradeSpoil').addEventListener('click', () => {
    const cost = SHOP_COST.SPOIL_CHANCE_C * (pet.spoilBonusLevel + 1);
    if (pet.crystals >= cost) {
        pet.crystals -= cost;
        pet.spoilBonusLevel++; 
        log(`Шанс Spoil увеличен!`, '#ffd700');
        checkLevel();
    } else { log(`Недостаточно пудр (нужно ${cost} C)!`, '#ff0000'); }
});

// === РЕНДЕР & ЛУП ===
function render() {
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.save();
  
  // Применяем камеру
  ctx.translate(-camera.x * CONFIG.ZOOM, -camera.y * CONFIG.ZOOM);
  ctx.scale(CONFIG.ZOOM, CONFIG.ZOOM);

  // Карта
  ctx.fillStyle = '#222';
  ctx.fillRect(0,0,CONFIG.ROOM_SIZE*2,CONFIG.ROOM_SIZE*2);
  ctx.strokeStyle = '#555';
  ctx.lineWidth = 4;
  for (let i=0; i<=2; i++) {
    ctx.beginPath();
    ctx.moveTo(i*CONFIG.ROOM_SIZE, 0);
    ctx.lineTo(i*CONFIG.ROOM_SIZE, CONFIG.ROOM_SIZE*2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, i*CONFIG.ROOM_SIZE);
    ctx.lineTo(CONFIG.ROOM_SIZE*2, i*CONFIG.ROOM_SIZE);
    ctx.stroke();
  }

  // Юниты
  entities.forEach(e => {
    if (e.hp <= 0) return; 

    if (e === selectedTarget) {
      ctx.strokeStyle = '#ffff00';
      ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(e.x, e.y, 25, 0, Math.PI*2); ctx.stroke();
    }
    
    ctx.font = '36px Arial';
    ctx.fillText(e.symbol, e.x, e.y + 2);
    
    if (e.hp > 0) {
        ctx.fillStyle = '#ff0000';
        ctx.fillRect(e.x-22, e.y-35, 44, 6);
        ctx.fillStyle = '#44ff44';
        ctx.fillRect(e.x-22, e.y-35, 44*(e.hp/e.maxHp), 6);
    }
    
    if (e.spoiled) {
       ctx.fillStyle = '#ffd700';
       ctx.font = '10px Arial';
       ctx.fillText('SPOIL', e.x, e.y - 40);
    }
    
    ctx.fillStyle = '#fff';
    ctx.font = '8px Arial';
    const statText = `L${e.mobLvl || e.level} STR:${e.str} DEF:${e.def}`;
    ctx.fillText(statText, e.x, e.y - 45);
  });

  ctx.restore();
}

function updateCamera() {
  // Камера центрируется на игроке (x, y)
  camera.x = player.x - canvas.width / (2 * CONFIG.ZOOM);
  camera.y = player.y - canvas.height / (2 * CONFIG.ZOOM);
}

function loop() {
  player.update();
  entities.forEach(e => { if (e !== player) e.aiTick(); });
  updateCamera();
  render();
  requestAnimationFrame(loop);
}

// === ОБРАБОТКА КЛИКА ===
canvas.addEventListener('touchstart', e => {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  
  const tx = (e.touches[0].clientX - rect.left) / CONFIG.ZOOM + camera.x;
  const ty = (e.touches[0].clientY - rect.top) / CONFIG.ZOOM + camera.y;
  
  selectedTarget = entities.find(ent => ent !== player && ent.hp > 0 && dist(ent, {x:tx, y:ty}) < 40);
});

// Запуск
resize();
init();
loop();
