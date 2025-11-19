import React, { useState, useEffect, useRef, useCallback } from 'react';
import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  signInWithCustomToken, 
  signInAnonymously,
  onAuthStateChanged, 
  signOut
} from 'firebase/auth';
import { 
  getFirestore, 
  doc, 
  setDoc, 
  getDoc 
} from 'firebase/firestore';
import { 
  Shield, Zap, Sword, LogOut, X, Crosshair, ShoppingBag, Skull, Users, AlertCircle, Loader, Sparkles 
} from 'lucide-react';

// --- FIREBASE CONFIG ---
const firebaseConfig = JSON.parse(__firebase_config);
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

// --- GAME CONFIG ---
const Config = {
    CLASSES: {
        fighter: { 
            name: 'Tank', type: 'melee', range: 60, 
            base: { pAtk: 30, pDef: 30, atkSpd: 1.1, runSpd: 150 }, 
            hp: 500, mp: 60, color: 0x3b82f6 
        },
        mage: { 
            name: 'Mage', type: 'magic', range: 320, 
            base: { pAtk: 25, pDef: 10, atkSpd: 1.0, runSpd: 140 }, 
            hp: 150, mp: 500, cost: 5, color: 0x9333ea 
        },
        archer: { 
            name: 'Archer', type: 'range', range: 260, 
            base: { pAtk: 40, pDef: 15, atkSpd: 1.2, runSpd: 170 }, 
            hp: 220, mp: 100, color: 0x16a34a 
        }
    },
    BUFFS: {
        might: { name: 'Might', icon: '💪', stat: 'pAtk', val: 0.15, color: '#ef4444' },
        shield: { name: 'Shield', icon: '🛡️', stat: 'pDef', val: 0.15, color: '#3b82f6' },
        haste: { name: 'Haste', icon: '⚡', stat: 'atkSpd', val: 0.15, color: '#eab308' },
        ww: { name: 'Wind Walk', icon: '🦶', stat: 'runSpd', val: 0.15, color: '#22c55e' }
    },
    ITEMS: {
        'ssd': { name: 'Soulshot: D', icon: '⚡', type: 'etc', stack: true, price: 5 },
        'potion': { name: 'HP Potion', icon: '🍷', type: 'use', effect: {hp:150}, stack: true, price: 30 },
        'sword_d': { name: 'Revolution Sword', icon: '⚔️', type: 'gear', slot: 'weapon', pAtk: 60, price: 0 },
        'bow_d': { name: 'Gastraphetes', icon: '🏹', type: 'gear', slot: 'weapon', pAtk: 75, price: 0 },
        'staff_d': { name: 'Staff of Life', icon: '🪄', type: 'gear', slot: 'weapon', pAtk: 55, price: 0 },
        'armor_d': { name: 'Brigandine', icon: '🛡️', type: 'gear', slot: 'armor', pDef: 50, price: 0 },
        'qa_ring': { name: 'Ring of Queen Ant', icon: '💍', type: 'gear', slot: 'acc', pAtk: 30, pDef: 20, grade: 's', price: 0 },
        'adena': { name: 'Adena', icon: '💰', type: 'etc', stack: true }
    },
    MOBS: {
        'gremlin': { name: 'Gremlin', lvl: 1, hp: 50, exp: 15, pAtk: 10, atkSpd: 0.8, adena: [5,10], drop: ['ssd'], color: 0x60a5fa, scale: 0.8 },
        'wolf': { name: 'Wolf', lvl: 3, hp: 120, exp: 35, pAtk: 25, atkSpd: 1.0, adena: [15,30], drop: ['potion'], color: 0x9ca3af, scale: 1.1 },
        'orc': { name: 'Orc', lvl: 5, hp: 250, exp: 70, pAtk: 45, atkSpd: 0.6, adena: [40,80], drop: ['armor_d'], color: 0x166534, scale: 1.3 }
    },
    BOSSES: {
        'qa': { name: 'Queen Ant', lvl: 10, hp: 5000, exp: 5000, pAtk: 150, atkSpd: 1.2, adena: [1000, 5000], drop: ['qa_ring'], color: 0xb91c1c, scale: 3.0 }
    },
    WORLD: {
        SAFE_ZONE_RADIUS: 550
    }
};

// --- REACT COMPONENT ---
export default function PocketL2() {
    const [user, setUser] = useState(null);
    const [authMode, setAuthMode] = useState('loading'); 
    const [charName, setCharName] = useState('');
    const [selectedClass, setSelectedClass] = useState('fighter');
    const [error, setError] = useState(''); 
    
    const [modal, setModal] = useState(null);
    const [npcDialog, setNpcDialog] = useState(null);
    const [bossInfo, setBossInfo] = useState(null);
    const [, updateState] = useState();
    const forceUpdate = useCallback(() => updateState({}), []);
    
    // GAME LOGIC REF
    const gameLogic = useRef({
        player: {
            name: 'Guest', class: 'fighter',
            lvl: 1, exp: 0, maxExp: 100,
            hp: 140, maxHp: 140, mp: 50, maxMp: 50,
            stats: { pAtk: 0, pDef: 0, atkSpd: 0, runSpd: 0 },
            inv: {}, equip: { weapon: null, armor: null, acc: null },
            buffs: {}, 
            auto: false, ss: false, targetId: null, isDead: false,
            party: false
        },
        zoneSafe: true,
        chat: [],
        recalc: function() {
            const c = Config.CLASSES[this.player.class];
            let pAtk = c.base.pAtk + (this.player.lvl * 3);
            let pDef = c.base.pDef + (this.player.lvl * 1.5);
            let atkSpd = c.base.atkSpd;
            let runSpd = c.base.runSpd;
            let maxHp = c.hp + (this.player.lvl * 50);
            let maxMp = c.mp + (this.player.lvl * 20);

            if (this.player.equip.weapon) pAtk += Config.ITEMS[this.player.equip.weapon].pAtk;
            if (this.player.equip.armor) pDef += Config.ITEMS[this.player.equip.armor].pDef;
            if (this.player.equip.acc) {
                pAtk += Config.ITEMS[this.player.equip.acc].pAtk || 0;
                pDef += Config.ITEMS[this.player.equip.acc].pDef || 0;
            }

            const now = Date.now();
            let modPAtk = 1, modPDef = 1, modAtkSpd = 1, modRunSpd = 1;
            
            const activeBuffs = {};
            Object.entries(this.player.buffs || {}).forEach(([k, t]) => {
                if(t > now) {
                    activeBuffs[k] = t;
                    const bConf = Config.BUFFS[k];
                    if(bConf.stat === 'pAtk') modPAtk += bConf.val;
                    if(bConf.stat === 'pDef') modPDef += bConf.val;
                    if(bConf.stat === 'atkSpd') modAtkSpd += bConf.val;
                    if(bConf.stat === 'runSpd') modRunSpd += bConf.val;
                }
            });
            this.player.buffs = activeBuffs;

            this.player.stats = { 
                pAtk: Math.floor(pAtk * modPAtk), 
                pDef: Math.floor(pDef * modPDef), 
                atkSpd: atkSpd * modAtkSpd,
                runSpd: runSpd * modRunSpd
            };
            this.player.maxHp = maxHp;
            this.player.maxMp = maxMp;
            this.player.maxExp = this.player.lvl * 100;
        },
        addBuff: function(id) {
            this.player.buffs[id] = Date.now() + 120000; 
            this.recalc();
            forceUpdate();
        },
        addItem: function(id, qty=1) {
             if (Config.ITEMS[id].stack) {
                this.player.inv[id] = (this.player.inv[id] || 0) + qty;
             } else {
                const uid = Date.now() + Math.random();
                this.player.inv[uid] = { id, qty: 1 };
             }
        },
        useItem: function(key) {
            const item = Config.ITEMS[key];
            if(item && item.type === 'use' && this.player.inv[key] > 0) {
                if(item.effect.hp) this.player.hp = Math.min(this.player.maxHp, this.player.hp + item.effect.hp);
                this.player.inv[key]--;
                forceUpdate();
            }
        },
        buyItem: function(id, price) {
             const adena = this.player.inv['adena'] || 0;
             if(adena >= price) {
                 this.player.inv['adena'] -= price;
                 this.addItem(id, 1);
                 forceUpdate();
                 return true;
             }
             return false;
        },
        equip: function(key) {
            const itemDef = Config.ITEMS[key] ? Config.ITEMS[key] : Config.ITEMS[this.player.inv[key].id];
            const slot = itemDef.slot;
            if (this.player.equip[slot]) this.unequip(slot);
            this.player.equip[slot] = Config.ITEMS[key] ? key : this.player.inv[key].id;
            this.recalc();
        },
        unequip: function(slot) {
            if (!this.player.equip[slot]) return;
            this.player.equip[slot] = null;
            this.recalc();
        },
        takeDamage: function(amount) {
            const dmg = Math.max(1, amount - (this.player.stats.pDef * 0.5));
            this.player.hp = Math.max(0, Math.floor(this.player.hp - dmg));
            
            if(this.player.hp <= 0 && !this.player.isDead) {
                this.player.isDead = true;
                this.player.auto = false;
                this.player.targetId = null;
                this.player.exp = Math.floor(this.player.exp * 0.9);
                if(this.chat) this.chat.push({msg: 'YOU DIED! To village.', type: 'dmg'});
                
                setTimeout(() => {
                    this.player.hp = Math.floor(this.player.maxHp * 0.5);
                    this.player.isDead = false;
                    if(window.gameInstance?.scene?.keys?.MainScene) {
                         window.gameInstance.scene.keys.MainScene.respawnPlayer();
                    }
                }, 3000);
            }
            forceUpdate();
        }
    });

    // --- AUTH & INIT ---
    useEffect(() => {
        const initAuth = async () => {
            try {
                if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) {
                    await signInWithCustomToken(auth, __initial_auth_token);
                } else {
                    await signInAnonymously(auth);
                }
            } catch (e) {
                console.error("Auth Init Error", e);
                setError("Auth Error: " + e.message);
            }
        };
        initAuth();

        return onAuthStateChanged(auth, async (u) => {
            setUser(u);
            if(u) {
                 try {
                     const snap = await getDoc(doc(db, 'artifacts', appId, 'users', u.uid, 'data', 'char'));
                     if(snap.exists()) {
                         const d = snap.data();
                         gameLogic.current.player = { ...gameLogic.current.player, ...d };
                         gameLogic.current.recalc();
                         setAuthMode('game');
                     } else {
                         setAuthMode('create');
                     }
                 } catch (e) {
                     console.error("DB Load Error", e);
                     setAuthMode('create'); 
                 }
            }
        });
    }, []);

    // --- ACTIONS ---
    const handleCreateChar = async () => {
        if(!charName) return setError('Enter name!');
        setError('');
        
        const p = gameLogic.current.player;
        p.name = charName;
        p.class = selectedClass;
        p.hp = Config.CLASSES[selectedClass].hp;
        p.maxHp = p.hp;
        p.mp = Config.CLASSES[selectedClass].mp;
        p.maxMp = p.mp;
        
        gameLogic.current.addItem('ssd', 500);
        gameLogic.current.addItem('potion', 10);
        if(selectedClass === 'mage') gameLogic.current.addItem('staff_d');
        else if(selectedClass === 'archer') gameLogic.current.addItem('bow_d');
        else gameLogic.current.addItem('sword_d');
        
        gameLogic.current.recalc();

        if(auth.currentUser) {
            try {
                await setDoc(doc(db, 'artifacts', appId, 'users', auth.currentUser.uid, 'data', 'char'), p);
                setAuthMode('game');
            } catch(e) {
                setError("Save Error: " + e.message);
            }
        }
    };

    // Load Phaser
    useEffect(() => {
        if (authMode === 'game') {
            const loadPhaser = () => {
                if(window.Phaser) initGame();
                else {
                    const script = document.createElement('script');
                    script.src = 'https://cdn.jsdelivr.net/npm/phaser@3.80.1/dist/phaser.min.js';
                    script.onload = initGame;
                    document.body.appendChild(script);
                }
            };
            loadPhaser();
        }
    }, [authMode]);

    const initGame = () => {
        if(window.gameInstance) return;

        class MainScene extends window.Phaser.Scene {
            constructor() { super('MainScene'); }

            preload() {
                const g = this.make.graphics();
                // Environment
                g.clear(); g.fillStyle(0x52525b); g.fillRect(0,0,64,64); 
                g.fillStyle(0x71717a); g.fillRect(2,2,28,28); g.fillRect(34,34,28,28);
                g.generateTexture('tile_town', 64, 64);

                g.clear(); g.fillStyle(0x18181b); g.fillRect(0,0,64,64);
                g.fillStyle(0x27272a); g.fillRect(10,10,4,4); g.fillRect(50,40,6,6);
                g.generateTexture('tile_field', 64, 64);

                g.clear(); g.fillStyle(0x404040); g.fillRect(0,0,32,32);
                g.lineStyle(2, 0x171717); g.strokeRect(0,0,32,32);
                g.generateTexture('wall', 32, 32);

                // Characters
                const drawChar = (key, color, weaponType) => {
                    g.clear();
                    g.fillStyle(0x000000, 0.4); g.fillEllipse(16, 28, 20, 8);
                    g.fillStyle(color); g.fillRect(10, 8, 12, 16);
                    g.fillStyle(0xfca5a5); g.fillRect(10, 4, 12, 6);
                    g.fillStyle(0xcccccc);
                    if(weaponType === 'sword') { 
                         g.fillRect(22, 12, 4, 14); g.fillStyle(0x444444); g.fillRect(6, 12, 4, 10);
                    } else if (weaponType === 'staff') {
                         g.fillStyle(0x8b5cf6); g.fillRect(24, 6, 2, 20); g.fillStyle(0xfef08a); g.fillCircle(25, 6, 3);
                    } else if (weaponType === 'bow') {
                         g.lineStyle(2, 0x854d0e); g.beginPath(); g.arc(20, 16, 8, -Math.PI/2, Math.PI/2); g.stroke();
                    }
                    g.generateTexture(key, 32, 32);
                };
                drawChar('char_fighter', 0x2563eb, 'sword');
                drawChar('char_mage', 0x9333ea, 'staff');
                drawChar('char_archer', 0x16a34a, 'bow');
                drawChar('char_healer', 0xffffff, 'staff'); 

                // Mobs
                const drawMob = (key, color) => {
                    g.clear();
                    g.fillStyle(0x000000, 0.4); g.fillEllipse(16, 28, 20, 8); // Shadow
                    g.fillStyle(color); 
                    // Simple shape fallback for logic
                    g.fillRect(8,8,16,16); 
                    g.generateTexture(key, 32, 32);
                };

                // --- MOB DRAWINGS ---
                // Gremlin
                g.clear(); g.fillStyle(0x000000, 0.4); g.fillEllipse(16, 28, 20, 8);
                g.fillStyle(0x60a5fa); g.fillRect(10, 14, 12, 12); g.fillRect(8, 10, 16, 4); 
                g.fillStyle(0x3b82f6); g.beginPath(); g.moveTo(8, 10); g.lineTo(4, 4); g.lineTo(12, 10); g.fill(); g.beginPath(); g.moveTo(24, 10); g.lineTo(28, 4); g.lineTo(20, 10); g.fill();
                g.fillStyle(0xef4444); g.fillCircle(14, 16, 1); g.fillCircle(18, 16, 1);
                g.generateTexture('mob_gremlin', 32, 32);

                // Wolf
                g.clear(); g.fillStyle(0x000000, 0.4); g.fillEllipse(16, 28, 24, 8);
                g.fillStyle(0x9ca3af); g.fillRect(6, 16, 18, 10); g.fillRect(24, 12, 6, 6); g.fillRect(10, 26, 4, 4); g.fillRect(18, 26, 4, 4);
                g.fillStyle(0x404040); g.fillRect(26, 18, 2, 2); g.fillStyle(0x9ca3af); g.beginPath(); g.moveTo(6, 18); g.lineTo(2, 14); g.lineTo(4, 20); g.fill();
                g.generateTexture('mob_wolf', 32, 32);

                // Orc
                g.clear(); g.fillStyle(0x000000, 0.4); g.fillEllipse(16, 28, 28, 10);
                g.fillStyle(0x166534); g.fillRect(8, 8, 16, 18); g.fillRect(6, 10, 4, 10); g.fillRect(22, 10, 4, 10);
                g.fillStyle(0x525252); g.fillRect(8, 8, 16, 4); g.fillRect(8, 16, 16, 4);
                g.fillStyle(0x166534); g.fillRect(10, 4, 12, 6); g.fillStyle(0xffffff); g.beginPath(); g.moveTo(10, 8); g.lineTo(8, 6); g.lineTo(10, 4); g.fill(); g.beginPath(); g.moveTo(22, 8); g.lineTo(24, 6); g.lineTo(22, 4); g.fill();
                g.generateTexture('mob_orc', 32, 32);

                // BOSS
                g.clear(); g.fillStyle(0x000000, 0.5); g.fillEllipse(32, 56, 48, 16); 
                g.fillStyle(0xb91c1c); g.fillCircle(32, 40, 14); g.fillCircle(12, 40, 12); g.fillCircle(52, 36, 8); 
                g.lineStyle(3, 0xb91c1c); g.beginPath(); g.moveTo(32, 40); g.lineTo(10, 60); g.stroke(); g.beginPath(); g.moveTo(32, 40); g.lineTo(54, 60); g.stroke();
                g.fillStyle(0xfacc15); g.fillCircle(46, 30, 2); g.fillCircle(50, 30, 2);
                g.generateTexture('mob_qa', 64, 64);

                // Misc
                g.clear(); g.fillStyle(0x854d0e); g.fillRect(8, 8, 16, 12); g.fillStyle(0xa16207); g.fillRect(10, 4, 12, 4); g.lineStyle(2, 0xfacc15); g.strokeRect(8, 8, 16, 12); g.generateTexture('drop_bag', 32, 32);
                g.clear(); g.fillStyle(0x000000, 0.4); g.fillEllipse(16, 28, 20, 8); g.fillStyle(0xffffff); g.fillRect(8, 6, 16, 22); g.fillStyle(0xfca5a5); g.fillRect(10, 2, 12, 6); g.generateTexture('npc_base', 32, 32);
                
                g.clear(); g.fillStyle(0xef4444); g.fillRect(0,0,8,8); g.generateTexture('fx_hit', 8, 8);
                g.clear(); g.fillStyle(0x3b82f6); g.fillCircle(4,4,4); g.generateTexture('fx_magic', 8, 8);
                g.clear(); g.fillStyle(0xffffff); g.fillRect(0,0,12,2); g.generateTexture('fx_arrow', 12, 2);
                
                // Heal FX
                g.clear(); g.fillStyle(0x4ade80); g.fillCircle(4,4,4); g.generateTexture('fx_heal', 8, 8); 
                
                // Buff FX (Golden Aura)
                g.clear(); g.lineStyle(2, 0xfacc15); g.beginPath(); g.arc(16, 16, 14, 0, Math.PI*2); g.stroke();
                g.fillStyle(0xfacc15); g.fillCircle(16, 4, 2); g.fillCircle(16, 28, 2); g.fillCircle(4, 16, 2); g.fillCircle(28, 16, 2);
                g.generateTexture('fx_buff', 32, 32);
            }

            create() {
                this.physics.world.setBounds(0, 0, 3000, 3000);
                this.add.tileSprite(1500, 1500, 3000, 3000, 'tile_field');
                const r = Config.WORLD.SAFE_ZONE_RADIUS;
                this.add.tileSprite(1500, 1500, r*2, r*2, 'tile_town');
                
                const walls = this.physics.add.staticGroup();
                for(let i = -r; i <= r; i+=32) {
                    if(Math.abs(i) > 120) {
                        walls.create(1500+i, 1500-r, 'wall');
                        walls.create(1500+i, 1500+r, 'wall');
                        walls.create(1500-r, 1500+i, 'wall');
                        walls.create(1500+r, 1500+i, 'wall');
                    }
                }

                const pClass = this.game.reactLogic.current.player.class;
                this.player = this.physics.add.sprite(1500, 1500, `char_${pClass}`);
                this.player.setCollideWorldBounds(true);
                this.player.setScale(1.5);
                this.player.setDepth(100);
                this.cameras.main.startFollow(this.player, true, 0.1, 0.1);
                this.physics.add.collider(this.player, walls);

                this.mobs = this.physics.add.group();
                this.npcs = this.physics.add.staticGroup();
                this.drops = this.physics.add.group();
                this.partyMember = null; 
                this.partyLabel = null;

                this.spawnNPC(1500, 1400, 'Trader Wood', 0xf59e0b, 'shop');
                this.spawnNPC(1600, 1500, 'GK Clarissa', 0xd946ef, 'teleport');
                this.spawnNPC(1400, 1500, 'Warehouse', 0x3b82f6, 'bank');
                
                this.spawnBoss();

                this.input.on('pointerdown', (p) => {
                    const logic = this.game.reactLogic.current;
                    if (logic.player.isDead) return;
                    const worldPoint = this.cameras.main.getWorldPoint(p.x, p.y);
                    const clicked = this.physics.overlapRect(worldPoint.x-10, worldPoint.y-10, 20, 20);
                    let targetFound = null;
                    if(clicked.length > 0) {
                        clicked.forEach(body => {
                            if(body.gameObject.getData('type') === 'npc') targetFound = body.gameObject;
                            else if (body.gameObject.getData('type') === 'mob') {
                                logic.player.targetId = body.gameObject.getData('id');
                                this.game.triggerUpdate();
                            } else if (body.gameObject.getData('type') === 'drop') {
                                targetFound = body.gameObject; 
                            }
                        });
                    }
                    if (targetFound) {
                        const dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, targetFound.x, targetFound.y);
                        if(dist < 100) {
                             if(targetFound.getData('type') === 'drop') this.pickupDrop(targetFound);
                             else if (targetFound.getData('type') === 'npc') this.game.openNpc(targetFound.getData('name'), targetFound.getData('role'));
                             this.player.body.stop();
                             this.targetPos = null;
                        } else {
                             this.moveTo(targetFound.x, targetFound.y);
                             this.interactTarget = targetFound;
                        }
                    } else if (!logic.player.auto) {
                        this.moveTo(worldPoint.x, worldPoint.y);
                        this.interactTarget = null;
                    }
                });

                for(let i=0; i<25; i++) this.spawnMob();
                this.time.addEvent({ delay: 3000, callback: this.spawnMob, callbackScope: this, loop: true });

                // REGEN & PARTY LOGIC LOOP (1s)
                this.time.addEvent({
                    delay: 1000, 
                    callback: () => {
                        const logic = this.game.reactLogic.current;
                        if(logic.player.isDead) return;
                        
                        const p = logic.player;
                        const isSafe = logic.zoneSafe;
                        let hpRegen = isSafe ? 20 : 2;
                        let mpRegen = isSafe ? 20 : 2;
                        if (!isSafe && p.class === 'mage') mpRegen += 5;
                        if (p.hp < p.maxHp) p.hp = Math.min(p.maxHp, p.hp + hpRegen);
                        if (p.mp < p.maxMp) p.mp = Math.min(p.maxMp, p.mp + mpRegen);
                        
                        // RECALC
                        logic.recalc();

                        // PARTY
                        if (logic.player.party && !this.partyMember) {
                            this.partyMember = this.physics.add.sprite(this.player.x, this.player.y, 'char_healer').setScale(1.5);
                            this.partyLabel = this.add.text(0, 0, 'Healer', { fontSize: '10px', color: '#86efac', stroke: '#000', strokeThickness: 2 }).setOrigin(0.5);
                        } 
                        else if (logic.player.party && this.partyMember) {
                            if (p.hp < p.maxHp * 0.7) {
                                const fx = this.add.sprite(this.player.x, this.player.y, 'fx_heal').setScale(2);
                                this.tweens.add({ targets: fx, y: this.player.y - 20, alpha: 0, duration: 500, onComplete: ()=>fx.destroy() });
                                p.hp = Math.min(p.maxHp, p.hp + 150); 
                            }
                            else {
                                const now = Date.now();
                                const buffsToCast = ['might', 'shield', 'haste', 'ww'];
                                for (const b of buffsToCast) {
                                    if (!p.buffs[b] || p.buffs[b] < now + 5000) {
                                        logic.addBuff(b);
                                        const fx = this.add.sprite(this.player.x, this.player.y, 'fx_buff');
                                        this.tweens.add({ targets: fx, scale: 2, alpha: 0, angle: 180, duration: 800, onComplete: ()=>fx.destroy() });
                                        break; 
                                    }
                                }
                            }
                            if (Phaser.Math.Distance.Between(this.partyMember.x, this.partyMember.y, this.player.x, this.player.y) > 60) {
                                this.physics.moveToObject(this.partyMember, this.player, 160);
                            } else {
                                this.partyMember.body.stop();
                            }
                        } 
                        else if (!logic.player.party && this.partyMember) {
                            this.partyMember.destroy();
                            this.partyLabel.destroy();
                            this.partyMember = null;
                            this.partyLabel = null;
                        }
                        
                        this.game.triggerUpdate();
                    },
                    loop: true
                });
            }

            respawnPlayer() {
                this.player.setPosition(1500, 1500);
                this.player.body.stop();
                this.targetPos = null;
                this.interactTarget = null;
                this.game.triggerUpdate();
            }

            spawnNPC(x, y, name, color, role) {
                const npc = this.npcs.create(x, y, 'npc_base').setScale(1.5).setTint(color);
                npc.setData('type', 'npc');
                npc.setData('name', name);
                npc.setData('role', role);
                this.add.text(x, y-35, name, { fontSize: '10px', fontFamily: 'monospace', color: '#86efac', backgroundColor: '#00000080' }).setOrigin(0.5);
            }

            spawnBoss() {
                const data = Config.BOSSES['qa'];
                const boss = this.mobs.create(2500, 2500, 'mob_qa').setScale(data.scale);
                boss.setData('type', 'mob');
                boss.setData('id', 'boss_qa');
                boss.setData('stats', {...data, curHp: data.hp, isBoss: true});
                boss.setData('aggro', false);
                const label = this.add.text(2500, 2450, `☠️ ${data.name} ☠️`, { fontSize:'14px', color:'#ef4444', fontStyle: 'bold', stroke: '#000', strokeThickness: 4 }).setOrigin(0.5);
                boss.setData('label', label);
            }

            moveTo(x, y) {
                if (this.game.reactLogic.current.player.isDead) return;
                this.physics.moveTo(this.player, x, y, 200);
                this.targetPos = new Phaser.Math.Vector2(x, y);
            }

            update() {
                const logic = this.game.reactLogic.current;
                if (logic.player.isDead) return;
                
                if (this.partyMember && this.partyLabel) {
                    this.partyLabel.x = this.partyMember.x;
                    this.partyLabel.y = this.partyMember.y - 35;
                    this.partyLabel.setDepth(this.partyMember.y + 100);
                    this.partyMember.setDepth(this.partyMember.y);
                }
                
                if(this.targetPos) {
                    if(Phaser.Math.Distance.Between(this.player.x, this.player.y, this.targetPos.x, this.targetPos.y) < 10) {
                        this.player.body.stop();
                        this.targetPos = null;
                        if(this.interactTarget) {
                            if(this.interactTarget.active) {
                                if(this.interactTarget.getData('type') === 'drop') this.pickupDrop(this.interactTarget);
                                else if (this.interactTarget.getData('type') === 'npc') this.game.openNpc(this.interactTarget.getData('name'), this.interactTarget.getData('role'));
                            }
                            this.interactTarget = null;
                        }
                    }
                }

                const distCenter = Phaser.Math.Distance.Between(this.player.x, this.player.y, 1500, 1500);
                const isSafe = distCenter < Config.WORLD.SAFE_ZONE_RADIUS;
                if (logic.zoneSafe !== isSafe) {
                    logic.zoneSafe = isSafe;
                    this.game.triggerUpdate();
                }

                if (logic.player.auto && !isSafe) {
                    this.doAutoHunt(logic);
                }

                if (logic.player.targetId) {
                    const target = this.mobs.children.getArray().find(m => m.getData('id') === logic.player.targetId);
                    if (target && target.active && target.getData('stats').isBoss) {
                        this.game.updateBossUi(target.getData('stats'));
                    } else {
                        this.game.updateBossUi(null);
                    }
                } else {
                    this.game.updateBossUi(null);
                }

                this.mobs.children.iterate(m => {
                    if(m.active) {
                        m.setDepth(m.y);
                        const label = m.getData('label');
                        if(label) { label.x = m.x; label.y = m.y - (30 * m.scale); }

                        const mobStats = m.getData('stats');
                        if (m.getData('aggro')) {
                            const dist = Phaser.Math.Distance.Between(m.x, m.y, this.player.x, this.player.y);
                            const atkRange = mobStats.isBoss ? 80 : 40;
                            if (dist > atkRange) {
                                this.physics.moveToObject(m, this.player, mobStats.isBoss ? 160 : 120);
                            } else {
                                m.body.stop();
                                if (!m.getData('attackCD') || this.time.now > m.getData('attackCD')) {
                                    m.setData('attackCD', this.time.now + (1000/mobStats.atkSpd));
                                    this.tweens.add({ targets: m, x: this.player.x, y: this.player.y, duration: 100, yoyo: true });
                                    logic.takeDamage(mobStats.pAtk);
                                    this.showDmg(this.player.x, this.player.y, mobStats.pAtk, false, '#ef4444');
                                }
                            }
                        }
                    }
                });

                this.player.setDepth(this.player.y);
            }

            spawnMob() {
                if (this.mobs.countActive() >= 35) return;
                let x, y;
                do {
                    x = Phaser.Math.Between(200, 2800);
                    y = Phaser.Math.Between(200, 2800);
                } while (Phaser.Math.Distance.Between(x, y, 1500, 1500) < Config.WORLD.SAFE_ZONE_RADIUS + 100);

                const types = Object.keys(Config.MOBS);
                const tKey = types[Math.floor(Math.random()*types.length)];
                const data = Config.MOBS[tKey];
                const mob = this.mobs.create(x, y, `mob_${tKey}`).setScale(data.scale);
                mob.setData('type', 'mob');
                mob.setData('id', Date.now() + Math.random());
                mob.setData('stats', {...data, curHp: data.hp});
                mob.setData('aggro', false);
                const label = this.add.text(x, y-30, `${data.name}`, { fontSize:'10px', color:'#f87171' }).setOrigin(0.5);
                mob.setData('label', label);
            }

            spawnDrop(x, y, itemId) {
                const drop = this.drops.create(x, y, 'drop_bag').setScale(0.8);
                drop.setData('type', 'drop');
                drop.setData('itemId', itemId);
                drop.setData('dropTime', this.time.now);
                this.tweens.add({ targets: drop, y: y-10, duration: 500, yoyo: true, repeat: -1 });
                this.time.delayedCall(60000, () => { if(drop.active) drop.destroy(); });
            }

            pickupDrop(drop) {
                const logic = this.game.reactLogic.current;
                const itemId = drop.getData('itemId');
                logic.addItem(itemId, 1);
                this.game.log(`Picked up: ${Config.ITEMS[itemId].name}`, 'gain');
                drop.destroy();
            }

            doAutoHunt(logic) {
                let loot = this.physics.closest(this.player, this.drops.getChildren());
                if (loot && Phaser.Math.Distance.Between(this.player.x, this.player.y, loot.x, loot.y) < 300) {
                     if (Phaser.Math.Distance.Between(this.player.x, this.player.y, loot.x, loot.y) > 20) {
                         this.physics.moveToObject(this.player, loot, 200);
                     } else {
                         this.pickupDrop(loot);
                     }
                     return;
                }

                let target = this.currentTarget;
                if (logic.player.targetId) {
                    const t = this.mobs.children.getArray().find(m => m.getData('id') === logic.player.targetId);
                    if(t && t.active) target = t;
                }

                if (!target || !target.active) {
                    target = this.physics.closest(this.player, this.mobs.getChildren());
                    this.currentTarget = target;
                }
                
                if (target) {
                    const dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, target.x, target.y);
                    const cls = Config.CLASSES[logic.player.class];
                    if (dist > cls.range) {
                        this.physics.moveToObject(this.player, target, 180);
                    } else {
                        this.player.body.stop();
                        this.attack(target, logic, cls);
                    }
                }
            }

            attack(target, logic, cls) {
                if (this.isAttacking) return;
                if (cls.type === 'magic' && logic.player.mp < cls.cost) return;

                this.isAttacking = true;
                if (cls.type === 'melee') {
                    this.tweens.add({ targets: this.player, x: target.x, y: target.y, duration: 100, yoyo: true });
                } else {
                    const proj = this.add.sprite(this.player.x, this.player.y, cls.type === 'magic' ? 'fx_magic' : 'fx_arrow');
                    this.tweens.add({ targets: proj, x: target.x, y: target.y, duration: 300, onComplete: () => proj.destroy() });
                }

                setTimeout(() => {
                    this.dealDamage(target, logic, cls);
                    this.isAttacking = false;
                }, cls.type === 'melee' ? 200 : 300);
            }

            dealDamage(target, logic, cls) {
                if (!target.active) return;
                target.setData('aggro', true);

                if (cls.type === 'magic') {
                    logic.player.mp -= cls.cost;
                    this.game.triggerUpdate();
                }

                let dmg = logic.player.stats.pAtk + Phaser.Math.Between(0, 10);
                let crit = Math.random() < 0.15;
                if (crit) dmg *= 2;

                if (logic.player.ss && logic.player.inv['ssd'] > 0) {
                    dmg *= 2;
                    logic.player.inv['ssd']--;
                    const fx = this.add.sprite(target.x, target.y, 'fx_hit').setScale(3);
                    this.tweens.add({ targets: fx, alpha: 0, duration: 200, onComplete: ()=>fx.destroy() });
                    this.game.triggerUpdate();
                }

                const stats = target.getData('stats');
                stats.curHp -= dmg;
                this.showDmg(target.x, target.y, Math.floor(dmg), crit);

                if (stats.curHp <= 0) {
                    logic.player.exp += stats.exp;
                    const adena = Phaser.Math.Between(...stats.adena);
                    logic.addItem('adena', adena);
                    
                    if (Math.random() < 0.5) { 
                        this.spawnDrop(target.x, target.y, stats.drop[0]);
                    }
                    
                    if (logic.player.exp >= logic.player.maxExp) {
                        logic.player.lvl++;
                        logic.player.exp = 0;
                        logic.recalc();
                        logic.player.hp = logic.player.maxHp;
                    }
                    
                    this.game.save();
                    this.game.triggerUpdate();
                    if(target.getData('label')) target.getData('label').destroy();
                    target.destroy();
                    this.currentTarget = null;
                    if (logic.player.targetId === stats.id) logic.player.targetId = null;
                }
            }

            showDmg(x, y, dmg, crit, colorOverride) {
                const color = colorOverride ? colorOverride : (crit ? '#fbbf24' : '#ffffff');
                const size = crit ? '24px' : '14px';
                const txt = this.add.text(x, y-20, dmg, { fontSize: size, color: color, stroke: '#000', strokeThickness: 3 }).setOrigin(0.5);
                this.tweens.add({ targets: txt, y: y-60, alpha: 0, duration: 800, onComplete: ()=>txt.destroy() });
            }
        }

        const config = {
            type: window.Phaser.AUTO,
            parent: 'phaser-root',
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundColor: '#000',
            pixelArt: true,
            physics: { default: 'arcade', arcade: { debug: false } },
            scene: [MainScene]
        };
        window.gameInstance = new window.Phaser.Game(config);
        window.gameInstance.reactLogic = gameLogic;
        window.gameInstance.triggerUpdate = forceUpdate;
        // --- FIX: Added log function back ---
        window.gameInstance.log = (msg, type) => {
            gameLogic.current.chat.push({msg, type});
            if(gameLogic.current.chat.length > 6) gameLogic.current.chat.shift();
            forceUpdate();
        };
        window.gameInstance.updateBossUi = (info) => setBossInfo(info);
        window.gameInstance.save = async () => {
            if(auth.currentUser) {
                await setDoc(doc(db, 'artifacts', appId, 'users', auth.currentUser.uid, 'data', 'char'), gameLogic.current.player);
            }
        };
        window.gameInstance.openNpc = (name, type) => {
            setNpcDialog({name, type});
            forceUpdate();
        };
    };

    // --- RENDER ---
    if (authMode === 'loading') {
        return (
            <div className="flex items-center justify-center h-screen bg-[#0f172a] text-white font-mono">
                <Loader className="animate-spin" size={32}/>
            </div>
        );
    }

    if (authMode === 'create') {
        return (
            <div className="flex items-center justify-center h-screen bg-[#0f172a] text-white font-mono">
                <div className="w-96 p-8 bg-[#1e293b] border-2 border-[#334155] rounded shadow-2xl text-center">
                    <h1 className="text-3xl font-bold text-indigo-400 mb-2">POCKET L2</h1>
                    <p className="text-xs text-slate-500 mb-6 uppercase">Pixel Remaster</p>
                    
                    {error && <div className="bg-red-900/50 text-red-200 text-sm p-2 mb-4 border border-red-800 flex items-center gap-2"><AlertCircle size={16}/> {error}</div>}

                    <input className="w-full bg-[#0f172a] border p-3 mb-4 text-center outline-none" placeholder="Character Name" value={charName} onChange={e=>setCharName(e.target.value)}/>
                    <div className="flex gap-2 mb-6 justify-center">
                    {Object.entries(Config.CLASSES).map(([k, v]) => (
                        <div key={k} onClick={()=>setSelectedClass(k)} className={`p-2 border cursor-pointer w-24 ${selectedClass===k ? 'border-indigo-500 bg-[#312e81]' : 'border-[#334155]'}`}>
                            <div className="text-2xl mb-1">{k==='fighter'?'🛡️':k==='mage'?'🔮':'🏹'}</div>
                            <div className="text-[10px] font-bold uppercase">{v.name}</div>
                        </div>
                    ))}
                    </div>
                    <button onClick={handleCreateChar} className="w-full py-3 bg-green-600 font-bold">Start Journey</button>
                </div>
            </div>
        );
    }

    const p = gameLogic.current.player;

    return (
        <div className="relative w-screen h-screen bg-black overflow-hidden select-none font-sans text-white">
            <div id="phaser-root" className="absolute inset-0 z-0"></div>

            {p.isDead && (
                <div className="absolute inset-0 z-50 bg-red-900/40 flex items-center justify-center">
                    <div className="text-4xl font-bold text-red-500 animate-pulse flex flex-col items-center">
                        <Skull size={64}/>
                        <span>YOU DIED</span>
                        <span className="text-sm text-white mt-2">Respawning in town...</span>
                    </div>
                </div>
            )}

            {/* BOSS BAR */}
            {bossInfo && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 w-96 pointer-events-none z-20">
                     <div className="flex justify-between text-red-500 font-bold text-shadow mb-1">
                         <span>☠️ {bossInfo.name}</span>
                         <span>{Math.floor((bossInfo.curHp/bossInfo.maxHp)*100)}%</span>
                     </div>
                     <div className="h-6 bg-black border-2 border-red-900 rounded relative overflow-hidden">
                         <div className="h-full bg-gradient-to-r from-red-600 to-red-800 transition-all duration-200" style={{width:`${(bossInfo.curHp/bossInfo.maxHp)*100}%`}}/>
                     </div>
                </div>
            )}

            {/* HUD */}
            <div className="absolute top-4 left-4 pointer-events-auto bg-[#0f172a]/90 border border-[#334155] p-2 rounded w-64">
                 <div className="flex justify-between items-baseline mb-2">
                     <span className="font-bold text-indigo-300">{p.name}</span>
                     <span className="text-[10px] bg-slate-800 px-1 rounded text-slate-300">Lv.{p.lvl}</span>
                 </div>
                 
                 <div className="flex justify-between items-center mb-1">
                     <div className="text-[10px] font-bold text-red-400">HP</div>
                     <div className="flex-1 mx-2 h-3 bg-[#1e293b] border border-[#334155] relative">
                         <div className="h-full bg-red-600 transition-all" style={{width:`${(p.hp/p.maxHp)*100}%`}}/>
                     </div>
                     <div className="text-[10px]">{p.hp}</div>
                 </div>
                 <div className="flex justify-between items-center mb-2">
                     <div className="text-[10px] font-bold text-blue-400">MP</div>
                     <div className="flex-1 mx-2 h-3 bg-[#1e293b] border border-[#334155] relative">
                         <div className="h-full bg-blue-600 transition-all" style={{width:`${(p.mp/p.maxMp)*100}%`}}/>
                     </div>
                     <div className="text-[10px]">{p.mp}</div>
                 </div>

                 {/* BUFFS BAR */}
                 <div className="flex gap-1 mb-2 h-5">
                     {Object.keys(p.buffs || {}).map(k => (
                         <div key={k} className="w-5 h-5 bg-[#1e293b] border border-slate-600 flex items-center justify-center text-xs" title={Config.BUFFS[k].name} style={{borderColor: Config.BUFFS[k].color}}>
                             {Config.BUFFS[k].icon}
                         </div>
                     ))}
                 </div>

                 <div className="flex justify-between text-xs text-slate-400 border-t border-slate-700 pt-1">
                     <span>{Config.CLASSES[p.class].name}</span>
                     <span className="text-yellow-500">{p.inv['adena']||0} Adena</span>
                 </div>
            </div>

            {/* CHAT */}
            <div className="absolute bottom-24 left-4 w-80 h-40 flex flex-col justify-end pointer-events-none" style={{maskImage: 'linear-gradient(to top, black 80%, transparent 100%)'}}>
                {gameLogic.current.chat.map((m, i) => (
                    <div key={i} className={`text-[11px] font-mono mb-1 text-shadow-sm ${m.type === 'gain' ? 'text-green-400' : m.type === 'dmg' ? 'text-red-400' : 'text-slate-300'}`}>
                        {m.msg}
                    </div>
                ))}
            </div>

            {/* BOTTOM BAR */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-3 pointer-events-auto">
                <button onClick={()=>{gameLogic.current.player.auto=!gameLogic.current.player.auto; forceUpdate()}} className={`w-14 h-14 rounded-full border-2 flex items-center justify-center ${p.auto?'border-green-500 text-green-500':'border-slate-600 text-slate-500'} bg-[#1e293b]`}>
                    <Crosshair/>
                </button>
                <button onClick={()=>{gameLogic.current.player.ss=!gameLogic.current.player.ss; forceUpdate()}} className={`w-14 h-14 rounded-full border-2 flex items-center justify-center ${p.ss?'border-yellow-500 text-yellow-500':'border-slate-600 text-slate-500'} bg-[#1e293b] relative`}>
                    <Zap/>
                    <span className="absolute -top-1 -right-1 bg-blue-600 text-[9px] px-1 rounded text-white">{p.inv['ssd']||0}</span>
                </button>
                
                {/* PARTY BUTTON */}
                <button onClick={()=>{gameLogic.current.player.party=!gameLogic.current.player.party; forceUpdate()}} className={`w-14 h-14 rounded-full border-2 flex items-center justify-center ${p.party?'border-green-400 bg-green-900/30 text-green-400':'border-slate-600 text-slate-500'} bg-[#1e293b]`}>
                    <Users/>
                </button>
                
                <div className="w-4"/>
                <button onClick={()=>setModal('inv')} className="w-14 h-14 rounded-full border-2 border-slate-600 bg-[#1e293b] flex items-center justify-center hover:border-indigo-500">
                    <ShoppingBag/>
                </button>
            </div>

            {/* NPC DIALOG */}
            {npcDialog && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/60 z-50 pointer-events-auto" onClick={()=>setNpcDialog(null)}>
                    <div className="bg-[#1e293b] border-2 border-[#334155] p-6 rounded w-80 shadow-2xl" onClick={e=>e.stopPropagation()}>
                        <div className="text-xl font-bold text-yellow-500 mb-1">{npcDialog.name}</div>
                        <div className="text-xs text-slate-400 mb-4 uppercase">{npcDialog.type}</div>
                        
                        {npcDialog.type === 'shop' && (
                             <div className="grid gap-2">
                                 <button onClick={()=>gameLogic.current.buyItem('ssd', 5)} className="bg-[#0f172a] p-2 border border-[#334155] flex justify-between hover:border-yellow-500">
                                     <span>⚡ Soulshot: D</span> <span className="text-yellow-500">5a</span>
                                 </button>
                                 <button onClick={()=>gameLogic.current.buyItem('potion', 30)} className="bg-[#0f172a] p-2 border border-[#334155] flex justify-between hover:border-yellow-500">
                                     <span>🍷 HP Potion</span> <span className="text-yellow-500">30a</span>
                                 </button>
                             </div>
                        )}
                        
                        {npcDialog.type === 'teleport' && (
                             <div className="text-center text-slate-300 py-4">
                                 "I can teleport you to hunting grounds... for a fee."
                                 <div className="mt-2 text-xs text-red-400">(Not implemented in demo)</div>
                             </div>
                        )}
                         {npcDialog.type === 'bank' && (
                             <div className="text-center text-slate-300 py-4">
                                 "Your items are safe with me."
                             </div>
                        )}

                        <button onClick={()=>setNpcDialog(null)} className="w-full mt-4 py-2 bg-red-900/50 border border-red-800 text-red-200">Close</button>
                    </div>
                </div>
            )}

            {/* INVENTORY MODAL */}
            {modal === 'inv' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/60 z-50 pointer-events-auto" onClick={()=>setModal(null)}>
                    <div className="bg-[#1e293b] border-2 border-[#334155] rounded w-96 h-[50vh] flex flex-col shadow-2xl" onClick={e=>e.stopPropagation()}>
                        <div className="p-3 bg-[#0f172a] border-b border-[#334155] flex justify-between font-bold text-slate-200">
                            <span>INVENTORY</span>
                            <button onClick={()=>setModal(null)}><X/></button>
                        </div>
                        <div className="p-4 grid grid-cols-5 gap-2 overflow-y-auto">
                            {Object.entries(p.inv).map(([k, v]) => {
                                if(k === 'adena' || !v) return null;
                                const item = Config.ITEMS[v.id || k];
                                const count = v.qty || v;
                                if(count <= 0) return null;
                                return (
                                    <div key={k} onClick={()=>{
                                            if(item.type==='gear') gameLogic.current.equip(k);
                                            if(item.type==='use') gameLogic.current.useItem(k);
                                         }} 
                                         className={`aspect-square bg-[#0f172a] border border-[#334155] flex items-center justify-center text-2xl relative cursor-pointer hover:border-yellow-500 ${item.grade?'bg-blue-900/20':''}`}>
                                        {item.icon}
                                        {count > 1 && <span className="absolute bottom-0 right-1 text-[9px] text-white">{count}</span>}
                                    </div>
                                )
                            })}
                        </div>
                        <div className="p-3 border-t border-[#334155] flex justify-between items-center text-xs">
                            <span className="text-slate-400">Equipped: {p.equip.weapon ? Config.ITEMS[p.equip.weapon].name : 'None'}</span>
                            {p.equip.acc && <span className="text-yellow-400">{Config.ITEMS[p.equip.acc].name}</span>}
                        </div>
                    </div>
                </div>
            )}
            
            <button onClick={()=>signOut(auth)} className="absolute top-4 right-4 pointer-events-auto bg-red-900/80 px-3 py-1 rounded text-xs border border-red-700 hover:bg-red-700">LOGOUT</button>
        </div>
    );
}
