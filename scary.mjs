import makeWASocket, { useMultiFileAuthState, DisconnectReason, delay, fetchLatestBaileysVersion, Browsers, downloadMediaMessage, generateWAMessageFromContent, proto } from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import pino from 'pino';
import fs from 'fs';
import readline from 'readline';
import gtts from 'node-gtts';

const ROLES_FILE = './data/roles.json';
const BOTS_FILE = './data/bots.json';
const DELAYS_FILE = './data/ncDelays.json';

const defaultRoles = {
    admins: [],
    subAdmins: {}
};

const defaultDelays = {
    // Individual NC delays
    nc1: 200, nc2: 200, nc3: 200, nc4: 200, nc5: 200,
    nc6: 200, nc7: 200, nc8: 200, nc9: 200, nc10: 200,
    nc11: 200, nc12: 200, nc13: 200, nc14: 200, nc15: 200,
    nc16: 200, nc17: 200, nc18: 200, nc19: 200, nc20: 200,
    nc21: 200, nc22: 200, nc23: 200, nc24: 200, nc25: 200,
    nc26: 200, nc27: 200, nc28: 200, nc29: 200, nc30: 200,
    nc31: 200, nc32: 200, nc33: 200, nc34: 200, nc35: 200,
    nc36: 200, nc37: 200, nc38: 200, nc39: 200, nc40: 200,
    nc41: 200, nc42: 200, nc43: 200, nc44: 200, nc45: 200,
    nc46: 200, nc47: 200, nc48: 200, nc49: 200, nc50: 200,
    nc51: 200, nc52: 200, nc53: 200, nc54: 200, nc55: 200,
    nc56: 200, nc57: 200, nc58: 200, nc59: 200, nc60: 200,
    nc61: 200, nc62: 200, nc63: 200, nc64: 200, nc65: 200,
    nc66: 200, nc67: 200, nc68: 200, nc69: 200, nc70: 200,
    nc71: 200, nc72: 200, nc73: 200, nc74: 200, nc75: 200,
    nc76: 200, nc77: 200, nc78: 200, nc79: 200, nc80: 200,
    nc81: 200, nc82: 200, nc83: 200, nc84: 200, nc85: 200,
    nc86: 200, nc87: 200, nc88: 200, nc89: 200, nc90: 200,
    nc91: 200, nc92: 200, nc93: 200, nc94: 200, nc95: 200,
    nc96: 200, nc97: 200, nc98: 200, nc99: 200, nc100: 200,
    
    // Triple attack delays
    triple1: 200, triple2: 200, triple3: 200, triple4: 200, triple5: 200,
    triple6: 200, triple7: 200, triple8: 200, triple9: 200, triple10: 200,
    triple11: 200, triple12: 200, triple13: 200, triple14: 200, triple15: 200,
    triple16: 200, triple17: 200, triple18: 200, triple19: 200, triple20: 200,
    triple21: 200, triple22: 200, triple23: 200, triple24: 200, triple25: 200,
    triple26: 200, triple27: 200, triple28: 200, triple29: 200, triple30: 200,
    triple31: 200, triple32: 200, triple33: 200, triple34: 200, triple35: 200
};

// Minimum safe delays (for warning)
const MINIMUM_SAFE_DELAYS = {
    nc_attacks: 1000,
    messages: 1500,
    voice: 2000,
    group_changes: 5000,
    triple_nc: 500
};

function loadRoles() {
    try {
        if (fs.existsSync(ROLES_FILE)) {
            const data = fs.readFileSync(ROLES_FILE, 'utf8');
            return JSON.parse(data);
        }
    } catch (err) {
        console.log('[ROLES] Error loading roles, using defaults');
    }
    return { ...defaultRoles };
}

function saveRoles(roles) {
    try {
        if (!fs.existsSync('./data')) {
            fs.mkdirSync('./data', { recursive: true });
        }
        fs.writeFileSync(ROLES_FILE, JSON.stringify(roles, null, 2));
    } catch (err) {
        console.error('[ROLES] Error saving roles:', err.message);
    }
}

function loadDelays() {
    try {
        if (fs.existsSync(DELAYS_FILE)) {
            const data = fs.readFileSync(DELAYS_FILE, 'utf8');
            const loadedDelays = { ...defaultDelays, ...JSON.parse(data) };
            
            // Check for dangerously low delays and warn
            for (const [key, value] of Object.entries(loadedDelays)) {
                if (key.startsWith('triple') && value < MINIMUM_SAFE_DELAYS.triple_nc) {
                    console.warn(`⚠️  WARNING: ${key} delay is set to ${value}ms (RISKY - Minimum recommended: ${MINIMUM_SAFE_DELAYS.triple_nc}ms)`);
                } else if (key.startsWith('nc') && value < MINIMUM_SAFE_DELAYS.nc_attacks) {
                    console.warn(`⚠️  WARNING: ${key} delay is set to ${value}ms (RISKY - Minimum recommended: ${MINIMUM_SAFE_DELAYS.nc_attacks}ms)`);
                }
            }
            
            return loadedDelays;
        }
    } catch (err) {
        console.log('[DELAYS] Error loading delays, using defaults');
    }
    return { ...defaultDelays };
}

function saveDelays(delays) {
    try {
        if (!fs.existsSync('./data')) {
            fs.mkdirSync('./data', { recursive: true });
        }
        fs.writeFileSync(DELAYS_FILE, JSON.stringify(delays, null, 2));
    } catch (err) {
        console.error('[DELAYS] Error saving delays:', err.message);
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

// ========== EMOJI ARRAYS ==========
const emojiArrays = {
    // FACE EMOJIS (1-10)
    nc1: ['😀','😃','😄','😁','😆','😅','😂','🤣','😊','😇','🙂','🙃'],
    nc2: ['😉','😌','😍','🥰','😘','😗','😙','😚','😋','😛','😝','😜'],
    nc3: ['🤪','😎','🥸','🤓','🧐','🤯','🥳','😏','😒','😞','😔','😟'],
    nc4: ['😕','🙁','☹️','😣','😖','😫','😩','🥺','😢','😭','😤','😠'],
    nc5: ['😡','🤬','🤯','😳','🥵','🥶','😱','😨','😰','😥','😓','🤗'],
    nc6: ['🤔','🫣','🤭','🤫','🤥','😶','🫥','😐','🫤','😑','😬','🫨'],
    nc7: ['🙄','😯','😦','😧','😮','😲','🥱','😴','🤤','😪','😵','🤐'],
    nc8: ['🥴','😷','🤒','🤕','🤢','🤮','🤧','😇','🥳','🥸','😈','👿'],
    nc9: ['👹','👺','🤡','💩','👻','💀','☠️','👽','👾','🤖','🎃','😺'],
    nc10: ['😸','😹','😻','😼','😽','🙀','😿','😾','👋','🤚','🖐️','✋'],
    
    // HAND GESTURES (11-20)
    nc11: ['🖖','👌','🤌','🤏','✌️','🤞','🫰','🤟','🤘','🤙','🫵','🫲'],
    nc12: ['🫳','👈','👉','👆','🖕','👇','☝️','👍','👎','✊','👊','🤛'],
    nc13: ['🤜','👏','🙌','🫶','👐','🤲','🤝','🙏','✍️','💅','🤳','💪'],
    nc14: ['🦾','🦿','🦵','🦶','👂','🦻','👃','🧠','🫀','🫁','🦷','🦴'],
    nc15: ['👀','👁️','👅','👄','🫦','👶','🧒','👦','👧','🧑','👨','👩'],
    nc16: ['🧔','👨‍🦰','👩‍🦰','👨‍🦱','👩‍🦱','👨‍🦳','👩‍🦳','👨‍🦲','👩‍🦲','🧑‍🦰','🧑‍🦱','🧑‍🦳'],
    nc17: ['🧑‍🦲','👱','👱‍♀️','🧓','👴','👵','🙍','🙍‍♂️','🙍‍♀️','🙎','🙎‍♂️','🙎‍♀️'],
    nc18: ['🙅','🙅‍♂️','🙅‍♀️','🙆','🙆‍♂️','🙆‍♀️','💁','💁‍♂️','💁‍♀️','🙋','🙋‍♂️','🙋‍♀️'],
    nc19: ['🧏','🧏‍♂️','🧏‍♀️','🙇','🙇‍♂️','🙇‍♀️','🤦','🤦‍♂️','🤦‍♀️','🤷','🤷‍♂️','🤷‍♀️'],
    nc20: ['👮','👮‍♂️','👮‍♀️','🕵️','🕵️‍♂️','🕵️‍♀️','💂','💂‍♂️','💂‍♀️','🥷','👷','👷‍♂️'],
    
    // PEOPLE & PROFESSIONS (21-30)
    nc21: ['👷‍♀️','👨‍⚕️','👩‍⚕️','👨‍🎓','👩‍🎓','👨‍🏫','👩‍🏫','👨‍⚖️','👩‍⚖️','👨‍🌾','👩‍🌾','👨‍🍳'],
    nc22: ['👩‍🍳','👨‍🔧','👩‍🔧','👨‍🏭','👩‍🏭','👨‍💼','👩‍💼','👨‍🔬','👩‍🔬','👨‍💻','👩‍💻','👨‍🎤'],
    nc23: ['👩‍🎤','👨‍🎨','👩‍🎨','👨‍✈️','👩‍✈️','👨‍🚀','👩‍🚀','👨‍🚒','👩‍🚒','👮','🕵️','💂'],
    nc24: ['👷','🤴','👸','👳','👳‍♂️','👳‍♀️','🧕','👲','🧔‍♀️','🤵','🤵‍♂️','🤵‍♀️'],
    nc25: ['👰','👰‍♂️','👰‍♀️','🤰','🫃','🫄','🤱','👼','🎅','🤶','🦸','🦸‍♂️'],
    nc26: ['🦸‍♀️','🦹','🦹‍♂️','🦹‍♀️','🧙','🧙‍♂️','🧙‍♀️','🧚','🧚‍♂️','🧚‍♀️','🧛','🧛‍♂️'],
    nc27: ['🧛‍♀️','🧜','🧜‍♂️','🧜‍♀️','🧝','🧝‍♂️','🧝‍♀️','🧞','🧞‍♂️','🧞‍♀️','🧟','🧟‍♂️'],
    nc28: ['🧟‍♀️','💆','💆‍♂️','💆‍♀️','💇','💇‍♂️','💇‍♀️','🚶','🚶‍♂️','🚶‍♀️','🏃','🏃‍♂️'],
    nc29: ['🏃‍♀️','💃','🕺','🕴️','👯','👯‍♂️','👯‍♀️','🧖','🧖‍♂️','🧖‍♀️','🧗','🧗‍♂️'],
    nc30: ['🧗‍♀️','🏇','🏂','🏌️','🏌️‍♂️','🏌️‍♀️','🏄','🏄‍♂️','🏄‍♀️','🚣','🚣‍♂️','🚣‍♀️'],
    
    // SPORTS & ACTIVITIES (31-40)
    nc31: ['🏊','🏊‍♂️','🏊‍♀️','⛹️','⛹️‍♂️','⛹️‍♀️','🏋️','🏋️‍♂️','🏋️‍♀️','🚴','🚴‍♂️','🚴‍♀️'],
    nc32: ['🚵','🚵‍♂️','🚵‍♀️','🤸','🤸‍♂️','🤸‍♀️','🤼','🤼‍♂️','🤼‍♀️','🤽','🤽‍♂️','🤽‍♀️'],
    nc33: ['🤾','🤾‍♂️','🤾‍♀️','🤺','🤹','🤹‍♂️','🤹‍♀️','🧘','🧘‍♂️','🧘‍♀️','🛀','🛌'],
    nc34: ['🧑‍🤝‍🧑','👭','👫','👬','💏','👩‍❤️‍💋‍👨','👨‍❤️‍💋‍👨','👩‍❤️‍💋‍👩','💑','👩‍❤️‍👨','👨‍❤️‍👨','👩‍❤️‍👩'],
    nc35: ['👨‍👩‍👦','👨‍👩‍👧','👨‍👩‍👧‍👦','👨‍👩‍👦‍👦','👨‍👩‍👧‍👧','👨‍👨‍👦','👨‍👨‍👧','👨‍👨‍👧‍👦','👨‍👨‍👦‍👦','👨‍👨‍👧‍👧','👩‍👩‍👦','👩‍👩‍👧'],
    nc36: ['👩‍👩‍👧‍👦','👩‍👩‍👦‍👦','👩‍👩‍👧‍👧','👨‍👦','👨‍👦‍👦','👨‍👧','👨‍👧‍👦','👨‍👧‍👧','👩‍👦','👩‍👦‍👦','👩‍👧','👩‍👧‍👦'],
    nc37: ['👩‍👧‍👧','🗣️','👤','👥','🫂','👣','🐵','🐒','🦍','🦧','🐶','🐕'],
    nc38: ['🐩','🐺','🦊','🦝','🐱','🐈','🦁','🐯','🐅','🐆','🐴','🐎'],
    nc39: ['🦄','🦓','🦌','🐮','🐂','🐃','🐄','🐷','🐖','🐗','🐽','🐏'],
    nc40: ['🐑','🐐','🐪','🐫','🦙','🦒','🐘','🦏','🦛','🐭','🐁','🐀'],
    
    // ANIMALS (41-50)
    nc41: ['🐹','🐰','🐇','🐿️','🦫','🦔','🦇','🐻','🐨','🐼','🦥','🦦'],
    nc42: ['🦨','🦘','🦡','🐾','🦃','🐔','🐓','🐣','🐤','🐥','🐦','🐧'],
    nc43: ['🕊️','🦅','🦆','🦢','🦉','🦤','🪶','🦩','🦚','🦜','🐸','🐊'],
    nc44: ['🐢','🦎','🐍','🐲','🐉','🦕','🦖','🐳','🐋','🐬','🦭','🐟'],
    nc45: ['🐠','🐡','🦈','🐙','🐚','🪸','🐌','🦋','🐛','🐜','🐝','🪲'],
    nc46: ['🐞','🦗','🕷️','🕸️','🦂','🦟','🪳','🪰','🪱','🦠','💐','🌸'],
    nc47: ['💮','🪷','🏵️','🌹','🥀','🌺','🌻','🌼','🌷','🌱','🪴','🌲'],
    nc48: ['🌳','🌴','🌵','🌾','🌿','☘️','🍀','🍁','🍂','🍃','🪹','🪺'],
    nc49: ['🍄','🍇','🍈','🍉','🍊','🍋','🍌','🍍','🥭','🍎','🍏','🍐'],
    nc50: ['🍑','🍒','🍓','🫐','🥝','🍅','🫒','🥥','🥑','🍆','🥔','🥕'],
    
    // FOOD & DRINK (51-60)
    nc51: ['🌽','🌶️','🫑','🥒','🥬','🥦','🧄','🧅','🍄','🥜','🫘','🌰'],
    nc52: ['🍞','🥐','🥖','🫓','🥨','🥯','🥞','🧇','🧀','🍖','🍗','🥩'],
    nc53: ['🥓','🍔','🍟','🍕','🌭','🥪','🌮','🌯','🫔','🥙','🧆','🥚'],
    nc54: ['🍳','🥘','🍲','🫕','🥣','🥗','🍿','🧈','🧂','🥫','🍝','🍜'],
    nc55: ['🍠','🍢','🍣','🍤','🍥','🥮','🍡','🥟','🥠','🥡','🦪','🍦'],
    nc56: ['🍧','🍨','🍩','🍪','🎂','🍰','🧁','🥧','🍫','🍬','🍭','🍮'],
    nc57: ['🍯','🍼','🥛','☕','🫖','🍵','🍶','🍾','🍷','🍸','🍹','🍺'],
    nc58: ['🍻','🥂','🥃','🥤','🧋','🧃','🧉','🧊','🥢','🍽️','🍴','🥄'],
    nc59: ['🔪','🏺','🌍','🌎','🌏','🌐','🗺️','🗾','🧭','🏔️','⛰️','🌋'],
    nc60: ['🗻','🏕️','🏖️','🏜️','🏝️','🏞️','🏟️','🏛️','🏗️','🧱','🪨','🪵'],
    
    // TRAVEL & PLACES (61-70)
    nc61: ['🛖','🏘️','🏚️','🏠','🏡','🏢','🏣','🏤','🏥','🏦','🏨','🏩'],
    nc62: ['🏪','🏫','🏬','🏭','🏯','🏰','💒','🗼','🗽','⛪','🕌','🛕'],
    nc63: ['🕍','⛩️','🕋','⛲','⛺','🌁','🌃','🏙️','🌄','🌅','🌆','🌇'],
    nc64: ['🌉','♨️','🎠','🎡','🎢','💈','🎪','🚂','🚃','🚄','🚅','🚆'],
    nc65: ['🚇','🚈','🚉','🚊','🚝','🚞','🚋','🚌','🚍','🚎','🚐','🚑'],
    nc66: ['🚒','🚓','🚔','🚕','🚖','🚗','🚘','🚙','🛻','🚚','🚛','🚜'],
    nc67: ['🏎️','🏍️','🛵','🛺','🚲','🛴','🚏','🛣️','🛤️','🛢️','⛽','🚨'],
    nc68: ['🚥','🚦','🛑','🚧','⚓','⛵','🛶','🚤','🛳️','⛴️','🛥️','🚢'],
    nc69: ['✈️','🛩️','🛫','🛬','🪂','💺','🚁','🚟','🚠','🚡','🛰️','🚀'],
    nc70: ['🛸','🪐','🌠','🌌','⛱️','🧨','🎆','🎇','🎑','✨','🎈','🎉'],
    
    // OBJECTS & SYMBOLS (71-80)
    nc71: ['🎊','🎋','🎍','🎎','🎏','🎐','🎀','🎁','🤿','🪀','🪁','🧿'],
    nc72: ['🎫','🎟️','🎖️','🏆','🏅','🥇','🥈','🥉','⚽','⚾','🥎','🏀'],
    nc73: ['🏐','🏈','🏉','🎾','🥏','🎳','🏏','🏑','🏒','🥍','🏓','🏸'],
    nc74: ['🥊','🥋','🥅','⛳','⛸️','🎣','🤿','🎽','🎿','🛷','🥌','🎯'],
    nc75: ['🪀','🪃','🥏','🎱','🔮','🧿','🪄','🎮','🎰','🎲','🧩','🧸'],
    nc76: ['🪅','🪆','♠️','♥️','♦️','♣️','♟️','🃏','🀄','🎴','🎭','🖼️'],
    nc77: ['🎨','🧵','🪡','🧶','🪢','👓','🕶️','🥽','🥼','🦺','👔','👕'],
    nc78: ['👖','🧣','🧤','🧥','🧦','👗','👘','🥻','🩱','🩲','🩳','👙'],
    nc79: ['👚','👛','👜','👝','🎒','🩴','👞','👟','🥾','🥿','👠','👡'],
    nc80: ['🩰','👢','👑','👒','🎩','🎓','🧢','🪖','⛑️','💄','💍','💼'],
    
    // PHONE & TECH (81-90)
    nc81: ['📱','📲','☎️','📞','📟','📠','🔋','🔌','💻','🖥️','🖨️','⌨️'],
    nc82: ['🖱️','🖲️','💽','💾','💿','📀','🧮','🎥','📽️','🎬','📺','📷'],
    nc83: ['📸','📹','📼','🔍','🔎','🕯️','💡','🔦','🏮','🪔','📔','📕'],
    nc84: ['📖','🗂️','📂','📅','📆','🗒️','📊','📈','📉','🗃️','🗄️','🗑️'],
    nc85: ['🔒','🔓','🔏','🔐','🔑','🗝️','🔨','🪓','⛏️','⚒️','🛠️','🗡️'],
    nc86: ['⚔️','🔫','🏹','🛡️','🔧','🔩','⚙️','🗜️','⚖️','🦯','🔗','⛓️'],
    nc87: ['🧰','🧲','⚗️','🧪','🧫','🧬','🔬','🔭','📡','💉','🩸','💊'],
    nc88: ['🩹','🩺','🚪','🛏️','🛋️','🪑','🚽','🚿','🛁','🧴','🧷','🧹'],
    nc89: ['🧺','🧻','🪣','🧼','🪥','🧽','🧯','🛒','🚬','⚰️','🪦','⚱️'],
    nc90: ['🏧','🚮','🚰','♿','🚹','🚺','🚻','🚼','🚾','🛂','🛃','🛄'],
    
    // SYMBOLS & SIGNS (91-100)
    nc91: ['🛅','⚠️','🚸','⛔','🚫','🚳','🚭','🚯','🚱','🚷','📵','🔞'],
    nc92: ['☢️','☣️','⬆️','↗️','➡️','↘️','⬇️','↙️','⬅️','↖️','↕️','↔️'],
    nc93: ['↩️','↪️','⤴️','⤵️','🔃','🔄','🔙','🔚','🔛','🔜','🔝','🛐'],
    nc94: ['⚛️','🕉️','✡️','☸️','☪️','✝️','☦️','☮️','🕎','🔯','♈','♉'],
    nc95: ['♊','♋','♌','♍','♎','♏','♐','♑','♒','♓','⛎','🔀'],
    nc96: ['🔁','🔂','▶️','⏩','⏭️','⏯️','◀️','⏪','⏮️','🔼','⏫','🔽'],
    nc97: ['⏬','⏸️','⏹️','⏺️','⏏️','🎦','🔅','🔆','📶','📳','📴','♀️'],
    nc98: ['♂️','⚧️','✖️','➕','➖','➗','♾️','‼️','⁉️','❓','❔','❕'],
    nc99: ['❗','〰️','💱','💲','⚕️','♻️','⚜️','🔱','📛','🔰','⭕','🟠'],
    nc100: ['🟡','🟢','🔵','🟣','🟤','⚫','⚪','🟥','🟧','🟨','🟩','🟦']
};

// ========== FONT STYLES FOR TEXT ==========
const fontStyles = {
    // DOUBLE STRIKE/BOLD FONTS
    double: {
        name: "Double Strike",
        chars: {
            'A': '𝔸', 'B': '𝔹', 'C': 'ℂ', 'D': '𝔻', 'E': '𝔼', 'F': '𝔽', 'G': '𝔾',
            'H': 'ℍ', 'I': '𝕀', 'J': '𝕁', 'K': '𝕂', 'L': '𝕃', 'M': '𝕄', 'N': 'ℕ',
            'O': '𝕆', 'P': 'ℙ', 'Q': 'ℚ', 'R': 'ℝ', 'S': '𝕊', 'T': '𝕋', 'U': '𝕌',
            'V': '𝕍', 'W': '𝕎', 'X': '𝕏', 'Y': '𝕐', 'Z': 'ℤ',
            'a': '𝕒', 'b': '𝕓', 'c': '𝕔', 'd': '𝕕', 'e': '𝕖', 'f': '𝕗', 'g': '𝕘',
            'h': '𝕙', 'i': '𝕚', 'j': '𝕛', 'k': '𝕜', 'l': '𝕝', 'm': '𝕞', 'n': '𝕟',
            'o': '𝕠', 'p': '𝕡', 'q': '𝕢', 'r': '𝕣', 's': '𝕤', 't': '𝕥', 'u': '𝕦',
            'v': '𝕧', 'w': '𝕨', 'x': '𝕩', 'y': '𝕪', 'z': '𝕫',
            '0': '𝟘', '1': '𝟙', '2': '𝟚', '3': '𝟛', '4': '𝟜', '5': '𝟝', '6': '𝟞',
            '7': '𝟟', '8': '𝟠', '9': '𝟡'
        }
    },
    
    // MONOSPACE/BLOCK FONTS
    mono: {
        name: "Monospace",
        chars: {
            'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶',
            'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽',
            'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃', 'U': '𝚄',
            'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉',
            'a': '𝚊', 'b': '𝚋', 'c': '𝚌', 'd': '𝚍', 'e': '𝚎', 'f': '𝚏', 'g': '𝚐',
            'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕', 'm': '𝚖', 'n': '𝚗',
            'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛', 's': '𝚜', 't': '𝚝', 'u': '𝚞',
            'v': '𝚟', 'w': '𝚠', 'x': '𝚡', 'y': '𝚢', 'z': '𝚣',
            '0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺', '5': '𝟻', '6': '𝟼',
            '7': '𝟽', '8': '𝟾', '9': '𝟿'
        }
    },
    
    // SCRIPT/CURSIVE FONTS
    script: {
        name: "Script",
        chars: {
            'A': '𝒜', 'B': '𝐵', 'C': '𝒞', 'D': '𝒟', 'E': '𝐸', 'F': '𝐹', 'G': '𝒢',
            'H': '𝐻', 'I': '𝐼', 'J': '𝒥', 'K': '𝒦', 'L': '𝐿', 'M': '𝑀', 'N': '𝒩',
            'O': '𝒪', 'P': '𝒫', 'Q': '𝒬', 'R': '𝑅', 'S': '𝒮', 'T': '𝒯', 'U': '𝒰',
            'V': '𝒱', 'W': '𝒲', 'X': '𝒳', 'Y': '𝒴', 'Z': '𝒵',
            'a': '𝒶', 'b': '𝒷', 'c': '𝒸', 'd': '𝒹', 'e': '𝑒', 'f': '𝒻', 'g': 'ℊ',
            'h': '𝒽', 'i': '𝒾', 'j': '𝒿', 'k': '𝓀', 'l': '𝓁', 'm': '𝓂', 'n': '𝓃',
            'o': '𝑜', 'p': '𝓅', 'q': '𝓆', 'r': '𝓇', 's': '𝓈', 't': '𝓉', 'u': '𝓊',
            'v': '𝓋', 'w': '𝓌', 'x': '𝓍', 'y': '𝓎', 'z': '𝓏'
        }
    },
    
    // BOLD SCRIPT FONTS
    boldscript: {
        name: "Bold Script",
        chars: {
            'A': '𝓐', 'B': '𝓑', 'C': '𝓒', 'D': '𝓓', 'E': '𝓔', 'F': '𝓕', 'G': '𝓖',
            'H': '𝓗', 'I': '𝓘', 'J': '𝓙', 'K': '𝓚', 'L': '𝓛', 'M': '𝓜', 'N': '𝓝',
            'O': '𝓞', 'P': '𝓟', 'Q': '𝓠', 'R': '𝓡', 'S': '𝓢', 'T': '𝓣', 'U': '𝓤',
            'V': '𝓥', 'W': '𝓦', 'X': '𝓧', 'Y': '𝓨', 'Z': '𝓩',
            'a': '𝓪', 'b': '𝓫', 'c': '𝓬', 'd': '𝓭', 'e': '𝓮', 'f': '𝓯', 'g': '𝓰',
            'h': '𝓱', 'i': '𝓲', 'j': '𝓳', 'k': '𝓴', 'l': '𝓵', 'm': '𝓶', 'n': '𝓷',
            'o': '𝓸', 'p': '𝓹', 'q': '𝓺', 'r': '𝓻', 's': '𝓼', 't': '𝓽', 'u': '𝓾',
            'v': '𝓿', 'w': '𝔀', 'x': '𝔁', 'y': '𝔂', 'z': '𝔃'
        }
    },
    
    // GOTHIC/BLACKLETTER FONTS
    gothic: {
        name: "Gothic",
        chars: {
            'A': '𝔄', 'B': '𝔅', 'C': 'ℭ', 'D': '𝔇', 'E': '𝔈', 'F': '𝔉', 'G': '𝔊',
            'H': 'ℌ', 'I': 'ℑ', 'J': '𝔍', 'K': '𝔎', 'L': '𝔏', 'M': '𝔐', 'N': '𝔑',
            'O': '𝔒', 'P': '𝔓', 'Q': '𝔔', 'R': 'ℜ', 'S': '𝔖', 'T': '𝔗', 'U': '𝔘',
            'V': '𝔙', 'W': '𝔚', 'X': '𝔛', 'Y': '𝔜', 'Z': 'ℨ'
        }
    },
    
    // BOLD GOTHIC FONTS
    boldgothic: {
        name: "Bold Gothic",
        chars: {
            'A': '𝕬', 'B': '𝕭', 'C': '𝕮', 'D': '𝕯', 'E': '𝕰', 'F': '𝕱', 'G': '𝕲',
            'H': '𝕳', 'I': '𝕴', 'J': '𝕵', 'K': '𝕶', 'L': '𝕷', 'M': '𝕸', 'N': '𝕹',
            'O': '𝕺', 'P': '𝕻', 'Q': '𝕼', 'R': '𝕽', 'S': '𝕾', 'T': '𝕿', 'U': '𝖀',
            'V': '𝖁', 'W': '𝖂', 'X': '𝖃', 'Y': '𝖄', 'Z': '𝖅',
            'a': '𝖆', 'b': '𝖇', 'c': '𝖈', 'd': '𝖉', 'e': '𝖊', 'f': '𝖋', 'g': '𝖌',
            'h': '𝖍', 'i': '𝖎', 'j': '𝖏', 'k': '𝖐', 'l': '𝖑', 'm': '𝖒', 'n': '𝖓',
            'o': '𝖔', 'p': '𝖕', 'q': '𝖖', 'r': '𝖗', 's': '𝖘', 't': '𝖙', 'u': '𝖚',
            'v': '𝖛', 'w': '𝖜', 'x': '𝖝', 'y': '𝖞', 'z': '𝖟'
        }
    },
    
    // SQUARE/FULLWIDTH FONTS
    square: {
        name: "Square",
        chars: {
            'A': 'Ａ', 'B': 'Ｂ', 'C': 'Ｃ', 'D': 'Ｄ', 'E': 'Ｅ', 'F': 'Ｆ', 'G': 'Ｇ',
            'H': 'Ｈ', 'I': 'Ｉ', 'J': 'Ｊ', 'K': 'Ｋ', 'L': 'Ｌ', 'M': 'Ｍ', 'N': 'Ｎ',
            'O': 'Ｏ', 'P': 'Ｐ', 'Q': 'Ｑ', 'R': 'Ｒ', 'S': 'Ｓ', 'T': 'Ｔ', 'U': 'Ｕ',
            'V': 'Ｖ', 'W': 'Ｗ', 'X': 'Ｘ', 'Y': 'Ｙ', 'Z': 'Ｚ',
            'a': 'ａ', 'b': 'ｂ', 'c': 'ｃ', 'd': 'ｄ', 'e': 'ｅ', 'f': 'ｆ', 'g': 'ｇ',
            'h': 'ｈ', 'i': 'ｉ', 'j': 'ｊ', 'k': 'ｋ', 'l': 'ｌ', 'm': 'ｍ', 'n': 'ｎ',
            'o': 'ｏ', 'p': 'ｐ', 'q': 'ｑ', 'r': 'ｒ', 's': 'ｓ', 't': 'ｔ', 'u': 'ｕ',
            'v': 'ｖ', 'w': 'ｗ', 'x': 'ｘ', 'y': 'ｙ', 'z': 'ｚ',
            '0': '０', '1': '１', '2': '２', '3': '３', '4': '４', '5': '５', '6': '６',
            '7': '７', '8': '８', '9': '９'
        }
    },
    
    // CIRCLED FONTS
    circled: {
        name: "Circled",
        chars: {
            'A': 'Ⓐ', 'B': 'Ⓑ', 'C': 'Ⓒ', 'D': 'Ⓓ', 'E': 'Ⓔ', 'F': 'Ⓕ', 'G': 'Ⓖ',
            'H': 'Ⓗ', 'I': 'Ⓘ', 'J': 'Ⓙ', 'K': 'Ⓚ', 'L': 'Ⓛ', 'M': 'Ⓜ', 'N': 'Ⓝ',
            'O': 'Ⓞ', 'P': 'Ⓟ', 'Q': 'Ⓠ', 'R': 'Ⓡ', 'S': 'Ⓢ', 'T': 'Ⓣ', 'U': 'Ⓤ',
            'V': 'Ⓥ', 'W': 'Ⓦ', 'X': 'Ⓧ', 'Y': 'Ⓨ', 'Z': 'Ⓩ',
            'a': 'ⓐ', 'b': 'ⓑ', 'c': 'ⓒ', 'd': 'ⓓ', 'e': 'ⓔ', 'f': 'ⓕ', 'g': 'ⓖ',
            'h': 'ⓗ', 'i': 'ⓘ', 'j': 'ⓙ', 'k': 'ⓚ', 'l': 'ⓛ', 'm': 'ⓜ', 'n': 'ⓝ',
            'o': 'ⓞ', 'p': 'ⓟ', 'q': 'ⓠ', 'r': 'ⓡ', 's': 'ⓢ', 't': 'ⓣ', 'u': 'ⓤ',
            'v': 'ⓥ', 'w': 'ⓦ', 'x': 'ⓧ', 'y': 'ⓨ', 'z': 'ⓩ',
            '0': '⓪', '1': '①', '2': '②', '3': '③', '4': '④', '5': '⑤', '6': '⑥',
            '7': '⑦', '8': '⑧', '9': '⑨'
        }
    }
};

// Function to convert text to a specific font style
function convertToFont(text, fontName) {
    const font = fontStyles[fontName];
    if (!font) return text;
    
    return text.split('').map(char => {
        const upperChar = char.toUpperCase();
        const lowerChar = char.toLowerCase();
        
        if (font.chars[upperChar]) {
            return char === upperChar ? font.chars[upperChar] : font.chars[lowerChar] || font.chars[upperChar] || char;
        }
        return font.chars[char] || char;
    }).join('');
}

// ========== TRIPLE ATTACK DEFINITIONS ==========
const tripleNcCombos = {
    // Format: tripleName: [nc1, nc2, nc3] - Each runs as separate attack
    triple1: ['nc1', 'nc2', 'nc3'],
    triple2: ['nc4', 'nc5', 'nc6'],
    triple3: ['nc7', 'nc8', 'nc9'],
    triple4: ['nc10', 'nc11', 'nc12'],
    triple5: ['nc13', 'nc14', 'nc15'],
    triple6: ['nc16', 'nc17', 'nc18'],
    triple7: ['nc19', 'nc20', 'nc21'],
    triple8: ['nc22', 'nc23', 'nc24'],
    triple9: ['nc25', 'nc26', 'nc27'],
    triple10: ['nc28', 'nc29', 'nc30'],
    
    // PHONE KEYBOARD TRIPLE ATTACKS
    triple11: ['nc81', 'nc82', 'nc83'],
    triple12: ['nc84', 'nc85', 'nc86'],
    triple13: ['nc87', 'nc88', 'nc89'],
    triple14: ['nc90', 'nc91', 'nc92'],
    triple15: ['nc93', 'nc94', 'nc95'],
    
    // FACE ATTACKS
    triple16: ['nc1', 'nc4', 'nc7'],
    triple17: ['nc2', 'nc5', 'nc8'],
    triple18: ['nc3', 'nc6', 'nc9'],
    
    // HAND ATTACKS
    triple19: ['nc11', 'nc12', 'nc13'],
    
    // FOOD ATTACKS
    triple20: ['nc50', 'nc51', 'nc52'],
    triple21: ['nc53', 'nc54', 'nc55'],
    triple22: ['nc56', 'nc57', 'nc58'],
    
    // TRAVEL ATTACKS
    triple23: ['nc64', 'nc65', 'nc66'],
    triple24: ['nc67', 'nc68', 'nc69'],
    
    // SPORTS ATTACKS
    triple25: ['nc72', 'nc73', 'nc74'],
    
    // CLOTHING ATTACKS
    triple26: ['nc77', 'nc78', 'nc79'],
    
    // SYMBOL ATTACKS
    triple27: ['nc93', 'nc97', 'nc99'],
    triple28: ['nc94', 'nc95', 'nc96'],
    triple29: ['nc98', 'nc99', 'nc100'],
    
    // MIXED ATTACKS
    triple30: ['nc31', 'nc41', 'nc71'],
    triple31: ['nc20', 'nc40', 'nc60'],
    triple32: ['nc35', 'nc45', 'nc55'],
    triple33: ['nc25', 'nc35', 'nc45'],
    triple34: ['nc15', 'nc25', 'nc35'],
    triple35: ['nc5', 'nc15', 'nc25']
};

// ========== UPDATED THUNDER MENU ==========
const thunderMenu = `
╔══════════════════════════════════════════════╗
║         ⚡⚡⚡ ROCKY WP GOD v3.0 ⚡⚡⚡         ║
║       ⚡ TRIPLE NC ATTACK SYSTEM ⚡          ║
╠══════════════════════════════════════════════╣
║  👑 ADMIN COMMANDS                           ║
╠══════════════════════════════════════════════╣
║  +admin      → Become admin (DM)             ║
║  -admin      → Remove yourself               ║
║  +sub        → Make sub-admin (reply)        ║
║  -sub        → Remove sub-admin              ║
╠══════════════════════════════════════════════╣
║  🤖 BOT MANAGEMENT                           ║
╠══════════════════════════════════════════════╣
║  +add [num]  → Add new bot                   ║
║  +bots       → List all bots                 ║
║  +ping       → Check bot latency             ║
╠══════════════════════════════════════════════╣
║  ⚡ TEXT + EMOJI ATTACKS (NEW!) ⚡           ║
╠══════════════════════════════════════════════╣
║  +tne [font] [nc#] [text] [delay]           ║
║  Fonts: double, mono, script, boldscript    ║
║          gothic, boldgothic, square, circled║
║  Example: +tne double nc1 RAID 1000         ║
║  Example: +tne script nc50 HELLO 1500       ║
║  +fonts       → Show available fonts        ║
║  -tne         → Stop text+emoji attacks     ║
╠══════════════════════════════════════════════╣
║  ⚡ TRIPLE NC ATTACKS (35 Types) ⚡          ║
╠══════════════════════════════════════════════╣
║  +triple1 [text]  → Starts: nc1 + nc2 + nc3  ║
║  +triple2 [text]  → Starts: nc4 + nc5 + nc6  ║
║  +triple3 [text]  → Starts: nc7 + nc8 + nc9  ║
║  +triple4 [text]  → Starts: nc10+nc11+nc12   ║
║  +triple5 [text]  → Starts: nc13+nc14+nc15   ║
║  ... up to +triple35                        ║
╠══════════════════════════════════════════════╣
║  DELAY CONTROLS                             ║
╠══════════════════════════════════════════════╣
║  +delaytriple[1-35] [ms] → Set triple delay ║
║  +delaync[1-100] [ms]    → Set NC delay     ║
║  +delays                → Show all delays   ║
╠══════════════════════════════════════════════╣
║  ⚡ INDIVIDUAL NC ATTACKS (100 Types) ⚡    ║
╠══════════════════════════════════════════════╣
║  +nc1 to +nc100 [text] → Single NC attacks  ║
║  -nc                   → Stop NC attacks    ║
╠══════════════════════════════════════════════╣
║  💬 MESSAGE ATTACKS                        ║
╠══════════════════════════════════════════════╣
║  +s [text] [delay]  → Slide attack         ║
║  -s                 → Stop slides          ║
║  +txt [text] [delay]→ Text spam            ║
║  -txt               → Stop text            ║
╠══════════════════════════════════════════════╣
║  🎤 TTS VOICE ATTACKS                      ║
╠══════════════════════════════════════════════╣
║  +tts [text]        → Send voice           ║
║  +ttsatk [text] [delay] → Voice spam       ║
║  -ttsatk            → Stop voice           ║
╠══════════════════════════════════════════════╣
║  📸 PICTURE ATTACKS                        ║
╠══════════════════════════════════════════════╣
║  +pic [delay]       → Pic spam             ║
║                      (reply to pic)         ║
║  -pic               → Stop pic             ║
╠══════════════════════════════════════════════╣
║  🛑 STOP ALL                               ║
╠══════════════════════════════════════════════╣
║  -all        → Stop all attacks            ║
╠══════════════════════════════════════════════╣
║  📋 INFO                                   ║
╠══════════════════════════════════════════════╣
║  +menu       → Show this menu              ║
║  +status     → Active attacks              ║
║  +delays     → Show current delays         ║
║  +triples    → List triple combos          ║
║  +fonts      → Show all font styles        ║
╠══════════════════════════════════════════════╣
║       ⚡ ULTIMATE POWER ⚡                   ║
╚══════════════════════════════════════════════╝
`;

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const question = (text) => new Promise((resolve) => rl.question(text, resolve));

async function generateTTS(text, lang = 'en') {
    return new Promise((resolve, reject) => {
        const tts = gtts(lang);
        const chunks = [];
        
        tts.stream(text).on('data', (chunk) => {
            chunks.push(chunk);
        }).on('end', () => {
            resolve(Buffer.concat(chunks));
        }).on('error', (err) => {
            reject(err);
        });
    });
}

// ========== CLASS DEFINITIONS ==========
class CommandBus {
    constructor() {
        this.botSessions = new Map();
        this.processedMessages = new Map();
        this.messageCleanupInterval = 60000;
        
        setInterval(() => {
            const now = Date.now();
            this.processedMessages.forEach((timestamp, msgId) => {
                if (now - timestamp > this.messageCleanupInterval) {
                    this.processedMessages.delete(msgId);
                }
            });
        }, this.messageCleanupInterval);
    }

    registerBot(botId, session) {
        this.botSessions.set(botId, session);
    }

    unregisterBot(botId) {
        this.botSessions.delete(botId);
    }

    shouldProcessMessage(msgId) {
        if (this.processedMessages.has(msgId)) {
            return false;
        }
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
                console.error(`[${bot.botId}] Command execution error:`, err.message);
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
        this.activeSlides = new Map();
        this.activeTxtSenders = new Map();
        this.activeTTSSenders = new Map();
        this.activePicSenders = new Map();
        this.activeTextEmojiAttacks = new Map(); // NEW: For text+emoji attacks
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
                keepAliveIntervalMs: 30000,
                emitOwnEvents: true,
                fireInitQueries: true,
                generateHighQualityLinkPreview: false,
                syncFullHistory: false,
                markOnlineOnConnect: false
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
                                    text: `🤖 *${this.botId} PAIRING CODE* 🤖\n\n` +
                                          `╔══════════════════════════════════╗\n` +
                                          `║      YOUR PAIRING CODE IS:       ║\n` +
                                          `╠══════════════════════════════════╣\n` +
                                          `║          ${code}              ║\n` +
                                          `╠══════════════════════════════════╣\n` +
                                          `║  Go to WhatsApp > Linked Devices ║\n` +
                                          `║  > Link a Device > Link with     ║\n` +
                                          `║  phone number instead            ║\n` +
                                          `╚══════════════════════════════════╝\n\n` +
                                          `📱 Number: ${this.phoneNumber}`
                                });
                            }
                        } else {
                            console.log(`\n╔══════════════════════════════════╗`);
                            console.log(`║   ${this.botId} PAIRING CODE        ║`);
                            console.log(`╠══════════════════════════════════╣`);
                            console.log(`║          ${code}              ║`);
                            console.log(`╠══════════════════════════════════╣`);
                            console.log(`║  Go to WhatsApp > Linked Devices ║`);
                            console.log(`║  > Link a Device > Link with     ║`);
                            console.log(`║  phone number instead            ║`);
                            console.log(`╚══════════════════════════════════╝\n`);
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
                    console.log(`[${this.botId}] ✅ CONNECTED!`);
                    this.connected = true;
                    this.botNumber = this.sock.user.id.split(':')[0] + '@s.whatsapp.net';
                    console.log(`[${this.botId}] Number:`, this.botNumber);
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
            
            const messageType = Object.keys(msg.message)[0];
            if (messageType === 'protocolMessage' || messageType === 'senderKeyDistributionMessage') return;

            const from = msg.key.remoteJid;
            const isGroup = from.endsWith('@g.us');
            const sender = isGroup ? msg.key.participant : from;
            
            const msgId = msg.key.id;
            const isLeader = this.botManager.commandBus.getLeaderBot()?.botId === this.botId;
            
            if (!isLeader && !this.botManager.commandBus.shouldProcessMessage(msgId)) {
                return;
            }
            
            if (isLeader) {
                if (!this.botManager.commandBus.shouldProcessMessage(msgId)) {
                    return;
                }
            }
            
            // Update slide messages
            this.activeSlides.forEach((task, taskId) => {
                if (task.active && task.groupJid === from && task.targetJid === sender) {
                    task.latestMsg = msg;
                    task.hasNewMsg = true;
                }
            });
            
            let text = msg.message.conversation || 
                      msg.message.extendedTextMessage?.text || 
                      msg.message.imageMessage?.caption || '';

            const originalText = text;
            text = text.trim().toLowerCase();

            console.log(`[${this.botId}] MSG from ${sender}: ${text}`);

            const isDM = !isGroup;
            const senderIsAdmin = isAdmin(sender);
            const senderIsSubAdmin = isGroup ? isSubAdmin(sender, from) : false;
            const senderHasPermission = senderIsAdmin || senderIsSubAdmin;

            // ADMIN COMMANDS
            if (isDM && text === '+admin') {
                if (roles.admins.length === 0) {
                    addAdmin(sender);
                    await this.sendMessage(from, `⚡ *THUNDER ${this.botId}* ⚡\n\n✅ You are now the ADMIN!\n\nSend *+menu* to see commands`);
                    console.log(`[${this.botId}] New admin:`, sender);
                } else if (senderIsAdmin) {
                    await this.sendMessage(from, `⚠️ You are already the admin! - ${this.botId}`);
                } else {
                    await this.sendMessage(from, `❌ Admin already exists! Only one admin allowed. - ${this.botId}`);
                }
                return;
            }

            if (isDM && text === '-admin') {
                if (senderIsAdmin) {
                    removeAdmin(sender);
                    await this.sendMessage(from, `✅ You are no longer an admin! - ${this.botId}`);
                    console.log(`[${this.botId}] Removed admin:`, sender);
                } else {
                    await this.sendMessage(from, `⚠️ You are not an admin! - ${this.botId}`);
                }
                return;
            }

            if (isGroup && text === '+sub' && senderIsAdmin) {
                if (!msg.message.extendedTextMessage?.contextInfo?.participant) {
                    await this.sendMessage(from, `❌ Reply to someone to make them sub-admin! - ${this.botId}`);
                    return;
                }
                const targetJid = msg.message.extendedTextMessage.contextInfo.participant;
                if (addSubAdmin(targetJid, from)) {
                    await this.sendMessage(from, `✅ @${targetJid.split('@')[0]} is now a SUB-ADMIN! - ${this.botId}`, [targetJid]);
                } else {
                    await this.sendMessage(from, `⚠️ Already a sub-admin! - ${this.botId}`);
                }
                return;
            }

            if (isGroup && text === '-sub' && senderIsAdmin) {
                if (!msg.message.extendedTextMessage?.contextInfo?.participant) {
                    await this.sendMessage(from, `❌ Reply to someone to remove them as sub-admin! - ${this.botId}`);
                    return;
                }
                const targetJid = msg.message.extendedTextMessage.contextInfo.participant;
                if (removeSubAdmin(targetJid, from)) {
                    await this.sendMessage(from, `✅ @${targetJid.split('@')[0]} is no longer a sub-admin! - ${this.botId}`, [targetJid]);
                } else {
                    await this.sendMessage(from, `⚠️ Not a sub-admin! - ${this.botId}`);
                }
                return;
            }

            if (originalText.toLowerCase().startsWith('+add ') && senderIsAdmin) {
                const number = originalText.slice(5).trim().replace(/[^0-9]/g, '');
                if (number.length < 10) {
                    await this.sendMessage(from, `❌ Invalid phone number! - ${this.botId}\n\nUsage: +add [number]\nExample: +add 1234567890`);
                    return;
                }
                
                const result = await this.botManager.addBot(number, from);
                await this.sendMessage(from, result);
                return;
            }

            if (text === '+bots' && senderHasPermission) {
                const bots = this.botManager.commandBus.getAllBots();
                let msg = `🤖 *ACTIVE BOTS (${this.botId})* 🤖\n\n`;
                msg += `Total Bots: ${bots.length}\n\n`;
                
                bots.forEach(bot => {
                    const status = bot.connected ? '✅ Online' : '⚠️ Offline';
                    msg += `${bot.botId}: ${status}\n`;
                    if (bot.botNumber) {
                        msg += `  📱 ${bot.botNumber.split('@')[0]}\n`;
                    }
                });
                
                await this.sendMessage(from, msg);
                return;
            }

            if (text === '+ping' && senderHasPermission) {
                const startTime = Date.now();
                await this.sendMessage(from, '🏓 Pinging...');
                const latency = Date.now() - startTime;
                await this.sendMessage(from, `⚡ *THUNDER PING* ⚡\n\n🏓 Latency: ${latency}ms\n🤖 Bot: ${this.botId}`);
                return;
            }

            if (text === '+delays' && senderHasPermission) {
                let delayMsg = `⚡ *THUNDER DELAYS (${this.botId})* ⚡\n\n`;
                
                // Show Triple Attack delays
                delayMsg += `*TRIPLE ATTACK DELAYS:*\n`;
                delayMsg += `━━━━━━━━━━━━━━━━━━━━━\n`;
                
                for (let i = 1; i <= 35; i++) {
                    const tripleKey = `triple${i}`;
                    const delayValue = ncDelays[tripleKey] || 200;
                    const comboNames = tripleNcCombos[tripleKey] || ['nc1', 'nc2', 'nc3'];
                    
                    delayMsg += `${tripleKey}: ${comboNames.join(', ')} → ${delayValue}ms`;
                    
                    if (delayValue < MINIMUM_SAFE_DELAYS.triple_nc) {
                        delayMsg += ` ⚠️ RISKY!\n`;
                    } else {
                        delayMsg += ` ✅\n`;
                    }
                    
                    if (i % 5 === 0) delayMsg += `\n`;
                }
                
                delayMsg += `\n*INDIVIDUAL NC DELAYS (Sample):*\n`;
                delayMsg += `━━━━━━━━━━━━━━━━━━━━━\n`;
                
                // Show sample of individual delays
                for (let i = 1; i <= 10; i++) {
                    const ncKey = `nc${i}`;
                    const delayValue = ncDelays[ncKey] || 200;
                    const firstEmoji = emojiArrays[ncKey]?.[0] || '❓';
                    
                    delayMsg += `${ncKey}: ${firstEmoji} → ${delayValue}ms`;
                    
                    if (delayValue < MINIMUM_SAFE_DELAYS.nc_attacks) {
                        delayMsg += ` ⚠️\n`;
                    } else {
                        delayMsg += ` ✅\n`;
                    }
                }
                
                delayMsg += `... +nc11 to +nc100 available\n\n`;
                delayMsg += `⚠️ MINIMUM SAFE DELAYS:\n`;
                delayMsg += `• Triple Attacks: ${MINIMUM_SAFE_DELAYS.triple_nc}ms\n`;
                delayMsg += `• Individual NC: ${MINIMUM_SAFE_DELAYS.nc_attacks}ms\n`;
                delayMsg += `• Messages: ${MINIMUM_SAFE_DELAYS.messages}ms\n\n`;
                delayMsg += `Use +delaync[1-100] [ms] or +delaytriple[1-35] [ms]`;
                
                await this.sendMessage(from, delayMsg);
                return;
            }

            if (text === '+triples' && senderHasPermission) {
                let triplesMsg = `⚡ *TRIPLE NC ATTACKS (${this.botId})* ⚡\n\n`;
                triplesMsg += `Total Triple Attacks: 35\n`;
                triplesMsg += `Format: +triple[1-35] [text]\n\n`;
                
                for (let i = 1; i <= 35; i++) {
                    const tripleKey = `triple${i}`;
                    const comboNames = tripleNcCombos[tripleKey] || ['nc1', 'nc2', 'nc3'];
                    const firstEmoji = emojiArrays[comboNames[0]]?.[0] || '❓';
                    const secondEmoji = emojiArrays[comboNames[1]]?.[0] || '❓';
                    const thirdEmoji = emojiArrays[comboNames[2]]?.[0] || '❓';
                    
                    triplesMsg += `${tripleKey}: ${firstEmoji} ${secondEmoji} ${thirdEmoji}`;
                    
                    // Add description for some attacks
                    if (i === 11) triplesMsg += ` (Phone Attacks 1)`;
                    else if (i === 12) triplesMsg += ` (Phone Attacks 2)`;
                    else if (i === 13) triplesMsg += ` (Phone Attacks 3)`;
                    else if (i === 14) triplesMsg += ` (Phone Attacks 4)`;
                    else if (i === 15) triplesMsg += ` (Phone Attacks 5)`;
                    
                    triplesMsg += `\n`;
                    
                    if (i % 7 === 0) triplesMsg += `\n`;
                }
                
                triplesMsg += `\nExample: +triple1 RAID → Starts nc1, nc2, and nc3 simultaneously`;
                await this.sendMessage(from, triplesMsg);
                return;
            }

            // NEW: FONT COMMANDS
            if (text === '+fonts' && senderHasPermission) {
                let fontMsg = `🎨 *AVAILABLE FONT STYLES* 🎨\n\n`;
                Object.keys(fontStyles).forEach((font, index) => {
                    const fontInfo = fontStyles[font];
                    const sampleText = convertToFont('Thunder', font);
                    fontMsg += `${font}: ${fontInfo.name}\nSample: ${sampleText}\n`;
                    if ((index + 1) % 2 === 0) fontMsg += `\n`;
                });
                fontMsg += `\nUsage: +tne [font] [nc#] [text] [delay]\nExample: +tne double nc1 RAID 1000`;
                await this.sendMessage(from, fontMsg);
                return;
            }

            if (!senderHasPermission) return;

            if (text === '+menu') {
                await this.sendMessage(from, `${thunderMenu}\n\n📍 Responding from: ${this.botId}`);
                return;
            }

            if (text === '+status') {
                const allBots = this.botManager.commandBus.getAllBots();
                let totalName = 0, totalTriple = 0, totalSlide = 0, totalTxt = 0, totalTTS = 0, totalPic = 0;
                let totalTne = 0; // NEW: Text+emoji attacks
                
                allBots.forEach(bot => {
                    totalName += bot.activeNameChanges.size;
                    totalTriple += bot.activeTripleNc.size;
                    totalSlide += bot.activeSlides.size;
                    totalTxt += bot.activeTxtSenders.size;
                    totalTTS += bot.activeTTSSenders.size;
                    totalPic += bot.activePicSenders.size;
                    totalTne += bot.activeTextEmojiAttacks.size; // NEW
                });
                
                let localName = 0, localTriple = 0, localSlide = 0, localTxt = 0, localTTS = 0, localPic = 0;
                let localTne = 0; // NEW
                
                this.activeNameChanges.forEach((val, key) => {
                    if (key.startsWith(from)) localName++;
                });
                this.activeTripleNc.forEach((val, key) => {
                    if (key.startsWith(from)) localTriple++;
                });
                this.activeSlides.forEach((task) => {
                    if (task.groupJid === from && task.active) localSlide++;
                });
                this.activeTxtSenders.forEach((task, key) => {
                    if (key.startsWith(from) && task.active) localTxt++;
                });
                this.activeTTSSenders.forEach((task, key) => {
                    if (key.startsWith(from) && task.active) localTTS++;
                });
                this.activePicSenders.forEach((task, key) => {
                    if (key.startsWith(from) && task.active) localPic++;
                });
                // NEW: Count text+emoji attacks
                this.activeTextEmojiAttacks.forEach((task, key) => {
                    if (key.startsWith(from) && task.active) localTne++;
                });
                
                const statusMsg = `
⚡ *${this.botId} THUNDER STATUS* ⚡
━━━━━━━━━━━━━━━━━━━━━
📊 *THIS CHAT (${this.botId})*
━━━━━━━━━━━━━━━━━━━━━
⚔️ Individual NC: ${localName}
🎭 Triple Attacks: ${localTriple}
🎨 Text+Emoji: ${localTne}
🎯 Slide Attacks: ${localSlide}
💀 Text Attacks: ${localTxt}
🎤 TTS Attacks: ${localTTS}
📸 Pic Attacks: ${localPic}
━━━━━━━━━━━━━━━━━━━━━
🌐 *ALL BOTS GLOBAL*
━━━━━━━━━━━━━━━━━━━━━
⚔️ Individual NC: ${totalName}
🎭 Triple Attacks: ${totalTriple}
🎨 Text+Emoji: ${totalTne}
🎯 Slide Attacks: ${totalSlide}
💀 Text Attacks: ${totalTxt}
🎤 TTS Attacks: ${totalTTS}
📸 Pic Attacks: ${totalPic}
━━━━━━━━━━━━━━━━━━━━━
🤖 Active Bots: ${allBots.filter(b => b.connected).length}/${allBots.length}
━━━━━━━━━━━━━━━━━━━━━`;
                
                await this.sendMessage(from, statusMsg);
                return;
            }

            if (text === '-all') {
                await this.botManager.commandBus.broadcastCommand('stop_all', { from }, this.botId);
                return;
            }

            // NEW: TEXT+EMOJI ATTACK COMMAND
            if (originalText.toLowerCase().startsWith('+tne ')) {
                const args = originalText.slice(5).trim().split(' ');
                if (args.length < 4) {
                    await this.sendMessage(from, `❌ Usage: +tne [font] [nc#] [text] [delay] - ${this.botId}\nExample: +tne double nc1 RAID 1000\nUse +fonts to see available fonts`);
                    return;
                }

                const fontStyle = args[0].toLowerCase();
                const ncKey = args[1].toLowerCase();
                const tneDelay = parseInt(args[args.length - 1]);
                const tneText = args.slice(2, -1).join(' ');

                if (!fontStyles[fontStyle]) {
                    await this.sendMessage(from, `❌ Invalid font style! Use +fonts to see available styles - ${this.botId}`);
                    return;
                }

                if (!emojiArrays[ncKey]) {
                    await this.sendMessage(from, `❌ Invalid NC number! Use nc1 to nc100 - ${this.botId}`);
                    return;
                }

                if (isNaN(tneDelay) || tneDelay < 100) {
                    await this.sendMessage(from, `❌ Delay must be >= 100ms - ${this.botId}`);
                    return;
                }

                if (!isGroup) {
                    await this.sendMessage(from, `❌ Use this in a group! - ${this.botId}`);
                    return;
                }

                await this.botManager.commandBus.broadcastCommand('start_tne', { 
                    from, 
                    tneText, 
                    tneDelay, 
                    fontStyle,
                    ncKey 
                }, this.botId);
                return;
            }
            else if (text === '-tne') {
                if (!isGroup) {
                    await this.sendMessage(from, `❌ Use this in a group! - ${this.botId}`);
                    return;
                }
                await this.botManager.commandBus.broadcastCommand('stop_tne', { from }, this.botId);
                return;
            }

            // TRIPLE ATTACK DELAY SETTING
            for (let i = 1; i <= 35; i++) {
                const tripleKey = `triple${i}`;
                if (originalText.toLowerCase().startsWith(`+delay${tripleKey} `)) {
                    const delayValue = parseInt(originalText.split(' ')[1]);
                    if (isNaN(delayValue) || delayValue < 50) {
                        await this.sendMessage(from, `❌ Delay must be >= 50ms - ${this.botId}`);
                        return;
                    }
                    
                    ncDelays[tripleKey] = delayValue;
                    saveDelays(ncDelays);
                    
                    const comboNames = tripleNcCombos[tripleKey] || ['nc1', 'nc2', 'nc3'];
                    
                    let warning = '';
                    if (delayValue < MINIMUM_SAFE_DELAYS.triple_nc) {
                        warning = `\n\n⚠️ WARNING: ${delayValue}ms is VERY RISKY for triple attacks!\nRecommended minimum: ${MINIMUM_SAFE_DELAYS.triple_nc}ms`;
                    }
                    
                    await this.sendMessage(from, `⚡ *THUNDER ${this.botId}* ⚡\n\n✅ ${tripleKey.toUpperCase()} delay set to ${delayValue}ms\nRuns: ${comboNames.join(', ')} simultaneously${warning}`);
                    return;
                }
            }

            // INDIVIDUAL NC DELAY SETTING
            for (let i = 1; i <= 100; i++) {
                const ncKey = `nc${i}`;
                if (originalText.toLowerCase().startsWith(`+delaync${i} `)) {
                    const delayValue = parseInt(originalText.split(' ')[1]);
                    if (isNaN(delayValue) || delayValue < 50) {
                        await this.sendMessage(from, `❌ Delay must be >= 50ms - ${this.botId}`);
                        return;
                    }
                    
                    ncDelays[ncKey] = delayValue;
                    saveDelays(ncDelays);
                    
                    let warning = '';
                    if (delayValue < MINIMUM_SAFE_DELAYS.nc_attacks) {
                        warning = `\n\n⚠️ WARNING: ${delayValue}ms is VERY RISKY!\nRecommended minimum: ${MINIMUM_SAFE_DELAYS.nc_attacks}ms`;
                    }
                    
                    await this.sendMessage(from, `⚡ *THUNDER ${this.botId}* ⚡\n\n✅ ${ncKey.toUpperCase()} delay set to ${delayValue}ms${warning}`);
                    return;
                }
            }

            // TRIPLE ATTACK COMMANDS
            for (let i = 1; i <= 35; i++) {
                const tripleKey = `triple${i}`;
                if (originalText.toLowerCase().startsWith(`+${tripleKey} `)) {
                    const nameText = originalText.slice(tripleKey.length + 2).trim();
                    if (!nameText) {
                        await this.sendMessage(from, `❌ Usage: +${tripleKey} [text] - ${this.botId}\nExample: +${tripleKey} RAID`);
                        return;
                    }

                    if (!isGroup) {
                        await this.sendMessage(from, `❌ Use this in a group! - ${this.botId}`);
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
            for (let i = 1; i <= 100; i++) {
                const ncKey = `nc${i}`;
                if (originalText.toLowerCase().startsWith(`+${ncKey} `)) {
                    const nameText = originalText.slice(ncKey.length + 2).trim();
                    if (!nameText) {
                        await this.sendMessage(from, `❌ Usage: +${ncKey} [text] - ${this.botId}\nExample: +${ncKey} RAID`);
                        return;
                    }

                    if (!isGroup) {
                        await this.sendMessage(from, `❌ Use this in a group! - ${this.botId}`);
                        return;
                    }

                    await this.botManager.commandBus.broadcastCommand('start_nc', { from, nameText, ncKey }, this.botId);
                    return;
                }
            }

            if (text === '-nc') {
                if (!isGroup) {
                    await this.sendMessage(from, `❌ Use this in a group! - ${this.botId}`);
                    return;
                }

                await this.botManager.commandBus.broadcastCommand('stop_nc', { from }, this.botId);
                await this.botManager.commandBus.broadcastCommand('stop_triple_nc', { from }, this.botId);
                return;
            }

            // SLIDE ATTACK
            if (originalText.toLowerCase().startsWith('+s ')) {
                if (!msg.message.extendedTextMessage?.contextInfo?.quotedMessage) {
                    await this.sendMessage(from, `❌ Reply to target\'s message! - ${this.botId}\nUsage: +s [text] [delay]`);
                    return;
                }

                const args = originalText.slice(3).trim().split(' ');
                if (args.length < 2) {
                    await this.sendMessage(from, `❌ Usage: +s [text] [delay] - ${this.botId}\nExample: +s Hello 1000`);
                    return;
                }

                const slideDelay = parseInt(args[args.length - 1]);
                const slideText = args.slice(0, -1).join(' ');

                if (isNaN(slideDelay) || slideDelay < 100) {
                    await this.sendMessage(from, `❌ Delay must be >= 100ms - ${this.botId}`);
                    return;
                }

                const quotedParticipant = msg.message.extendedTextMessage.contextInfo.participant || 
                                        msg.message.extendedTextMessage.contextInfo.remoteJid;
                const quotedMsgId = msg.message.extendedTextMessage.contextInfo.stanzaId;
                const quotedMessage = msg.message.extendedTextMessage.contextInfo.quotedMessage;

                await this.botManager.commandBus.broadcastCommand('start_slide', {
                    from,
                    slideText,
                    slideDelay,
                    quotedParticipant,
                    quotedMsgId,
                    quotedMessage
                }, this.botId);
                return;
            }
            else if (text === '-s') {
                await this.botManager.commandBus.broadcastCommand('stop_slide', { from }, this.botId);
                return;
            }

            // TEXT SPAM
            else if (originalText.toLowerCase().startsWith('+txt ')) {
                const args = originalText.slice(5).trim().split(' ');
                if (args.length < 2) {
                    await this.sendMessage(from, `❌ Usage: +txt [text] [delay] - ${this.botId}\nExample: +txt Hello 1000`);
                    return;
                }

                const txtDelay = parseInt(args[args.length - 1]);
                const txtText = args.slice(0, -1).join(' ');

                if (isNaN(txtDelay) || txtDelay < 100) {
                    await this.sendMessage(from, `❌ Delay must be >= 100ms - ${this.botId}`);
                    return;
                }

                await this.botManager.commandBus.broadcastCommand('start_txt', { from, txtText, txtDelay }, this.botId);
                return;
            }
            else if (text === '-txt') {
                await this.botManager.commandBus.broadcastCommand('stop_txt', { from }, this.botId);
                return;
            }

            // TTS ATTACKS
            else if (originalText.toLowerCase().startsWith('+tts ')) {
                const ttsText = originalText.slice(5).trim();
                if (!ttsText) {
                    await this.sendMessage(from, `❌ Usage: +tts [text] - ${this.botId}\nExample: +tts Hello everyone`);
                    return;
                }

                try {
                    const audioBuffer = await generateTTS(ttsText);
                    await this.sock.sendMessage(from, {
                        audio: audioBuffer,
                        mimetype: 'audio/ogg; codecs=opus',
                        ptt: true
                    });
                } catch (err) {
                    console.error(`[${this.botId}] TTS error:`, err.message);
                    await this.sendMessage(from, `❌ TTS error - ${this.botId}`);
                }
                return;
            }
            else if (originalText.toLowerCase().startsWith('+ttsatk ')) {
                const args = originalText.slice(8).trim().split(' ');
                if (args.length < 2) {
                    await this.sendMessage(from, `❌ Usage: +ttsatk [text] [delay] - ${this.botId}\nExample: +ttsatk Hello 2000`);
                    return;
                }

                const ttsDelay = parseInt(args[args.length - 1]);
                const ttsText = args.slice(0, -1).join(' ');

                if (isNaN(ttsDelay) || ttsDelay < 1000) {
                    await this.sendMessage(from, `❌ Delay must be >= 1000ms (1s) - ${this.botId}`);
                    return;
                }

                await this.botManager.commandBus.broadcastCommand('start_tts', { from, ttsText, ttsDelay }, this.botId);
                return;
            }
            else if (text === '-ttsatk') {
                await this.botManager.commandBus.broadcastCommand('stop_tts', { from }, this.botId);
                return;
            }

            // PICTURE ATTACKS
            else if (originalText.toLowerCase().startsWith('+pic ')) {
                if (!msg.message.extendedTextMessage?.contextInfo?.quotedMessage?.imageMessage) {
                    await this.sendMessage(from, `❌ Reply to an image! - ${this.botId}\nUsage: +pic [delay]`);
                    return;
                }

                const picDelay = parseInt(originalText.slice(5).trim());
                if (isNaN(picDelay) || picDelay < 100) {
                    await this.sendMessage(from, `❌ Delay must be >= 100ms - ${this.botId}`);
                    return;
                }

                const quotedMsg = {
                    key: {
                        remoteJid: from,
                        fromMe: false,
                        id: msg.message.extendedTextMessage.contextInfo.stanzaId,
                        participant: msg.message.extendedTextMessage.contextInfo.participant
                    },
                    message: msg.message.extendedTextMessage.contextInfo.quotedMessage
                };

                try {
                    const imageBuffer = await downloadMediaMessage(quotedMsg, 'buffer', {});
                    const imageMessage = msg.message.extendedTextMessage.contextInfo.quotedMessage.imageMessage;
                    
                    await this.botManager.commandBus.broadcastCommand('start_pic', { 
                        from, 
                        picDelay, 
                        imageBuffer: imageBuffer.toString('base64'),
                        mimetype: imageMessage.mimetype || 'image/jpeg'
                    }, this.botId);
                } catch (err) {
                    console.error(`[${this.botId}] Error downloading image:`, err.message);
                    await this.sendMessage(from, `❌ Error downloading image - ${this.botId}`);
                }
                return;
            }
            else if (text === '-pic') {
                await this.botManager.commandBus.broadcastCommand('stop_pic', { from }, this.botId);
                return;
            }

        } catch (err) {
            console.error(`[${this.botId}] ERROR:`, err);
        }
    }

    async executeCommand(commandType, data, sendConfirmation = true) {
        try {
            // INDIVIDUAL NC ATTACK
            if (commandType === 'start_nc') {
                const { from, nameText, ncKey } = data;
                const emojis = emojiArrays[ncKey] || ['❓'];
                const nameDelay = ncDelays[ncKey] || 200;
                
                for (let i = 0; i < 5; i++) {
                    const taskId = `${from}_${ncKey}_${i}`;
                    if (this.activeNameChanges.has(taskId)) {
                        this.activeNameChanges.delete(taskId);
                        await delay(100);
                    }

                    let emojiIndex = i * Math.floor(emojis.length / 5);
                    
                    const runLoop = async () => {
                        this.activeNameChanges.set(taskId, true);
                        await delay(i * 200);
                        while (this.activeNameChanges.get(taskId)) {
                            try {
                                const emoji = emojis[Math.floor(emojiIndex) % emojis.length];
                                const newName = `${nameText} ${emoji}`;
                                await this.sock.groupUpdateSubject(from, newName);
                                emojiIndex++;
                                await delay(nameDelay);
                            } catch (err) {
                                if (err.message?.includes('rate-overlimit')) {
                                    await delay(3000);
                                } else {
                                    await delay(nameDelay);
                                }
                            }
                        }
                    };

                    runLoop();
                }

                if (sendConfirmation) {
                    let warning = '';
                    if (nameDelay < MINIMUM_SAFE_DELAYS.nc_attacks) {
                        warning = `\n\n⚠️ WARNING: ${nameDelay}ms is VERY RISKY!\nRisk of WhatsApp ban is HIGH!`;
                    }
                    
                    await this.sendMessage(from, `⚡ *THUNDER ${ncKey.toUpperCase()} STARTED* ⚡\n\n💥 ${nameText}\n⏱️ Delay: ${nameDelay}ms${warning}\n🤖 Bot: ${this.botId}`);
                }
            }
            
            // TRIPLE NC ATTACK
            else if (commandType === 'start_triple_nc') {
                const { from, nameText, tripleKey } = data;
                const comboNames = tripleNcCombos[tripleKey] || ['nc1', 'nc2', 'nc3'];
                const tripleDelay = ncDelays[tripleKey] || 200;
                
                // Store this triple attack
                const tripleTaskId = `${from}_${tripleKey}`;
                const tripleTask = { active: true, ncKeys: comboNames };
                this.activeTripleNc.set(tripleTaskId, tripleTask);
                
                console.log(`[${this.botId}] Starting TRIPLE ATTACK: ${comboNames.join(', ')} with delay ${tripleDelay}ms`);
                
                // Start each NC in the combo as SEPARATE attacks
                for (const ncKey of comboNames) {
                    const emojis = emojiArrays[ncKey] || ['❓'];
                    const individualDelay = ncDelays[ncKey] || 200;
                    
                    for (let i = 0; i < 3; i++) {
                        const threadId = `${from}_${tripleKey}_${ncKey}_${i}`;
                        
                        if (this.activeNameChanges.has(threadId)) {
                            this.activeNameChanges.delete(threadId);
                            await delay(100);
                        }

                        let emojiIndex = i * Math.floor(emojis.length / 3);
                        
                        const runLoop = async () => {
                            this.activeNameChanges.set(threadId, true);
                            await delay(i * 100);
                            
                            while (this.activeNameChanges.get(threadId) && tripleTask.active) {
                                try {
                                    const emoji = emojis[Math.floor(emojiIndex) % emojis.length];
                                    const newName = `${nameText} ${emoji}`;
                                    await this.sock.groupUpdateSubject(from, newName);
                                    emojiIndex++;
                                    
                                    await delay(individualDelay);
                                } catch (err) {
                                    if (err.message?.includes('rate-overlimit')) {
                                        await delay(3000);
                                    } else {
                                        await delay(individualDelay);
                                    }
                                }
                            }
                            this.activeNameChanges.delete(threadId);
                        };

                        runLoop();
                    }
                }

                if (sendConfirmation) {
                    const comboNames = tripleNcCombos[tripleKey] || ['nc1', 'nc2', 'nc3'];
                    const firstEmoji = emojiArrays[comboNames[0]]?.[0] || '❓';
                    const secondEmoji = emojiArrays[comboNames[1]]?.[0] || '❓';
                    const thirdEmoji = emojiArrays[comboNames[2]]?.[0] || '❓';
                    
                    let warning = '';
                    if (tripleDelay < MINIMUM_SAFE_DELAYS.triple_nc) {
                        warning = `\n\n⚠️ WARNING: ${tripleDelay}ms is VERY RISKY for triple attacks!\nRisk of WhatsApp ban is EXTREMELY HIGH!`;
                    }
                    
                    await this.sendMessage(from, `⚡ *THUNDER ${tripleKey.toUpperCase()} STARTED* ⚡\n\n💥 ${nameText}\n🎭 Running 3 NCs: ${comboNames.join(', ')}\n⚡ Each: ${firstEmoji} ${secondEmoji} ${thirdEmoji}\n⏱️ Delay: ${tripleDelay}ms${warning}\n🤖 Bot: ${this.botId}`);
                }
            }
            
            // NEW: TEXT+EMOJI ATTACK
            else if (commandType === 'start_tne') {
                const { from, tneText, tneDelay, fontStyle, ncKey } = data;
                const emojis = emojiArrays[ncKey] || ['❓'];
                const fontName = fontStyles[fontStyle]?.name || 'Normal';
                
                const taskId = `${from}_tne_${fontStyle}_${ncKey}`;
                
                if (this.activeTextEmojiAttacks.has(taskId)) {
                    this.activeTextEmojiAttacks.get(taskId).active = false;
                    await delay(200);
                }

                const tneTask = { 
                    active: true,
                    fontStyle: fontStyle,
                    ncKey: ncKey,
                    emojiIndex: 0
                };
                this.activeTextEmojiAttacks.set(taskId, tneTask);

                const runTne = async () => {
                    while (tneTask.active) {
                        try {
                            const emoji = emojis[tneTask.emojiIndex % emojis.length];
                            const convertedText = convertToFont(tneText, fontStyle);
                            const finalText = `${convertedText} ${emoji}`;
                            
                            await this.sock.groupUpdateSubject(from, finalText);
                            
                            tneTask.emojiIndex++;
                            await delay(tneDelay);
                        } catch (err) {
                            console.error(`[${this.botId}] TNE Error:`, err.message);
                            await delay(tneDelay);
                        }
                    }
                };

                runTne();

                if (sendConfirmation) {
                    const sampleEmoji = emojis[0] || '❓';
                    const convertedSample = convertToFont(tneText, fontStyle);
                    const sampleFinal = `${convertedSample} ${sampleEmoji}`;
                    
                    let warning = '';
                    if (tneDelay < MINIMUM_SAFE_DELAYS.nc_attacks) {
                        warning = `\n\n⚠️ WARNING: ${tneDelay}ms is VERY RISKY!\nRisk of WhatsApp ban is HIGH!`;
                    }
                    
                    await this.sendMessage(from, `🎨 *TEXT+EMOJI ATTACK STARTED* 🎨\n\nFont: ${fontName}\nEmoji Set: ${ncKey}\nText: ${tneText}\nConverted: ${convertedSample}\nFinal: ${sampleFinal}\n⏱️ Delay: ${tneDelay}ms${warning}\n🤖 Bot: ${this.botId}`);
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
                    await this.sendMessage(from, `⚡ *THUNDER NC STOPPED* ⚡\n\n✅ Stopped ${stopped} individual NC threads - ${this.botId}`);
                }
            }
            
            // STOP TRIPLE NC
            else if (commandType === 'stop_triple_nc') {
                const { from } = data;
                let stoppedCombos = 0;
                
                this.activeTripleNc.forEach((task, taskId) => {
                    if (taskId.startsWith(from)) {
                        task.active = false;
                        
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
                    await this.sendMessage(from, `⚡ *TRIPLE ATTACKS STOPPED* ⚡\n\n✅ Stopped ${stoppedCombos} triple attack(s) - ${this.botId}`);
                }
            }
            
            // NEW: STOP TEXT+EMOJI ATTACKS
            else if (commandType === 'stop_tne') {
                const { from } = data;
                let stopped = 0;
                
                this.activeTextEmojiAttacks.forEach((task, taskId) => {
                    if (taskId.startsWith(from)) {
                        task.active = false;
                        this.activeTextEmojiAttacks.delete(taskId);
                        stopped++;
                    }
                });

                if (stopped > 0 && sendConfirmation) {
                    await this.sendMessage(from, `🎨 *TEXT+EMOJI ATTACKS STOPPED* 🎨\n\n✅ Stopped ${stopped} text+emoji attack(s) - ${this.botId}`);
                }
            }
            
            // SLIDE ATTACK
            else if (commandType === 'start_slide') {
                const { from, slideText, slideDelay, quotedParticipant, quotedMsgId, quotedMessage } = data;
                
                const taskId = `${from}_${quotedParticipant}`;
                
                if (this.activeSlides.has(taskId)) {
                    this.activeSlides.get(taskId).active = false;
                    await delay(200);
                }

                const slideTask = {
                    targetJid: quotedParticipant,
                    text: slideText,
                    groupJid: from,
                    latestMsg: {
                        key: {
                            remoteJid: from,
                            fromMe: false,
                            id: quotedMsgId,
                            participant: quotedParticipant
                        },
                        message: quotedMessage
                    },
                    hasNewMsg: true,
                    lastRepliedId: null,
                    active: true
                };

                this.activeSlides.set(taskId, slideTask);

                const runSlide = async () => {
                    while (slideTask.active) {
                        try {
                            await this.sock.sendMessage(from, { 
                                text: slideText 
                            }, { 
                                quoted: slideTask.latestMsg
                            });
                        } catch (err) {
                            console.error(`[${this.botId}] SLIDE Error:`, err.message);
                        }
                        await delay(slideDelay);
                    }
                };

                runSlide();

                if (sendConfirmation) {
                    let warning = '';
                    if (slideDelay < MINIMUM_SAFE_DELAYS.messages) {
                        warning = `\n\n⚠️ WARNING: ${slideDelay}ms is VERY RISKY!\nRisk of WhatsApp ban is HIGH!`;
                    }
                    
                    await this.sendMessage(from, `⚡ *THUNDER SLIDE STARTED* ⚡\n\n💬 ${slideText}\n⏱️ Delay: ${slideDelay}ms${warning}\n🤖 Bot: ${this.botId}`);
                }
            }
            else if (commandType === 'stop_slide') {
                const { from } = data;
                let stopped = 0;
                this.activeSlides.forEach((task, taskId) => {
                    if (task.groupJid === from) {
                        task.active = false;
                        this.activeSlides.delete(taskId);
                        stopped++;
                    }
                });

                if (stopped > 0 && sendConfirmation) {
                    await this.sendMessage(from, `⚡ *THUNDER SLIDE STOPPED* ⚡\n\n✅ ${stopped} attack(s) - ${this.botId}`);
                }
            }
            
            // TEXT SPAM
            else if (commandType === 'start_txt') {
                const { from, txtText, txtDelay } = data;
                
                const taskId = `${from}_txt`;
                
                if (this.activeTxtSenders.has(taskId)) {
                    this.activeTxtSenders.get(taskId).active = false;
                    await delay(200);
                }

                const txtTask = { active: true };
                this.activeTxtSenders.set(taskId, txtTask);

                const runTxt = async () => {
                    while (txtTask.active) {
                        try {
                            await this.sock.sendMessage(from, { text: txtText });
                        } catch (err) {
                            console.error(`[${this.botId}] TXT Error:`, err.message);
                        }
                        await delay(txtDelay);
                    }
                };

                runTxt();

                if (sendConfirmation) {
                    let warning = '';
                    if (txtDelay < MINIMUM_SAFE_DELAYS.messages) {
                        warning = `\n\n⚠️ WARNING: ${txtDelay}ms is VERY RISKY!\nRisk of WhatsApp ban is HIGH!`;
                    }
                    
                    await this.sendMessage(from, `⚡ *THUNDER TEXT ATTACK* ⚡\n\n💬 ${txtText}\n⏱️ Delay: ${txtDelay}ms${warning}\n🤖 Bot: ${this.botId}`);
                }
            }
            else if (commandType === 'stop_txt') {
                const { from } = data;
                const taskId = `${from}_txt`;
                if (this.activeTxtSenders.has(taskId)) {
                    this.activeTxtSenders.get(taskId).active = false;
                    this.activeTxtSenders.delete(taskId);
                    if (sendConfirmation) {
                        await this.sendMessage(from, `✅ Text attack stopped - ${this.botId}`);
                    }
                }
            }
            
            // TTS ATTACK
            else if (commandType === 'start_tts') {
                const { from, ttsText, ttsDelay } = data;
                
                const taskId = `${from}_tts`;
                
                if (this.activeTTSSenders.has(taskId)) {
                    this.activeTTSSenders.get(taskId).active = false;
                    await delay(200);
                }

                const ttsTask = { active: true };
                this.activeTTSSenders.set(taskId, ttsTask);

                const runTTS = async () => {
                    while (ttsTask.active) {
                        try {
                            const audioBuffer = await generateTTS(ttsText);
                            await this.sock.sendMessage(from, {
                                audio: audioBuffer,
                                mimetype: 'audio/ogg; codecs=opus',
                                ptt: true
                            });
                        } catch (err) {
                            console.error(`[${this.botId}] TTS Error:`, err.message);
                        }
                        await delay(ttsDelay);
                    }
                };

                runTTS();

                if (sendConfirmation) {
                    let warning = '';
                    if (ttsDelay < MINIMUM_SAFE_DELAYS.voice) {
                        warning = `\n\n⚠️ WARNING: ${ttsDelay}ms is VERY RISKY!\nRisk of WhatsApp ban is HIGH!`;
                    }
                    
                    await this.sendMessage(from, `⚡ *THUNDER TTS ATTACK* ⚡\n\n🎤 ${ttsText}\n⏱️ Delay: ${ttsDelay}ms${warning}\n🤖 Bot: ${this.botId}`);
                }
            }
            else if (commandType === 'stop_tts') {
                const { from } = data;
                const taskId = `${from}_tts`;
                if (this.activeTTSSenders.has(taskId)) {
                    this.activeTTSSenders.get(taskId).active = false;
                    this.activeTTSSenders.delete(taskId);
                    if (sendConfirmation) {
                        await this.sendMessage(from, `✅ TTS attack stopped - ${this.botId}`);
                    }
                }
            }
            
            // PICTURE ATTACK
            else if (commandType === 'start_pic') {
                const { from, picDelay, imageBuffer, mimetype } = data;
                
                const taskId = `${from}_pic`;
                
                if (this.activePicSenders.has(taskId)) {
                    this.activePicSenders.get(taskId).active = false;
                    await delay(200);
                }

                const picTask = { active: true, buffer: Buffer.from(imageBuffer, 'base64'), mimetype };
                this.activePicSenders.set(taskId, picTask);

                const runPic = async () => {
                    while (picTask.active) {
                        try {
                            await this.sock.sendMessage(from, {
                                image: picTask.buffer,
                                mimetype: picTask.mimetype
                            });
                        } catch (err) {
                            console.error(`[${this.botId}] PIC Error:`, err.message);
                        }
                        await delay(picDelay);
                    }
                };

                runPic();

                if (sendConfirmation) {
                    let warning = '';
                    if (picDelay < MINIMUM_SAFE_DELAYS.messages) {
                        warning = `\n\n⚠️ WARNING: ${picDelay}ms is VERY RISKY!\nRisk of WhatsApp ban is HIGH!`;
                    }
                    
                    await this.sendMessage(from, `⚡ *THUNDER PIC ATTACK* ⚡\n\n📸 Picture spam started\n⏱️ Delay: ${picDelay}ms${warning}\n🤖 Bot: ${this.botId}`);
                }
            }
            else if (commandType === 'stop_pic') {
                const { from } = data;
                const taskId = `${from}_pic`;
                if (this.activePicSenders.has(taskId)) {
                    this.activePicSenders.get(taskId).active = false;
                    this.activePicSenders.delete(taskId);
                    if (sendConfirmation) {
                        await this.sendMessage(from, `✅ Pic attack stopped - ${this.botId}`);
                    }
                }
            }
            
            // STOP ALL
            else if (commandType === 'stop_all') {
                const { from } = data;
                let stopped = 0;
                
                // Stop individual NC
                this.activeNameChanges.forEach((value, taskId) => {
                    if (taskId.startsWith(from)) {
                        this.activeNameChanges.set(taskId, false);
                        this.activeNameChanges.delete(taskId);
                        stopped++;
                    }
                });
                
                // Stop triple attacks
                this.activeTripleNc.forEach((task, taskId) => {
                    if (taskId.startsWith(from)) {
                        task.active = false;
                        this.activeTripleNc.delete(taskId);
                        stopped++;
                    }
                });
                
                // Stop text+emoji attacks
                this.activeTextEmojiAttacks.forEach((task, taskId) => {
                    if (taskId.startsWith(from)) {
                        task.active = false;
                        this.activeTextEmojiAttacks.delete(taskId);
                        stopped++;
                    }
                });
                
                // Stop slides
                this.activeSlides.forEach((task, taskId) => {
                    if (task.groupJid === from) {
                        task.active = false;
                        this.activeSlides.delete(taskId);
                        stopped++;
                    }
                });
                
                // Stop text
                const txtTaskId = `${from}_txt`;
                if (this.activeTxtSenders.has(txtTaskId)) {
                    this.activeTxtSenders.get(txtTaskId).active = false;
                    this.activeTxtSenders.delete(txtTaskId);
                    stopped++;
                }

                // Stop TTS
                const ttsTaskId = `${from}_tts`;
                if (this.activeTTSSenders.has(ttsTaskId)) {
                    this.activeTTSSenders.get(ttsTaskId).active = false;
                    this.activeTTSSenders.delete(ttsTaskId);
                    stopped++;
                }

                // Stop pics
                const picTaskId = `${from}_pic`;
                if (this.activePicSenders.has(picTaskId)) {
                    this.activePicSenders.get(picTaskId).active = false;
                    this.activePicSenders.delete(picTaskId);
                    stopped++;
                }
                
                if (stopped > 0 && sendConfirmation) {
                    await this.sendMessage(from, `🛑 *THUNDER ${this.botId}* 🛑\n\n✅ Stopped ${stopped} attack(s)!`);
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
            console.log('[MANAGER] No saved sessions. Waiting for first bot via +add command...');
            console.log('[MANAGER] Or pair the first bot manually...\n');
            
            const phoneNumber = await question('Enter phone number for BOT1 (or press Enter to skip): ');
            if (phoneNumber && phoneNumber.trim()) {
                const cleanNumber = phoneNumber.replace(/[^0-9]/g, '');
                if (cleanNumber.length >= 10) {
                    await this.addBot(cleanNumber, null);
                }
            } else {
                console.log('[MANAGER] Skipped. Use +add command in WhatsApp to add bots.\n');
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
        
        return `🤖 *${botId} CREATED!* 🤖\n\n✅ Bot session created\n📱 Number: ${phoneNumber}\n\n⏳ Waiting for pairing code...\nCheck messages above for pairing instructions!`;
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
console.log('╔══════════════════════════════════════════════╗');
console.log('║   ⚡ THUNDER MULTI-BOT SYSTEM v3.0 ⚡         ║');
console.log('║     ⚡ TRIPLE NC + TEXT+EMOJI SYSTEM ⚡       ║');
console.log('╚══════════════════════════════════════════════╝\n');
console.log('📱 COMPLETE PHONE KEYBOARD EMOJIS INCLUDED!');
console.log('🎨 8 FONT STYLES FOR TEXT+EMOJI ATTACKS');
console.log('🎭 35 TRIPLE ATTACKS AVAILABLE');
console.log('⚡ 100 INDIVIDUAL NC TYPES');
console.log('\n🎨 NEW TEXT+EMOJI FEATURE:');
console.log('• Combine any text with any emoji set');
console.log('• Apply 8 different font styles');
console.log('• Command: +tne [font] [nc#] [text] [delay]');
console.log('• Example: +tne double nc1 RAID 1000');
console.log('• Fonts: double, mono, script, boldscript');
console.log('          gothic, boldgothic, square, circled');
console.log('\n⚠️  WARNING: Default delays are set to 200ms');
console.log('⚠️  This is VERY RISKY and may cause WhatsApp bans!');
console.log('⚠️  Use +delaytriple[1-35] [ms] to set safer delays (500ms+)');
console.log('⚠️  Use +delaync[1-100] [ms] for individual delays (1000ms+)\n');

const botManager = new BotManager();
await botManager.restoreSavedBots();
rl.close();

console.log('\n✅ Thunder Bot System Ready!');
console.log('📌 Send +admin in DM to become admin');
console.log('📌 Send +fonts to see all font styles');
console.log('📌 Send +tne double nc1 RAID 1000 to test new feature');
console.log('📌 Send +triples to see all 35 triple attacks');
console.log('📌 Send +menu to see all commands');
console.log('📱 Phone keyboard emojis: nc81-nc100');
console.log('🎨 Text+Emoji: Combine any text with any emoji set!');
console.log('⚡ Triple attacks: Runs 3 different NCs simultaneously!');
console.log('⚠️  WARNING: Use at your own risk!\n');