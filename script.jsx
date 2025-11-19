import React, { useState, useEffect, useRef } from 'react';

// --- КОНФИГ (База знаний игры) ---
const ITEMS_DB = {
  "fang": { id: "fang", name: "Wolf Fang", icon: "🦷", price: 5, type: "trash" },
  "potion": { id: "potion", name: "HP Potion", icon: "🍷", price: 20, type: "consumable", heal: 50 },
  "sword": { id: "sword", name: "Iron Sword", icon: "⚔️", price: 100, type: "weapon", atk: 10 }
};

const MOBS_DB = [
  { name: "Grey Wolf", hp: 60, maxHp: 60, atk: 5, xp: 15, loot: ["fang"], chance: 0.5 },
  { name: "Dire Wolf", hp: 100, maxHp: 100, atk: 12, xp: 35, loot: ["fang", "potion"], chance: 0.3 }
];

// --- СТИЛИ (Dark L2 Theme) ---
const styles = {
  app: { fontFamily: 'Consolas, monospace', background: '#121212', color: '#ccc', minHeight: '100vh', padding: '20px', display: 'flex', gap: '15px' },
  col: { background: '#1e1e1e', border: '1px solid #333', borderRadius: '6px', padding: '15px', display: 'flex', flexDirection: 'column' },
  left: { width: '280px' },
  center: { flex: 1, position: 'relative' },
  right: { width: '320px' },
  barBox: { background: '#333', height: '18px', marginTop: '5px', position: 'relative' },
  barFill: (pct, color) => ({ width: `${Math.max(0, Math.min(100, pct))}%`, background: color, height: '100%', transition: 'width 0.2s' }),
  btn: (active) => ({ background: active ? '#2e7d32' : '#37474f', color: '#fff', border: '1px solid #555', padding: '10px', cursor: 'pointer', margin: '5px 0', width: '100%', fontSize: '14px' }),
  log: { height: '200px', background: '#000', overflowY: 'auto', padding: '10px', fontSize: '12px', borderTop: '1px solid #444', fontFamily: 'monospace' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '4px', marginTop: '10px' },
  slot: { aspectRatio: '1/1', background: '#2a2a2a', border: '1px solid #444', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px', cursor: 'pointer', position: 'relative' },
  count: { position: 'absolute', bottom: 0, right: 2, fontSize: '10px', color: '#fff' }
};

export default function Game() {
  // --- СОСТОЯНИЕ ---
  const [player, setPlayer] = useState({
    hp: 150, maxHp: 150,
    xp: 0, maxXp: 100,
    lvl: 1,
    gold: 0,
    atk: 15
  });

  const [inventory, setInventory] = useState([]); // Массив ID предметов
  const [location, setLocation] = useState('CITY'); // CITY, FIGHT
  const [isAuto, setIsAuto] = useState(false); // Автобой вкл/выкл
  const [target, setTarget] = useState(null); // Текущий монстр
  const [logs, setLogs] = useState(["System: Welcome back, Hawkar."]);

  // Ссылка для авто-скролла лога
  const logEndRef = useRef(null);

  // --- ЛОГИКА (Движок) ---
  
  const addLog = (msg) => setLogs(prev => [...prev.slice(-14), msg]);

  // Генерация монстра
  const spawnMob = () => {
    const template = MOBS_DB[Math.floor(Math.random() * MOBS_DB.length)];
    setTarget({ ...template, id: Date.now() }); // id нужен чтобы React понимал что это новый моб
    addLog(`⚔️ A wild ${template.name} appeared!`);
  };

  // Получение лута
  const lootItem = (lootTable, chance) => {
    if (Math.random() > (1 - chance)) {
        const itemId = lootTable[Math.floor(Math.random() * lootTable.length)];
        setInventory(prev => [...prev, itemId]);
        addLog(`📦 You found: ${ITEMS_DB[itemId].name}`);
    }
  };

  // Продажа всего хлама
  const sellTrash = () => {
    let totalGold = 0;
    const newInv = inventory.filter(itemId => {
        const item = ITEMS_DB[itemId];
        if (item.type === 'trash') {
            totalGold += item.price;
            return false; // удаляем из инвентаря
        }
        return true; // оставляем
    });
    setInventory(newInv);
    setPlayer(p => ({...p, gold: p.gold + totalGold}));
    addLog(`💰 Sold junk for ${totalGold} gold.`);
  };

  // --- ИГРОВОЙ ТИК (СЕРДЦЕБИЕНИЕ) ---
  useEffect(() => {
    let timer;
    if (location === 'FIGHT' && isAuto) {
      timer = setInterval(() => {
        
        // 1. Если моба нет или он мертв - ищем нового
        if (!target || target.hp <= 0) {
          spawnMob();
          return;
        }

        // 2. Удар Игрока -> Моб
        const dmg = Math.floor(player.atk * (0.8 + Math.random() * 0.4)); // Разброс урона
        const newMobHp = target.hp - dmg;
        
        // 3. Проверка смерти Моба
        if (newMobHp <= 0) {
            setTarget(null);
            setPlayer(p => {
                const newXp = p.xp + target.xp;
                // Левел ап?
                if (newXp >= p.maxXp) {
                    addLog(`🎉 LEVEL UP! You are now level ${p.lvl + 1}`);
                    return { ...p, xp: 0, maxXp: Math.floor(p.maxXp * 1.5), lvl: p.lvl + 1, maxHp: p.maxHp + 20, hp: p.maxHp + 20, atk: p.atk + 2 };
                }
                return { ...p, xp: newXp };
            });
            addLog(`💀 ${target.name} died. +${target.xp} XP.`);
            lootItem(target.loot, target.chance);
        } else {
            // Моб жив, обновляем его HP
            setTarget(prev => ({ ...prev, hp: newMobHp }));
            
            // 4. Удар Моба -> Игрок
            const mobDmg = Math.floor(target.atk * (0.5 + Math.random() * 0.5));
            setPlayer(p => {
                const newHp = p.hp - mobDmg;
                if (newHp <= 0) {
                    setIsAuto(false);
                    setLocation('CITY');
                    setTarget(null);
                    addLog(`☠️ YOU DIED. Teleported to City.`);
                    return { ...p, hp: 1 };
                }
                return { ...p, hp: newHp };
            });
        }

      }, 800); // Скорость тика (800мс)
    }
    return () => clearInterval(timer);
  }, [location, isAuto, target, player]);

  // Автоскролл лога
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);


  // --- ОТРИСОВКА (UI) ---
  return (
    <div style={styles.app}>
      
      {/* ЛЕВАЯ ПАНЕЛЬ: ГЕРОЙ */}
      <div style={{...styles.col, ...styles.left}}>
        <h2 style={{color: '#ffb74d', margin: 0}}>Hawkar</h2>
        <div style={{fontSize: '14px', color: '#888'}}>Lvl {player.lvl} Orc Destroyer</div>
        
        <div style={{marginTop: 20}}>
            <div>HP {player.hp} / {player.maxHp}</div>
            <div style={styles.barBox}><div style={styles.barFill(player.hp/player.maxHp*100, '#d32f2f')}></div></div>
        </div>
        
        <div style={{marginTop: 10}}>
            <div>XP {player.xp} / {player.maxXp}</div>
            <div style={styles.barBox}><div style={styles.barFill(player.xp/player.maxXp*100, '#fbc02d')}></div></div>
        </div>

        <div style={{marginTop: 'auto', fontSize: '20px', color: '#ffd700'}}>
           {player.gold} 🪙
        </div>
      </div>

      {/* ЦЕНТРАЛЬНАЯ ПАНЕЛЬ: МИР */}
      <div style={{...styles.col, ...styles.center}}>
        <div style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
            
            {location === 'CITY' ? (
                <>
                    <h1 style={{color: '#90caf9'}}>Town of Dion</h1>
                    <p>Safe Zone. HP Regenerating...</p>
                    <button style={styles.btn(false)} onClick={() => {
                        if(player.hp < player.maxHp) { setPlayer(p => ({...p, hp: Math.min(p.maxHp, p.hp + 20)})); addLog("❤️ Rested."); }
                    }}>Heal (+20 HP)</button>
                    
                    <button style={styles.btn(false)} onClick={sellTrash}>Sell Junk</button>
                    
                    <div style={{height: 30}}></div>
                    <button style={{...styles.btn(true), background: '#d32f2f'}} onClick={() => setLocation('FIGHT')}>➔ Go Hunting</button>
                </>
            ) : (
                <>
                    <h2 style={{color: '#e57373'}}>Fields of Silence</h2>
                    
                    {target ? (
                        <div style={{width: '80%', textAlign: 'center', border: '1px solid #555', padding: 10, background: '#222'}}>
                            <div style={{fontSize: 40}}>🐺</div>
                            <h3>{target.name}</h3>
                            <div style={styles.barBox}><div style={styles.barFill(target.hp/target.maxHp*100, '#d32f2f')}></div></div>
                            <div>HP: {target.hp}/{target.maxHp}</div>
                        </div>
                    ) : (
                        <div>Looking for target...</div>
                    )}

                    <div style={{marginTop: 30, width: '60%'}}>
                        <button style={styles.btn(isAuto)} onClick={() => setIsAuto(!isAuto)}>
                            {isAuto ? "⏹ STOP AUTO" : "▶ START AUTO"}
                        </button>
                        <button style={styles.btn(false)} onClick={() => {
                            setIsAuto(false);
                            setLocation('CITY');
                            setTarget(null);
                        }}>🏃‍♂️ To Village</button>
                    </div>
                </>
            )}

        </div>

        {/* CHAT LOG */}
        <div style={styles.log}>
            {logs.map((line, i) => <div key={i} style={{marginBottom: 2, color: line.includes('died') ? '#ef5350' : line.includes('found') ? '#66bb6a' : '#ccc'}}>{line}</div>)}
            <div ref={logEndRef} />
        </div>
      </div>

      {/* ПРАВАЯ ПАНЕЛЬ: ИНВЕНТАРЬ */}
      <div style={{...styles.col, ...styles.right}}>
        <h3>Inventory ({inventory.length})</h3>
        <div style={styles.grid}>
            {inventory.map((itemId, idx) => (
                <div key={idx} style={styles.slot} title={ITEMS_DB[itemId].name}>
                    {ITEMS_DB[itemId].icon}
                </div>
            ))}
            {/* Пустые слоты для красоты */}
            {[...Array(Math.max(0, 25 - inventory.length))].map((_, i) => (
                <div key={i + 999} style={{...styles.slot, opacity: 0.3}}></div>
            ))}
        </div>
      </div>

    </div>
  );
}
