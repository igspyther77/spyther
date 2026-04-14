import makeWASocket, { useMultiFileAuthState, DisconnectReason, delay, fetchLatestBaileysVersion, Browsers } from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import pino from 'pino';
import fs from 'fs';
import readline from 'readline';

const ROLES_FILE = './data/roles.json';
const BOTS_FILE = './data/bots.json';
const DELAYS_FILE = './data/delays.json';

const defaultRoles = {
    admins: [],
    subAdmins: {}
};

const defaultDelays = {
    nc1: 50, nc2: 50, nc3: 50, nc4: 50, nc5: 50, nc6: 50, nc7: 50,
    nc8: 50, nc9: 50, nc10: 50, nc11: 50, nc12: 50, nc13: 50,
    triple1: 50, triple2: 50, triple3: 50, triple4: 50
};

const CONSTANT_WORDS = [
    'TMR🐿️',
    'CHUTIYA🐦‍🔥', 
    'CHUD🦕',
    'TBKC🦐',
    'TMKC🐚',
    'RANDI🐡',
    'POOR🐬',
    'AUTO WALE🦡',
    'LUN CHUS🐾',
    'MA CHUDA👻',
    'JATIN TERA PAPA🕷️',
    'TMKC ME AALU🦋',
    'CHUDJA🐣'
];

// ========== ALL EMOJI SECTIONS (12 SECTIONS) ==========
const emojiArrays = {
    // SECTION 1: FACES & EMOTIONS
    nc1: ['🤢','😩','😣','😖','😫','🥶','🫩','🤥','🤓','😇','😎','🤯'],
    nc2: ['💖','💘','💕','🩶','💞','💙','💗','🩷','❤️‍🩹','🤍','💜','💚'],
    nc3: ['🌙','🌑','🌘','🌗','🌖','🌕','🌔','🌓','🌒','🌑','🌚','🌛'],
    
    // SECTION 2: NATURE & FLOWERS
    nc4: ['🌷','🌺','🥀','🍂','🪷','🪻','🌻','🏵️','💐','🌼','🌸','🌹'],
    nc5: ['🌩️','⭐','✨','⚜️','🌟','🪔','💫','⚡','💡','🏮','🔦','🕯️'],
    nc6: ['🏞️','🪺','❄️','🌋','💧','🪵','🪹','🪨','🌬️','🫧','🌀','🌊'],
    
    // SECTION 3: FLAGS & SYMBOLS
    nc7: ['🇦🇪','🇦🇩','🇦🇪','🇦🇫','🇦🇬','🇦🇮','🇦🇱','🇦🇲','🇦🇴','🇦🇶','🇦🇷','🇦🇸'],
    nc8: ['🖋️','🖊️','🖍️','🖌️','📐','📏','✂️','🖇️','✏️','✒️','🔏','📝'],
    nc9: ['🪽','🐼','🦎','🦇','🦭','🐦‍🔥','🦘','🦆','🦑','🐚','🦜','🦢'],
    
    // SECTION 4: COLORS & SHAPES
    nc10: ['🟥','🟧','🟨','🟩','♂️','🟦','🟪','🟫','⬛','⬜','🔴','🟢'],
    nc11: ['💠','🔷','🔹','💠','🔷','🔹','💠','🔷','🔹','💠','🔶','🔸'],
    nc12: ['🦚','🪱','🦠','🦋','🐣','🦔','🦨','🦒','🫏','🐍','🐸','🦥'],
    nc13: ['🌀','🫧','💧','🌀','🫧','💧','🌀','🫧','💧','🌀','🌪️','💨']
};

// ========== TRIPLE ATTACK DEFINITIONS ==========
const tripleNcCombos = {
    triple1: ['nc1', 'nc2', 'nc3'],     // FACES + HEARTS + MOONS
    triple2: ['nc4', 'nc5', 'nc6'],     // FLOWERS + STARS + NATURE
    triple3: ['nc7', 'nc8', 'nc9'],     // FLAGS + WRITING + ANIMALS
    triple4: ['nc10', 'nc11', 'nc12']   // COLORS + SHAPES + CREATURES
};

// ========== CUSTOM FONT CONVERSION ==========
const customFontMap = {
    // Your provided letters
    'T': 'ᴛ', 'ʀ': 'ʀ', 'ɪ': 'ɪ', 'ᴘ': 'ᴘ', 'ʟ': 'ʟ', 'ᴇ': 'ᴇ',
    'ɴ': 'ɴ', 'ᴄ': 'ᴄ', 's': 's', 'ᴛ': 'ᴛ', 'ᴀ': 'ᴀ', 'ʀ': 'ʀ',
    'ᴅ': 'ᴅ', 'ǫ': 'ǫ', 'ᴡ': 'ᴡ', 'ᴇ': 'ᴇ', 'ʀ': 'ʀ', 'ᴛ': 'ᴛ',
    'ʏ': 'ʏ', 'ᴜ': 'ᴜ', 'ɪ': 'ɪ', 'ᴏ': 'ᴏ', 'ᴘ': 'ᴘ', 'ʟ': 'ʟ',
    'ᴋ': 'ᴋ', 'ᴊ': 'ᴊ', 'ʜ': 'ʜ', 'ɢ': 'ɢ', 'ғ': 'ғ', 'ᴅ': 'ᴅ',
    's': 's', 'ᴀ': 'ᴀ', 'ᴢ': 'ᴢ', 'x': 'x', 'ᴄ': 'ᴄ', 'ᴠ': 'ᴠ',
    'ʙ': 'ʙ', 'ɴ': 'ɴ', 'ᴍ': 'ᴍ',
    
    // Complete alphabet mapping
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    
    // Numbers
    '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', 
    '6': '6', '7': '7', '8': '8', '9': '9',
    
    // All special characters
    ' ': ' ', '.': '.', ',': ',', '!': '!', '?': '?', ':': ':', 
    ';': ';', '(': '(', ')': ')', '[': '[', ']': ']', '{': '{', 
    '}': '}', '@': '@', '#': '#', '$': '$', '%': '%', '^': '^', 
    '&': '&', '*': '*', '-': '-', '_': '_', '=': '=', '+': '+', 
    '|': '|', '\\': '\\', '/': '/', '<': '<', '>': '>', '"': '"', 
    "'": "'", '`': '`', '~': '~'
};

function convertToCustomFont(text) {
    return text.split('').map(char => customFontMap[char] || char).join('');
}

// ========== ALL REPLY MESSAGES IN CUSTOM FONT ==========
const replyMessages = {
    rougesBot: convertToCustomFont('rouges bot'),
    tripleNcStarted: convertToCustomFont('triple nc started') + ' 🎀',
    ncStarted: convertToCustomFont('nc started') + ' 🎀',
    csStarted: convertToCustomFont('cs nc started') + ' 🎀',
    ncStopped: convertToCustomFont('nc stopped') + ' 🎀',
    csStopped: convertToCustomFont('cs attack stopped') + ' 🎀',
    tripleDelaySet: convertToCustomFont('triple delay set to') + ' 🎀',
    ncDelaySet: convertToCustomFont('nc delay set to') + ' 🎀',
    youAreNowAdmin: convertToCustomFont('you are now the admin') + ' 🎀',
    youAreAlreadyAdmin: convertToCustomFont('you are already the admin') + ' 🎀',
    adminAlreadyExists: convertToCustomFont('admin already exists') + ' 🎀',
    youAreNoLongerAdmin: convertToCustomFont('you are no longer an admin') + ' 🎀',
    youAreNotAdmin: convertToCustomFont('you are not an admin') + ' 🎀',
    subAdminAdded: convertToCustomFont('sub-admin added') + ' 🎀',
    alreadySubAdmin: convertToCustomFont('already sub-admin') + ' 🎀',
    subAdminRemoved: convertToCustomFont('sub-admin removed') + ' 🎀',
    notSubAdmin: convertToCustomFont('not a sub-admin') + ' 🎀',
    replyToSomeone: convertToCustomFont('reply to someone') + ' 🎀',
    invalidPhone: convertToCustomFont('invalid phone number') + ' 🎀',
    useInGroup: convertToCustomFont('use in group') + ' 🎀',
    delayTooLow: convertToCustomFont('delay must be >= 50ms') + ' 🎀',
    invalidNcNumber: convertToCustomFont('invalid nc number use nc1 to nc13') + ' 🎀',
    usage: convertToCustomFont('usage') + ' 🎀',
    activeBots: convertToCustomFont('active bots') + ' 🎀',
    rougesStatus: convertToCustomFont('rouges status') + ' 🎀',
    individualNc: convertToCustomFont('individual nc') + ' 🎀',
    constantText: convertToCustomFont('constant text') + ' 🎀',
    tripleAttacks: convertToCustomFont('triple attacks') + ' 🎀',
    constantTexts: convertToCustomFont('constant texts') + ' 🎀',
    rougesPing: convertToCustomFont('rouges ping') + ' 🎀',
    activeBotsCount: convertToCustomFont('active bots') + ' 🎀',
    connected: convertToCustomFont('connected') + ' 🎀',
    pairingCode: convertToCustomFont('pairing code') + ' 🎀',
    number: convertToCustomFont('number') + ' 🎀',
    total: convertToCustomFont('total') + ' 🎀',
    pinging: convertToCustomFont('pinging') + ' 🎀',
    latency: convertToCustomFont('latency') + ' 🎀',
    botCreated: convertToCustomFont('bot created') + ' 🎀',
    realTripleAttack: convertToCustomFont('real triple attack started') + ' 🎀'
};

// ========== MENU IN CUSTOM FONT ==========
const rougeMenu = convertToCustomFont(`
rouges bot 🎀

.admin commands 🎀
.admin → become admin (dm) 🎀
.sub → make sub-admin (reply) 🎀
.add [num] → add new bot 🎀

.constant text attack 🎀
.cs [text] [nc#] [delay] 🎀
.cwords → show constant texts 🎀
.csstop → stop cs attack 🎀

.real triple attacks (4) 🎀
.triple1 [text] → nc1+nc2+nc3 🎀
.triple2 [text] → nc4+nc5+nc6 🎀
.triple3 [text] → nc7+nc8+nc9 🎀
.triple4 [text] → nc10+nc11+nc12 🎀
.ncstop → stop all nc 🎀

.nc attacks (1-13) 🎀
.nc1 to .nc13 [text] 🎀

.delay controls 🎀
.delaync[1-13] [ms] 🎀
.delaytriple[1-4] [ms] 🎀

.info & status 🎀
.menu → show menu 🎀
.status → active attacks 🎀
.bots → list bots 🎀
.ping → check latency 🎀
`);

function loadRoles() {
    try {
        if (fs.existsSync(ROLES_FILE)) {
            const data = fs.readFileSync(ROLES_FILE, 'utf8');
            return JSON.parse(data);
        }
    } catch (err) {
        console.log('[ROLES] Using defaults');
    }
    return { ...defaultRoles };
}

function saveRoles(roles) {
    try {
        if (!fs.existsSync('./data')) fs.mkdirSync('./data', { recursive: true });
        fs.writeFileSync(ROLES_FILE, JSON.stringify(roles, null, 2));
    } catch (err) {
        console.error('[ROLES] Error:', err.message);
    }
}

function loadDelays() {
    try {
        if (fs.existsSync(DELAYS_FILE)) {
            const data = fs.readFileSync(DELAYS_FILE, 'utf8');
            return { ...defaultDelays, ...JSON.parse(data) };
        }
    } catch (err) {
        console.log('[DELAYS] Using defaults');
    }
    return { ...defaultDelays };
}

function saveDelays(delays) {
    try {
        if (!fs.existsSync('./data')) fs.mkdirSync('./data', { recursive: true });
        fs.writeFileSync(DELAYS_FILE, JSON.stringify(delays, null, 2));
    } catch (err) {
        console.error('[DELAYS] Error:', err.message);
    }
}

let roles = loadRoles();
let ncDelays = loadDelays();

function isAdmin(jid) {
    return roles.admins.includes(jid);
}

function isSubAdmin(jid, groupJid) {
    return roles.subAdmins[groupJid]?.includes(jid) || false;
}

function hasPermission(jid, groupJid) {
    return isAdmin(jid) || isSubAdmin(jid, groupJid);
}

function addAdmin(jid) {
    if (!roles.admins.includes(jid)) {
        roles.admins.push(jid);
        saveRoles(roles);
        return true;
    }
    return false;
}

function removeAdmin(jid) {
    const index = roles.admins.indexOf(jid);
    if (index > -1) {
        roles.admins.splice(index, 1);
        saveRoles(roles);
        return true;
    }
    return false;
}

function addSubAdmin(jid, groupJid) {
    if (!roles.subAdmins[groupJid]) {
        roles.subAdmins[groupJid] = [];
    }
    if (!roles.subAdmins[groupJid].includes(jid)) {
        roles.subAdmins[groupJid].push(jid);
        saveRoles(roles);
        return true;
    }
    return false;
}

function removeSubAdmin(jid, groupJid) {
    if (roles.subAdmins[groupJid]) {
        const index = roles.subAdmins[groupJid].indexOf(jid);
        if (index > -1) {
            roles.subAdmins[groupJid].splice(index, 1);
            saveRoles(roles);
            return true;
        }
    }
    return false;
}

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const question = (text) => new Promise((resolve) => rl.question(text, resolve));

class CommandBus {
    constructor() {
        this.botSessions = new Map();
        this.processedMessages = new Map();
    }

    registerBot(botId, session) {
        this.botSessions.set(botId, session);
    }

    unregisterBot(botId) {
        this.botSessions.delete(botId);
    }

    shouldProcessMessage(msgId) {
        if (this.processedMessages.has(msgId)) return false;
        this.processedMessages.set(msgId, Date.now());
        return true;
    }

    async broadcastCommand(commandType, data, originBotId, sendConfirmation = true) {
        const bots = Array.from(this.botSessions.values()).filter(b => b.connected);
        
        for (const bot of bots) {
            try {
                const isOrigin = bot.botId === originBotId;
                await bot.executeCommand(commandType, data, isOrigin && sendConfirmation);
            } catch (err) {
                console.error(`[${bot.botId}] Error:`, err.message);
            }
        }
    }

    getAllBots() {
        return Array.from(this.botSessions.values());
    }

    getConnectedBots() {
        return Array.from(this.botSessions.values()).filter(b => b.connected);
    }

    getLeaderBot() {
        const connected = this.getConnectedBots();
        return connected.length > 0 ? connected[0] : null;
    }
}

class BotSession {
    constructor(botId, phoneNumber, botManager, requestingJid = null) {
        this.botId = botId;
        this.phoneNumber = phoneNumber;
        this.botManager = botManager;
        this.requestingJid = requestingJid;
        this.sock = null;
        this.connected = false;
        this.botNumber = null;
        this.authPath = `./auth/${botId}`;
        this.pairingCodeRequested = false;
        
        this.activeNameChanges = new Map();
        this.activeTripleNc = new Map();
        this.activeConstantAttacks = new Map();
    }

    async connect() {
        try {
            if (!fs.existsSync(this.authPath)) {
                fs.mkdirSync(this.authPath, { recursive: true });
            }

            const { state, saveCreds } = await useMultiFileAuthState(this.authPath);
            const { version } = await fetchLatestBaileysVersion();
            
            const needsPairing = !state.creds.registered;

            this.sock = makeWASocket({
                auth: state,
                logger: pino({ level: 'silent' }),
                browser: Browsers.macOS('Chrome'),
                version,
                printQRInTerminal: false,
                connectTimeoutMs: 60000,
                defaultQueryTimeoutMs: 0,
                keepAliveIntervalMs: 30000
            });

            this.sock.ev.on('connection.update', async (update) => {
                const { connection, lastDisconnect } = update;

                if (needsPairing && this.phoneNumber && !this.pairingCodeRequested && !state.creds.registered) {
                    this.pairingCodeRequested = true;
                    await delay(2000);
                    try {
                        const code = await this.sock.requestPairingCode(this.phoneNumber);
                        console.log(`[${this.botId}] Pairing code: ${code}`);
                        
                        if (this.requestingJid) {
                            const connectedBots = this.botManager.commandBus.getConnectedBots();
                            if (connectedBots.length > 0) {
                                const firstBot = connectedBots[0];
                                await firstBot.sock.sendMessage(this.requestingJid, {
                                    text: `${replyMessages.rougesBot}\n\n${replyMessages.pairingCode} ${code}\n\n${replyMessages.number} ${this.phoneNumber} 🎀`
                                });
                            }
                        } else {
                            console.log(`\n${replyMessages.rougesBot}`);
                            console.log(`${replyMessages.pairingCode} ${code}`);
                            console.log(`${replyMessages.number} ${this.phoneNumber} 🎀\n`);
                        }
                    } catch (err) {
                        console.error(`[${this.botId}] Error getting pairing code:`, err.message);
                        this.pairingCodeRequested = false;
                    }
                }

                if (connection === 'close') {
                    const statusCode = (lastDisconnect?.error instanceof Boom)
                        ? lastDisconnect.error.output.statusCode
                        : 500;

                    const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                    
                    console.log(`[${this.botId}] Connection closed. Status: ${statusCode}`);
                    this.connected = false;

                    if (shouldReconnect) {
                        console.log(`[${this.botId}] Reconnecting in 5 seconds...`);
                        await delay(5000);
                        this.connect();
                    } else {
                        console.log(`[${this.botId}] Logged out.`);
                        this.botManager.removeBot(this.botId);
                    }
                } else if (connection === 'open') {
                    console.log(`[${this.botId}] ✅ ${replyMessages.connected}`);
                    this.connected = true;
                    this.botNumber = this.sock.user.id.split(':')[0] + '@s.whatsapp.net';
                }
            });

            this.sock.ev.on('creds.update', saveCreds);
            this.sock.ev.on('messages.upsert', async (m) => this.handleMessage(m));

        } catch (err) {
            console.error(`[${this.botId}] Connection error:`, err.message);
        }
    }

    async handleMessage({ messages, type }) {
        try {
            if (type !== 'notify') return;
            
            const msg = messages[0];
            if (!msg.message) return;
            if (msg.key.fromMe) return;
            
            const from = msg.key.remoteJid;
            const isGroup = from.endsWith('@g.us');
            const sender = isGroup ? msg.key.participant : from;
            
            const msgId = msg.key.id;
            const isLeader = this.botManager.commandBus.getLeaderBot()?.botId === this.botId;
            
            if (!isLeader && !this.botManager.commandBus.shouldProcessMessage(msgId)) return;
            if (isLeader && !this.botManager.commandBus.shouldProcessMessage(msgId)) return;
            
            let text = msg.message.conversation || 
                      msg.message.extendedTextMessage?.text || 
                      msg.message.imageMessage?.caption || '';

            const originalText = text;
            text = text.trim().toLowerCase();

            const isDM = !isGroup;
            const senderIsAdmin = isAdmin(sender);
            const senderIsSubAdmin = isGroup ? isSubAdmin(sender, from) : false;
            const senderHasPermission = senderIsAdmin || senderIsSubAdmin;

            // ADMIN COMMANDS
            if (isDM && text === '.admin') {
                if (roles.admins.length === 0) {
                    addAdmin(sender);
                    await this.sendMessage(from, `${replyMessages.rougesBot}\n\n${replyMessages.youAreNowAdmin}`);
                } else if (senderIsAdmin) {
                    await this.sendMessage(from, replyMessages.youAreAlreadyAdmin);
                } else {
                    await this.sendMessage(from, replyMessages.adminAlreadyExists);
                }
                return;
            }

            if (isDM && text === '.removeadmin') {
                if (senderIsAdmin) {
                    removeAdmin(sender);
                    await this.sendMessage(from, replyMessages.youAreNoLongerAdmin);
                } else {
                    await this.sendMessage(from, replyMessages.youAreNotAdmin);
                }
                return;
            }

            if (isGroup && text === '.sub' && senderIsAdmin) {
                if (!msg.message.extendedTextMessage?.contextInfo?.participant) {
                    await this.sendMessage(from, replyMessages.replyToSomeone);
                    return;
                }
                const targetJid = msg.message.extendedTextMessage.contextInfo.participant;
                if (addSubAdmin(targetJid, from)) {
                    await this.sendMessage(from, replyMessages.subAdminAdded, [targetJid]);
                } else {
                    await this.sendMessage(from, replyMessages.alreadySubAdmin);
                }
                return;
            }

            if (isGroup && text === '.removesub' && senderIsAdmin) {
                if (!msg.message.extendedTextMessage?.contextInfo?.participant) {
                    await this.sendMessage(from, replyMessages.replyToSomeone);
                    return;
                }
                const targetJid = msg.message.extendedTextMessage.contextInfo.participant;
                if (removeSubAdmin(targetJid, from)) {
                    await this.sendMessage(from, replyMessages.subAdminRemoved, [targetJid]);
                } else {
                    await this.sendMessage(from, replyMessages.notSubAdmin);
                }
                return;
            }

            if (originalText.toLowerCase().startsWith('.add ') && senderIsAdmin) {
                const number = originalText.slice(5).trim().replace(/[^0-9]/g, '');
                if (number.length < 10) {
                    await this.sendMessage(from, replyMessages.invalidPhone);
                    return;
                }
                
                const result = await this.botManager.addBot(number, from);
                await this.sendMessage(from, result);
                return;
            }

            if (text === '.bots' && senderHasPermission) {
                const bots = this.botManager.commandBus.getAllBots();
                let msg = `${replyMessages.activeBots}\n\n`;
                msg += `${replyMessages.total} ${bots.length}\n\n`;
                
                bots.forEach(bot => {
                    const status = bot.connected ? '✅' : '⚠️';
                    msg += `${bot.botId}: ${status}\n`;
                });
                
                await this.sendMessage(from, msg);
                return;
            }

            if (text === '.ping' && senderHasPermission) {
                const startTime = Date.now();
                await this.sendMessage(from, `${replyMessages.pinging}`);
                const latency = Date.now() - startTime;
                await this.sendMessage(from, `${replyMessages.rougesPing}\n\n${replyMessages.latency} ${latency}ᴍs`);
                return;
            }

            if (text === '.cwords' && senderHasPermission) {
                let constMsg = `${replyMessages.constantTexts}\n\n`;
                constMsg += `${replyMessages.total} ${CONSTANT_WORDS.length}\n\n`;
                CONSTANT_WORDS.forEach((word, index) => {
                    constMsg += `${index + 1}. ${word}\n`;
                });
                await this.sendMessage(from, constMsg);
                return;
            }

            if (!senderHasPermission) return;

            if (text === '.menu') {
                await this.sendMessage(from, rougeMenu);
                return;
            }

            if (text === '.status') {
                const allBots = this.botManager.commandBus.getAllBots();
                let totalName = 0, totalTriple = 0, totalConstant = 0;
                
                allBots.forEach(bot => {
                    totalName += bot.activeNameChanges.size;
                    totalTriple += bot.activeTripleNc.size;
                    totalConstant += bot.activeConstantAttacks.size;
                });
                
                const statusMsg = `${replyMessages.rougesStatus}\n\n` +
                                `${replyMessages.individualNc} ${totalName}\n` +
                                `${replyMessages.constantText} ${totalConstant}\n` +
                                `${replyMessages.tripleAttacks} ${totalTriple}\n` +
                                `${replyMessages.activeBotsCount} ${allBots.filter(b => b.connected).length}/${allBots.length}`;
                
                await this.sendMessage(from, statusMsg);
                return;
            }

            // CONSTANT TEXT ATTACK COMMAND (.cs)
            if (originalText.toLowerCase().startsWith('.cs ')) {
                const args = originalText.slice(4).trim().split(' ');
                if (args.length < 3) {
                    await this.sendMessage(from, `${replyMessages.usage} .cs [ᴛᴇxᴛ] [ɴᴄ#] [ᴅᴇʟᴀʏ]`);
                    return;
                }

                const csDelay = parseInt(args[args.length - 1]);
                const ncKey = args[args.length - 2].toLowerCase();
                const userText = args.slice(0, -2).join(' ');

                if (!emojiArrays[ncKey]) {
                    await this.sendMessage(from, replyMessages.invalidNcNumber);
                    return;
                }

                if (isNaN(csDelay) || csDelay < 50) {
                    await this.sendMessage(from, replyMessages.delayTooLow);
                    return;
                }

                if (!isGroup) {
                    await this.sendMessage(from, replyMessages.useInGroup);
                    return;
                }

                await this.botManager.commandBus.broadcastCommand('start_cs', { 
                    from, 
                    userText, 
                    csDelay, 
                    ncKey 
                }, this.botId);
                return;
            }
            else if (text === '.csstop') {
                if (!isGroup) {
                    await this.sendMessage(from, replyMessages.useInGroup);
                    return;
                }
                await this.botManager.commandBus.broadcastCommand('stop_cs', { from }, this.botId);
                return;
            }

            // TRIPLE ATTACK DELAY SETTING
            for (let i = 1; i <= 4; i++) {
                const tripleKey = `triple${i}`;
                if (originalText.toLowerCase().startsWith(`.delay${tripleKey} `)) {
                    const delayValue = parseInt(originalText.split(' ')[1]);
                    if (isNaN(delayValue) || delayValue < 50) {
                        await this.sendMessage(from, replyMessages.delayTooLow);
                        return;
                    }
                    
                    ncDelays[tripleKey] = delayValue;
                    saveDelays(ncDelays);
                    
                    await this.sendMessage(from, `${replyMessages.tripleDelaySet} ${delayValue}ᴍs`);
                    return;
                }
            }

            // INDIVIDUAL NC DELAY SETTING
            for (let i = 1; i <= 13; i++) {
                const ncKey = `nc${i}`;
                if (originalText.toLowerCase().startsWith(`.delaync${i} `)) {
                    const delayValue = parseInt(originalText.split(' ')[1]);
                    if (isNaN(delayValue) || delayValue < 50) {
                        await this.sendMessage(from, replyMessages.delayTooLow);
                        return;
                    }
                    
                    ncDelays[ncKey] = delayValue;
                    saveDelays(ncDelays);
                    
                    await this.sendMessage(from, `${replyMessages.ncDelaySet} ${delayValue}ᴍs`);
                    return;
                }
            }

            // TRIPLE ATTACK COMMANDS
            for (let i = 1; i <= 4; i++) {
                const tripleKey = `triple${i}`;
                if (originalText.toLowerCase().startsWith(`.${tripleKey} `)) {
                    const nameText = originalText.slice(tripleKey.length + 2).trim();
                    if (!nameText) {
                        await this.sendMessage(from, `${replyMessages.usage} .${tripleKey} [ᴛᴇxᴛ]`);
                        return;
                    }

                    if (!isGroup) {
                        await this.sendMessage(from, replyMessages.useInGroup);
                        return;
                    }

                    await this.botManager.commandBus.broadcastCommand('start_triple_nc', { 
                        from, 
                        nameText, 
                        tripleKey 
                    }, this.botId);
                    return;
                }
            }

            // INDIVIDUAL NC ATTACK COMMANDS
            for (let i = 1; i <= 13; i++) {
                const ncKey = `nc${i}`;
                if (originalText.toLowerCase().startsWith(`.${ncKey} `)) {
                    const nameText = originalText.slice(ncKey.length + 2).trim();
                    if (!nameText) {
                        await this.sendMessage(from, `${replyMessages.usage} .${ncKey} [ᴛᴇxᴛ]`);
                        return;
                    }

                    if (!isGroup) {
                        await this.sendMessage(from, replyMessages.useInGroup);
                        return;
                    }

                    await this.botManager.commandBus.broadcastCommand('start_nc', { from, nameText, ncKey }, this.botId);
                    return;
                }
            }

            if (text === '.ncstop') {
                if (!isGroup) {
                    await this.sendMessage(from, replyMessages.useInGroup);
                    return;
                }

                await this.botManager.commandBus.broadcastCommand('stop_nc', { from }, this.botId);
                await this.botManager.commandBus.broadcastCommand('stop_triple_nc', { from }, this.botId);
                return;
            }

        } catch (err) {
            console.error(`[${this.botId}] ERROR:`, err);
        }
    }

    async executeCommand(commandType, data, sendConfirmation = true) {
        try {
            // CONSTANT TEXT ATTACK (.cs command)
            if (commandType === 'start_cs') {
                const { from, userText, csDelay, ncKey } = data;
                
                const taskId = `${from}_cs`;
                
                if (this.activeConstantAttacks.has(taskId)) {
                    this.activeConstantAttacks.get(taskId).active = false;
                    await delay(100);
                }

                const csTask = { 
                    active: true,
                    userText: userText,
                    constantIndex: 0
                };
                this.activeConstantAttacks.set(taskId, csTask);

                const runCS = async () => {
                    while (csTask.active) {
                        try {
                            const constantWord = CONSTANT_WORDS[csTask.constantIndex % CONSTANT_WORDS.length];
                            const finalText = `${userText} ${constantWord}`;
                            await this.sock.groupUpdateSubject(from, finalText);
                            csTask.constantIndex++;
                            await delay(csDelay);
                        } catch (err) {
                            await delay(csDelay);
                        }
                    }
                };

                runCS();

                if (sendConfirmation) {
                    await this.sendMessage(from, replyMessages.csStarted);
                }
            }
            
            // STOP CONSTANT TEXT ATTACK
            else if (commandType === 'stop_cs') {
                const { from } = data;
                let stopped = 0;
                
                this.activeConstantAttacks.forEach((task, taskId) => {
                    if (taskId.startsWith(from)) {
                        task.active = false;
                        this.activeConstantAttacks.delete(taskId);
                        stopped++;
                    }
                });

                if (stopped > 0 && sendConfirmation) {
                    await this.sendMessage(from, replyMessages.csStopped);
                }
            }
            
            // INDIVIDUAL NC ATTACK
            else if (commandType === 'start_nc') {
                const { from, nameText, ncKey } = data;
                const emojis = emojiArrays[ncKey] || ['❓'];
                const nameDelay = ncDelays[ncKey] || 50;
                
                // Start 5 parallel threads for intense attack
                for (let i = 0; i < 5; i++) {
                    const taskId = `${from}_${ncKey}_${i}`;
                    if (this.activeNameChanges.has(taskId)) {
                        this.activeNameChanges.delete(taskId);
                        await delay(100);
                    }

                    let emojiIndex = i * Math.floor(emojis.length / 5);
                    
                    const runLoop = async () => {
                        this.activeNameChanges.set(taskId, true);
                        // Stagger start times for each thread
                        await delay(i * 100);
                        while (this.activeNameChanges.get(taskId)) {
                            try {
                                const emoji = emojis[Math.floor(emojiIndex) % emojis.length];
                                const newName = `${nameText} ${emoji}`;
                                await this.sock.groupUpdateSubject(from, newName);
                                emojiIndex++;
                                await delay(nameDelay);
                            } catch (err) {
                                await delay(nameDelay);
                            }
                        }
                    };

                    runLoop();
                }

                if (sendConfirmation) {
                    await this.sendMessage(from, replyMessages.ncStarted);
                }
            }
            
            // ========== REAL TRIPLE NC ATTACK ==========
            // This runs ALL THREE NC SECTIONS SIMULTANEOUSLY
            else if (commandType === 'start_triple_nc') {
                const { from, nameText, tripleKey } = data;
                const comboNames = tripleNcCombos[tripleKey] || ['nc1', 'nc2', 'nc3'];
                const tripleDelay = ncDelays[tripleKey] || 50;
                
                const tripleTaskId = `${from}_${tripleKey}`;
                const tripleTask = { 
                    active: true, 
                    ncKeys: comboNames,
                    threads: []
                };
                this.activeTripleNc.set(tripleTaskId, tripleTask);
                
                console.log(`[${this.botId}] 🔥 REAL TRIPLE ATTACK: Running ${comboNames.join(' + ')} simultaneously`);
                
                // Start EACH of the 3 NC sections as INDEPENDENT attacks
                comboNames.forEach((ncKey, sectionIndex) => {
                    const emojis = emojiArrays[ncKey] || ['❓'];
                    const individualDelay = ncDelays[ncKey] || 50;
                    
                    // Start 3 parallel threads for EACH NC section
                    for (let threadIndex = 0; threadIndex < 3; threadIndex++) {
                        const threadId = `${from}_${tripleKey}_${ncKey}_${threadIndex}`;
                        
                        if (this.activeNameChanges.has(threadId)) {
                            this.activeNameChanges.delete(threadId);
                        }

                        let emojiIndex = threadIndex * Math.floor(emojis.length / 3);
                        
                        const runTripleThread = async () => {
                            this.activeNameChanges.set(threadId, true);
                            // Stagger start times for each thread in each section
                            await delay((sectionIndex * 50) + (threadIndex * 30));
                            
                            while (this.activeNameChanges.get(threadId) && tripleTask.active) {
                                try {
                                    const emoji = emojis[Math.floor(emojiIndex) % emojis.length];
                                    const newName = `${nameText} ${emoji}`;
                                    await this.sock.groupUpdateSubject(from, newName);
                                    emojiIndex++;
                                    await delay(individualDelay);
                                } catch (err) {
                                    await delay(individualDelay);
                                }
                            }
                            this.activeNameChanges.delete(threadId);
                        };

                        // Store thread reference
                        tripleTask.threads.push(threadId);
                        runTripleThread();
                    }
                });

                if (sendConfirmation) {
                    const comboNames = tripleNcCombos[tripleKey];
                    const firstEmoji = emojiArrays[comboNames[0]]?.[0] || '❓';
                    const secondEmoji = emojiArrays[comboNames[1]]?.[0] || '❓';
                    const thirdEmoji = emojiArrays[comboNames[2]]?.[0] || '❓';
                    
                    const confirmationMsg = `${replyMessages.realTripleAttack}\n\n` +
                                          `${convertToCustomFont('running')}: ${comboNames.join(' + ')}\n` +
                                          `${convertToCustomFont('emojis')}: ${firstEmoji} ${secondEmoji} ${thirdEmoji}\n` +
                                          `${convertToCustomFont('delay')}: ${tripleDelay}ᴍs`;
                    
                    await this.sendMessage(from, confirmationMsg);
                }
            }
            
            // STOP INDIVIDUAL NC
            else if (commandType === 'stop_nc') {
                const { from } = data;
                let stopped = 0;
                
                this.activeNameChanges.forEach((value, taskId) => {
                    if (taskId.startsWith(from) && !taskId.includes('_triple')) {
                        this.activeNameChanges.set(taskId, false);
                        this.activeNameChanges.delete(taskId);
                        stopped++;
                    }
                });

                if (stopped > 0 && sendConfirmation) {
                    await this.sendMessage(from, replyMessages.ncStopped);
                }
            }
            
            // STOP TRIPLE NC
            else if (commandType === 'stop_triple_nc') {
                const { from } = data;
                let stoppedCombos = 0;
                
                this.activeTripleNc.forEach((task, taskId) => {
                    if (taskId.startsWith(from)) {
                        task.active = false;
                        
                        // Stop all threads in this triple attack
                        task.threads?.forEach(threadId => {
                            if (this.activeNameChanges.has(threadId)) {
                                this.activeNameChanges.delete(threadId);
                            }
                        });
                        
                        // Stop individual NC threads for each section
                        task.ncKeys?.forEach(ncKey => {
                            for (let i = 0; i < 3; i++) {
                                const threadId = `${from}_${taskId.split('_')[1]}_${ncKey}_${i}`;
                                if (this.activeNameChanges.has(threadId)) {
                                    this.activeNameChanges.delete(threadId);
                                }
                            }
                        });
                        
                        this.activeTripleNc.delete(taskId);
                        stoppedCombos++;
                    }
                });

                if (stoppedCombos > 0 && sendConfirmation) {
                    await this.sendMessage(from, replyMessages.ncStopped);
                }
            }
            
        } catch (err) {
            console.error(`[${this.botId}] executeCommand error:`, err.message);
        }
    }

    async sendMessage(jid, text, mentions = []) {
        if (!this.sock || !this.connected) return;
        try {
            const message = { text };
            if (mentions.length > 0) {
                message.mentions = mentions;
            }
            await this.sock.sendMessage(jid, message);
        } catch (err) {
            console.error(`[${this.botId}] Send message error:`, err.message);
        }
    }
}

class BotManager {
    constructor() {
        this.bots = new Map();
        this.commandBus = new CommandBus();
        this.botCounter = 0;
        this.loadedData = this.loadBots();
    }

    loadBots() {
        try {
            if (fs.existsSync(BOTS_FILE)) {
                const data = fs.readFileSync(BOTS_FILE, 'utf8');
                const savedBots = JSON.parse(data);
                this.botCounter = savedBots.counter || 0;
                console.log(`[MANAGER] Found ${savedBots.bots?.length || 0} saved bot(s)`);
                return savedBots;
            }
        } catch (err) {
            console.log('[MANAGER] No saved bots found, starting fresh');
        }
        return { counter: 0, bots: [] };
    }

    saveBots() {
        try {
            if (!fs.existsSync('./data')) {
                fs.mkdirSync('./data', { recursive: true });
            }
            const data = {
                counter: this.botCounter,
                bots: Array.from(this.bots.entries()).map(([id, bot]) => ({
                    id,
                    phoneNumber: bot.phoneNumber,
                    connected: bot.connected
                }))
            };
            fs.writeFileSync(BOTS_FILE, JSON.stringify(data, null, 2));
        } catch (err) {
            console.error('[MANAGER] Error saving bots:', err.message);
        }
    }

    async restoreSavedBots() {
        if (this.loadedData.bots && this.loadedData.bots.length > 0) {
            console.log(`[MANAGER] Restoring ${this.loadedData.bots.length} bot session(s)...`);
            
            for (const botData of this.loadedData.bots) {
                const authPath = `./auth/${botData.id}`;
                const hasAuth = fs.existsSync(authPath) && fs.readdirSync(authPath).length > 0;
                
                let phoneNumber = botData.phoneNumber;
                
                if (!hasAuth && !phoneNumber) {
                    console.log(`\n[MANAGER] ${botData.id} has no credentials and no phone number.`);
                    phoneNumber = await question(`Enter phone number for ${botData.id} (e.g. 919876543210): `);
                    phoneNumber = phoneNumber.replace(/[^0-9]/g, '');
                    
                    if (!phoneNumber || phoneNumber.length < 10) {
                        console.log(`[MANAGER] Invalid number. Removing ${botData.id}...`);
                        continue;
                    }
                }
                
                const session = new BotSession(botData.id, phoneNumber, this, null);
                this.bots.set(botData.id, session);
                this.commandBus.registerBot(botData.id, session);
                
                console.log(`[MANAGER] Reconnecting ${botData.id}...`);
                await session.connect();
                await delay(2000);
            }
            
            this.saveBots();
        } else {
            console.log('[MANAGER] No saved sessions. Waiting for first bot via .add command...');
            
            const phoneNumber = await question('Enter phone number for BOT1 (or press Enter to skip): ');
            if (phoneNumber && phoneNumber.trim()) {
                const cleanNumber = phoneNumber.replace(/[^0-9]/g, '');
                if (cleanNumber.length >= 10) {
                    await this.addBot(cleanNumber, null);
                }
            } else {
                console.log('[MANAGER] Skipped. Use .add command in WhatsApp to add bots.\n');
            }
        }
    }

    async addBot(phoneNumber, requestingJid = null) {
        this.botCounter++;
        const botId = `BOT${this.botCounter}`;
        
        const session = new BotSession(botId, phoneNumber, this, requestingJid);
        this.bots.set(botId, session);
        this.commandBus.registerBot(botId, session);
        
        await session.connect();
        this.saveBots();
        
        return `${replyMessages.botCreated}\n\n✅ ${convertToCustomFont('bot session created')} 🎀\n📱 ${replyMessages.number} ${phoneNumber}\n\n⏳ ${convertToCustomFont('waiting for pairing code')} 🎀`;
    }

    removeBot(botId) {
        if (this.bots.has(botId)) {
            this.commandBus.unregisterBot(botId);
            this.bots.delete(botId);
            this.saveBots();
            console.log(`[MANAGER] Removed ${botId}`);
        }
    }
}

// ========== STARTUP MESSAGE ==========
console.log(`${convertToCustomFont('rouges bot system')} 🎀\n`);
console.log(`${convertToCustomFont('features')}:`);
console.log(`${convertToCustomFont('• constant text attack')} 🌀`);
console.log(`${convertToCustomFont('• real triple attacks (3 sections at once)')} 🔥`);
console.log(`${convertToCustomFont('• 13 nc types with expanded emojis')} ⚔️`);
console.log(`${convertToCustomFont('• fast pairing system')} ⚡`);
console.log(`\n${convertToCustomFont('triple attacks')}:`);
console.log(`${convertToCustomFont('• triple1 → nc1 + nc2 + nc3')} 🎭`);
console.log(`${convertToCustomFont('• triple2 → nc4 + nc5 + nc6')} 🌸`);
console.log(`${convertToCustomFont('• triple3 → nc7 + nc8 + nc9')} 🏳️`);
console.log(`${convertToCustomFont('• triple4 → nc10 + nc11 + nc12')} 🎨`);
console.log(`\n${convertToCustomFont('minimum delay')}: 50ᴍs`);
console.log(`${convertToCustomFont('send .menu to see commands')} 🎀\n`);

const botManager = new BotManager();
await botManager.restoreSavedBots();
rl.close();

console.log(`\n✅ ${replyMessages.connected}`);
console.log(`${convertToCustomFont('send .admin in dm to become admin')} 🎀`);
console.log(`${convertToCustomFont('send .cs hello nc1 50 to test')} 🌀`);
console.log(`${convertToCustomFont('send .triple1 raid for real triple attack')} 🔥`);
console.log(`${convertToCustomFont('send .cwords to see constant texts')} 📝`);
console.log(`${convertToCustomFont('enjoy the power of rouges bot')} ⚡\n`);