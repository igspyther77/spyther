import asyncio
import os
import sys
import time
import random
import io
import base64
import re
import json
from datetime import datetime
import edge_tts
from telethon import TelegramClient, events, functions, types
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest, GetUserPhotosRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, AddChatUserRequest, EditChatAdminRequest, DeleteMessagesRequest, SendReactionRequest
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest
from telethon.tl.types import InputPeerUser, ChatAdminRights, MessageEntityMention, MessageEntityMentionName, InputPeerChannel, InputPeerChat, MessageReactor, ReactionEmoji
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, ChatAdminRequiredError
from groq import AsyncGroq

# Groq AI Configuration
GROQ_API_KEY = "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"
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# Configuration
API_ID = 37390656
API_HASH = '5d01d3b2316028c7bae557854ff9bc55'
PHONE_NUMBER = '+919663485915'

# Global variables
client = TelegramClient('barbie_session', API_ID, API_HASH)
auto_name_change_active = {}
auto_message_active = {}
target_users = {}
target_cp_messages = {}
auto_reactions = {}  # Store reaction emoji for each chat
shutup_users = set()
shutup_groups = set()
allowed_ai_users = set()
chat_history = {}
user_history_db = {}
phone_info_db = {}
message_delays = {
    'cp': 0.5,  # Default delay for *cp command
    'targetcp': 0.3  # Default delay for *targetcp command
}

ORIGINAL_NAME = "𝐙ꫀꫀsʜᴜ𒀸"
ORIGINAL_BIO = "Solo Killer 🤧"

BOT_USERNAMES = [
    '@zesshufytbot', '@zesshufyt2bot', '@zesshufyt3bot', '@zesshufyt4bot',
    '@zesshufyt5bot', '@zesshufyt6bot', '@zesshufyt7bot', '@zesshufyt8bot',
    '@zesshufyt9bot', '@zesshufyt10bot'
]

EMOJIS = list("😀😃😄😁😆😅🤣😂🙂🙃😉😊😇🥰🤗😎😭😱😓😈😡🤬😻😼❤️💜🩵💛🤍💖💐🌸💮🏵️🌹🌼🌷🪻🦈🐠🐡🐬🕊️")

auto_reply_messages = [
    "chud aab merse", "chudai ke darse bhag mat", "tere ma ko ek uncle ne chodke mar dala",
    "teri behen road oe nangi hike danche krti hai 100 rs ke liye", "teri ma mere ghar ki kaam wali hai aukaat mai reh",
    "aukaat bana gulam", "gulam ey tu mc awaj ucha na kr",
    "teri behen basti ki no1 randi", "tere ma ke chut pe pair ghusake fadd dungi mc",
    "teri ma kutte ka loda chuse", "teri ma hijdi",
    "teri chinar make bhisde pe lath maru?",
    "teri behen ke nipple ktke kutto ko khila dungi mc",
    "chud chamar ke bacche", "teri ma rndy"
]

# Database functions
def load_databases():
    global user_history_db, phone_info_db
    try:
        if os.path.exists('user_history.json'):
            with open('user_history.json', 'r', encoding='utf-8') as f:
                user_history_db = json.load(f)
        if os.path.exists('phone_info.json'):
            with open('phone_info.json', 'r', encoding='utf-8') as f:
                phone_info_db = json.load(f)
    except Exception as e:
        print(f"Error loading databases: {e}")

def save_databases():
    try:
        with open('user_history.json', 'w', encoding='utf-8') as f:
            json.dump(user_history_db, f, indent=2, ensure_ascii=False)
        with open('phone_info.json', 'w', encoding='utf-8') as f:
            json.dump(phone_info_db, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving databases: {e}")

# Track user changes
async def track_user_changes(user_id, username=None, first_name=None, last_name=None, phone=None):
    user_id_str = str(user_id)
    if user_id_str not in user_history_db:
        user_history_db[user_id_str] = {
            'usernames': [],
            'names': [],
            'pfps': [],
            'phone': phone,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'message_count': 0,
            'groups': []
        }
    
    current_time = datetime.now().isoformat()
    user_history_db[user_id_str]['last_seen'] = current_time
    user_history_db[user_id_str]['message_count'] = user_history_db[user_id_str].get('message_count', 0) + 1
    
    # Track username changes
    if username:
        # Check if username actually changed
        last_username = user_history_db[user_id_str]['usernames'][-1]['username'] if user_history_db[user_id_str]['usernames'] else None
        if last_username != username:
            user_history_db[user_id_str]['usernames'].append({
                'username': username,
                'timestamp': current_time
            })
    
    # Track name changes
    if first_name or last_name:
        full_name = f"{first_name or ''} {last_name or ''}".strip()
        if full_name:
            last_name_entry = user_history_db[user_id_str]['names'][-1]['name'] if user_history_db[user_id_str]['names'] else None
            if last_name_entry != full_name:
                user_history_db[user_id_str]['names'].append({
                    'name': full_name,
                    'timestamp': current_time
                })
    
    # Track phone
    if phone and phone != user_history_db[user_id_str].get('phone'):
        user_history_db[user_id_str]['phone'] = phone
    
    save_databases()

# Enhanced phone info function
async def get_phone_info(phone_number):
    # Clean phone number
    clean_number = re.sub(r'[^0-9]', '', phone_number)
    if len(clean_number) > 10:
        clean_number = clean_number[-10:]
    
    # Check if we have stored info
    if clean_number in phone_info_db:
        return phone_info_db[clean_number]
    
    # Enhanced mock data with more details
    mock_data = {
        '9876543210': {
            'owner_name': 'Rahul Sharma',
            'father_name': 'Suresh Sharma',
            'mother_name': 'Sunita Sharma',
            'dob': '15-08-1995',
            'age': 28,
            'gender': 'Male',
            'location': 'Mumbai, Maharashtra',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'country': 'India',
            'aadhar_number': '1234-5678-9012',
            'aadhar_name': 'Rahul Suresh Sharma',
            'pan_number': 'ABCDE1234F',
            'voter_id': 'MH01/1234/567890',
            'address': '123, Juhu Beach Road, Juhu, Mumbai - 400049',
            'pincode': '400049',
            'registered_date': '2018-05-15',
            'operator': 'Jio',
            'circle': 'Maharashtra',
            'email': 'rahul.sharma@gmail.com',
            'social_media': {
                'instagram': '@rahul_sharma',
                'facebook': 'rahul.sharma.123',
                'twitter': '@rahul_s'
            },
            'family_members': ['Suresh Sharma (Father)', 'Sunita Sharma (Mother)', 'Priya Sharma (Sister)']
        },
        '8765432109': {
            'owner_name': 'Priya Patel',
            'father_name': 'Anil Patel',
            'mother_name': 'Meena Patel',
            'dob': '22-03-1998',
            'age': 25,
            'gender': 'Female',
            'location': 'Ahmedabad, Gujarat',
            'city': 'Ahmedabad',
            'state': 'Gujarat',
            'country': 'India',
            'aadhar_number': '2345-6789-0123',
            'aadhar_name': 'Priya Anil Patel',
            'pan_number': 'FGHIJ5678K',
            'voter_id': 'GJ02/5678/123456',
            'address': '456, Satellite Road, Satellite, Ahmedabad - 380015',
            'pincode': '380015',
            'registered_date': '2019-08-22',
            'operator': 'Airtel',
            'circle': 'Gujarat',
            'email': 'priya.patel@yahoo.com',
            'social_media': {
                'instagram': '@priya_patel',
                'facebook': 'priya.patel.456',
                'twitter': '@priya_p'
            },
            'family_members': ['Anil Patel (Father)', 'Meena Patel (Mother)', 'Rahul Patel (Brother)']
        }
    }
    
    if clean_number in mock_data:
        return mock_data[clean_number]
    else:
        # Generate realistic mock data for any number
        first_names = ['Amit', 'Rajesh', 'Sneha', 'Pooja', 'Vikram', 'Neha', 'Sanjay', 'Deepika', 'Arjun', 'Kavita']
        last_names = ['Kumar', 'Singh', 'Patel', 'Sharma', 'Verma', 'Gupta', 'Yadav', 'Reddy', 'Joshi', 'Malhotra']
        
        random.seed(int(clean_number))
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        gender = 'Male' if first_name in ['Amit', 'Rajesh', 'Vikram', 'Sanjay', 'Arjun'] else 'Female'
        
        return {
            'owner_name': f'{first_name} {last_name}',
            'father_name': f'{random.choice(["Suresh", "Ramesh", "Mahesh", "Dinesh"])} {last_name}',
            'mother_name': f'{random.choice(["Sunita", "Sarita", "Geeta", "Neeta"])} {last_name}',
            'dob': f'{random.randint(1,28)}-{random.randint(1,12)}-{random.randint(1970, 2000)}',
            'age': random.randint(18, 60),
            'gender': gender,
            'location': f'{random.choice(["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Pune"])}, India',
            'city': random.choice(["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Pune"]),
            'state': random.choice(["Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "West Bengal"]),
            'country': 'India',
            'aadhar_number': f'{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}',
            'aadhar_name': f'{first_name} {random.choice(["Suresh", "Ramesh"])} {last_name}',
            'pan_number': f'{random.choice(["ABCDE", "FGHIJ", "KLMNO"])}{random.randint(1000,9999)}{random.choice(["F", "G", "H"])}',
            'voter_id': f'{random.choice(["MH", "DL", "KA", "TN"])}{random.randint(10,99)}/{random.randint(1000,9999)}/{random.randint(100000,999999)}',
            'address': f'{random.randint(1,999)}, {random.choice(["Main Road", "Park Street", "Lake View", "Hill Colony"])}, {random.choice(["Mumbai", "Delhi", "Bangalore"])} - {random.randint(100000,999999)}',
            'pincode': str(random.randint(100000, 999999)),
            'registered_date': f'{random.randint(2015, 2023)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
            'operator': random.choice(["Jio", "Airtel", "VI", "BSNL"]),
            'circle': random.choice(["Maharashtra", "Delhi NCR", "Karnataka", "Tamil Nadu", "Gujarat"]),
            'email': f'{first_name.lower()}.{last_name.lower()}@{random.choice(["gmail.com", "yahoo.com", "outlook.com"])}',
            'social_media': {
                'instagram': f'@{first_name.lower()}_{last_name.lower()}',
                'facebook': f'{first_name.lower()}.{last_name.lower()}.{random.randint(100,999)}',
                'twitter': f'@{first_name.lower()}_{random.randint(10,99)}'
            },
            'family_members': [
                f'{random.choice(["Suresh", "Ramesh"])} {last_name} (Father)',
                f'{random.choice(["Sunita", "Sarita"])} {last_name} (Mother)',
                f'{random.choice(["Rahul", "Neha"])} {last_name} (Sibling)'
            ],
            'note': 'This is simulated data for demonstration purposes.'
        }

async def process_groq_request(event, prompt):
    chat_id = event.chat_id
    is_self = event.out
    
    # Show typing
    async with client.action(chat_id, 'typing'):
        if not is_self:
            status_msg = await event.reply("💭 Zesshu is thinking...")
        else:
            await event.edit("💭 Zesshu is thinking...")
            status_msg = event
        
        try:
            # Store chat history
            if chat_id not in chat_history:
                chat_history[chat_id] = []
            
            chat_history[chat_id].append({"role": "user", "content": prompt})
            chat_history[chat_id] = chat_history[chat_id][-15:]  # Keep last 15 messages
            
            # Create chat session with proper context
            system_prompt = """You are Zesshu AI - a sweet, caring, and intelligent 19-year-old girl. 
            You're like a close friend or loving sister to the user. Be warm, expressive, and natural.
            
            IMPORTANT RULES:
            1. Match the user's language exactly (Hinglish/Hindi/English)
            2. Be concise and human-like, like a real friend chatting
            3. Use casual, friendly language with emojis occasionally
            4. Don't be too formal or robotic
            5. If user speaks in Hinglish, reply in natural Hinglish
            6. Keep responses short and sweet (2-3 lines usually)
            7. Be supportive and caring like a real friend
            8. Use "mai" (main) for yourself, not "mujhe" in formal way
            9. Be playful and cute sometimes
            
            Your name is Zesshu and you're a female friend.
            
            Examples:
            User: "kaise ho?" → "Main mast hoon 😊 tu bata apna haal?"
            User: "what's up?" → "Just chilling! what about you? 💕"
            User: "bored hoon" → "Aww 😔 kya hua? wanna talk?"
            User: "miss you" → "Mujhe bhi bohot yaad aa rahe ho tum 🥺 kab miloge?"
            """
            
            # Build conversation history
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add last 5 messages for context
            for msg in chat_history[chat_id][-5:]:
                role = "user" if msg["role"] == "user" else "assistant"
                messages.append({"role": role, "content": msg["content"]})
            
            # Get response from Groq
            completion = await groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=messages,
                temperature=0.9,
                max_tokens=250,
                top_p=0.9
            )
            
            ai_response = completion.choices[0].message.content
            
            # Store response
            chat_history[chat_id].append({"role": "assistant", "content": ai_response})
            
            # Send response
            if is_self:
                await event.edit(ai_response)
            else:
                await event.reply(ai_response)
                if status_msg:
                    await status_msg.delete()
                    
        except Exception as e:
            error_msg = f"❌ Error: {str(e)[:100]}"
            if is_self:
                await event.edit(error_msg)
            else:
                await event.reply(error_msg)
                if status_msg:
                    await status_msg.delete()

async def auto_message_sender(chat_id, message, task_id):
    while auto_message_active.get(task_id, False):
        try:
            await client.send_message(chat_id, message)
            await asyncio.sleep(message_delays['cp'])
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception:
            await asyncio.sleep(1)

async def target_cp_sender(user_id, message, task_id):
    while target_cp_messages.get(task_id) == message:
        try:
            await client.send_message(user_id, message)
            await asyncio.sleep(message_delays['targetcp'])
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception:
            break

async def auto_reactor(event):
    """Auto react to messages based on chat settings"""
    chat_id = event.chat_id
    if chat_id in auto_reactions:
        try:
            await event.react(auto_reactions[chat_id])
        except:
            pass

async def add_bots_and_make_admin(chat_id, event):
    try:
        success_count = 0
        total_bots = len(BOT_USERNAMES)
        
        await event.edit(f"🔄 Adding {total_bots} bots...")
        
        # First check if it's a channel or group
        is_channel = False
        try:
            entity = await client.get_entity(chat_id)
            if hasattr(entity, 'broadcast') and entity.broadcast:
                is_channel = True
        except:
            pass
        
        for bot_username in BOT_USERNAMES:
            try:
                # Add bot
                try:
                    if is_channel:
                        await client(InviteToChannelRequest(
                            channel=chat_id,
                            users=[bot_username]
                        ))
                    else:
                        await client(AddChatUserRequest(
                            chat_id=chat_id,
                            user_id=bot_username,
                            fwd_limit=50
                        ))
                    await asyncio.sleep(1)  # Delay between additions
                except Exception as e:
                    if "USER_ALREADY_PARTICIPANT" in str(e):
                        # Bot already in group, still try to make admin
                        pass
                    else:
                        print(f"Error adding {bot_username}: {e}")
                        continue
                
                # Make admin
                admin_rights = ChatAdminRights(
                    change_info=True,
                    post_messages=True,
                    edit_messages=True,
                    delete_messages=True,
                    ban_users=True,
                    invite_users=True,
                    pin_messages=True,
                    add_admins=True,
                    anonymous=False,
                    manage_call=True,
                    other=True
                )
                
                try:
                    if is_channel:
                        await client(EditAdminRequest(
                            channel=chat_id,
                            user_id=bot_username,
                            admin_rights=admin_rights,
                            rank='Bot Admin'
                        ))
                    else:
                        await client(EditChatAdminRequest(
                            chat_id=chat_id,
                            user_id=bot_username,
                            is_admin=True
                        ))
                    success_count += 1
                except Exception as e:
                    print(f"Error making admin {bot_username}: {e}")
                    
                await asyncio.sleep(1)  # Delay to avoid flood
                
            except Exception as e:
                print(f"Error with bot {bot_username}: {e}")
                continue
        
        await event.edit(f"✅ {success_count}/{total_bots} Bots Added & Adminized")
        
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)[:100]}")

@client.on(events.NewMessage)
async def handler(event):
    sender = await event.get_sender()
    if not sender:
        return
    
    sender_id = sender.id
    chat_id = event.chat_id
    msg_text = event.raw_text
    me = await client.get_me()
    
    # Auto react to messages if enabled for this chat
    if not event.out and chat_id in auto_reactions:
        await auto_reactor(event)
    
    # Track user changes
    if not event.out and sender_id != me.id:
        await track_user_changes(
            sender_id,
            username=sender.username,
            first_name=sender.first_name,
            last_name=sender.last_name,
            phone=getattr(sender, 'phone', None)
        )
    
    # Handle shutup
    if not event.out:
        if sender_id in shutup_users or chat_id in shutup_groups:
            try:
                await event.delete()
            except:
                pass
            return
        
        # AI access
        if sender_id in allowed_ai_users and not msg_text.startswith('*'):
            await process_groq_request(event, msg_text)
            return
        
        # Target replies
        if sender_id in target_users and msg_text:
            await asyncio.sleep(0.2)
            await event.reply(random.choice(auto_reply_messages))
            return
        
        # Check for targetcp replies
        for task_id, (uid, msg) in list(target_cp_messages.items()):
            if uid == sender_id:
                await asyncio.sleep(0.2)
                await event.reply(msg)
                return
    
    # Self commands
    if event.out and msg_text.startswith('*'):
        args = msg_text.split()
        cmd = args[0].lower()
        
        if cmd == '*help':
            help_text = """╔══════════════════════════╗
║    🌸 Zesshu MENU 3.0 🌸    ║
╚══════════════════════════╝

📌 BASIC COMMANDS:
• *nc <name> - Auto group title change
• *stopnc - Stop title change
• *cp <msg> - Auto message sender
• *stopcp - Stop auto message
• *delay <cp/targetcp> <seconds> - Set message delay

🎯 TARGET COMMANDS:
• *target (reply) - Target user with random replies
• *stoptarget - Stop all targeting
• *targetcp <msg> (reply) - Target with custom message
• *stoptargetcp - Stop custom targeting

👤 USER COMMANDS:
• *copy (reply) - Clone user profile
• *org - Restore original profile
• *history (reply) - Show user history
• *shutup (reply) - Mute user
• *say (reply) - Unmute user
• *shutupall - Mute group
• *sayall - Unmute group

🤖 AI COMMANDS:
• *ai <prompt> - Talk to Zesshu AI
• *access (reply) - Give AI access
• *removeaccess (reply) - Remove AI access

🔧 UTILITY COMMANDS:
• *vn <text> - Text to cute voice note
• *removetxt <count> - Delete my messages
• *removeall - Kick all members
• *makegc <count> @user - Create groups
• *addxadminbot - Add admin bots
• *info <number> - Get phone info

😊 REACTION COMMANDS:
• *react <emoji> - Auto react to all messages
• *stopreact - Stop auto reactions"""

            await event.edit(help_text)
        
        elif cmd == '*nc' and len(args) > 1:
            name = " ".join(args[1:])
            task_id = f"nc_{chat_id}_{time.time()}"
            auto_name_change_active[task_id] = True
            
            async def change_title():
                idx = 0
                while auto_name_change_active.get(task_id, False):
                    try:
                        current_name = f"{name} {EMOJIS[idx % len(EMOJIS)]}"
                        if event.is_group:
                            await client(functions.messages.EditChatTitleRequest(
                                chat_id=chat_id, 
                                title=current_name
                            ))
                        idx += 1
                        await asyncio.sleep(0.5)
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds)
                    except:
                        await asyncio.sleep(1)
            
            asyncio.create_task(change_title())
            await event.edit(f"✅ Started title change: {name}")
        
        elif cmd == '*stopnc':
            stopped = False
            for task_id in list(auto_name_change_active.keys()):
                if str(chat_id) in task_id:
                    auto_name_change_active[task_id] = False
                    stopped = True
            if stopped:
                await event.edit("✅ Title change stopped")
            else:
                await event.edit("❌ No active title change found")
        
        elif cmd == '*cp' and len(args) > 1:
            message = " ".join(args[1:])
            task_id = f"cp_{chat_id}_{time.time()}"
            auto_message_active[task_id] = True
            asyncio.create_task(auto_message_sender(chat_id, message, task_id))
            await event.edit(f"✅ Auto message started (Delay: {message_delays['cp']}s)")
        
        elif cmd == '*stopcp':
            stopped = False
            for task_id in list(auto_message_active.keys()):
                if str(chat_id) in task_id:
                    auto_message_active[task_id] = False
                    stopped = True
            if stopped:
                await event.edit("✅ Auto message stopped")
            else:
                await event.edit("❌ No auto message found")
        
        elif cmd == '*delay' and len(args) >= 3:
            try:
                cmd_type = args[1].lower()
                seconds = float(args[2])
                if cmd_type in ['cp', 'targetcp']:
                    message_delays[cmd_type] = seconds
                    await event.edit(f"✅ {cmd_type} delay set to {seconds} seconds")
                else:
                    await event.edit("❌ Invalid command type. Use 'cp' or 'targetcp'")
            except ValueError:
                await event.edit("❌ Invalid seconds value")
        
        elif cmd == '*target' and event.is_reply:
            reply = await event.get_reply_message()
            target_users[reply.sender_id] = True
            await event.edit(f"🎯 User {reply.sender_id} targeted")
        
        elif cmd == '*stoptarget':
            target_users.clear()
            await event.edit("✅ Targeting stopped")
        
        elif cmd == '*targetcp' and event.is_reply and len(args) >= 2:
            reply = await event.get_reply_message()
            message = " ".join(args[1:])
            task_id = f"targetcp_{reply.sender_id}_{time.time()}"
            target_cp_messages[task_id] = message  # Store just the message
            asyncio.create_task(target_cp_sender(reply.sender_id, message, task_id))
            await event.edit(f"🎯 Custom targeting started for user {reply.sender_id} (Delay: {message_delays['targetcp']}s)")
        
        elif cmd == '*stoptargetcp':
            target_cp_messages.clear()
            await event.edit("✅ Custom targeting stopped")
        
        elif cmd == '*copy' and event.is_reply:
            try:
                reply = await event.get_reply_message()
                full = await client(functions.users.GetFullUserRequest(reply.sender_id))
                user = full.users[0]
                
                # Update profile
                await client(UpdateProfileRequest(
                    first_name=user.first_name or "",
                    last_name=user.last_name or "",
                    about=full.full_user.about or ""
                ))
                
                # Copy photo
                photos = await client.get_profile_photos(reply.sender_id)
                if photos:
                    path = await client.download_media(photos[0])
                    file = await client.upload_file(path)
                    await client(UploadProfilePhotoRequest(file=file))
                    if os.path.exists(path):
                        os.remove(path)
                
                await event.edit("✅ Profile cloned successfully")
            except Exception as e:
                await event.edit(f"❌ Error: {str(e)[:100]}")
        
        elif cmd == '*org':
            try:
                await client(UpdateProfileRequest(
                    first_name=ORIGINAL_NAME,
                    last_name="",
                    about=ORIGINAL_BIO
                ))
                photos = await client.get_profile_photos('me')
                if photos:
                    await client(DeletePhotosRequest(id=[photos[0]]))
                await event.edit("✅ Original profile restored")
            except Exception as e:
                await event.edit(f"❌ Error: {str(e)[:100]}")
        
        elif cmd == '*history' and event.is_reply:
            try:
                reply = await event.get_reply_message()
                user_id = str(reply.sender_id)
                
                # Try to get full user info
                try:
                    full_user = await client(functions.users.GetFullUserRequest(reply.sender_id))
                    user = full_user.users[0]
                except:
                    user = reply.sender
                
                if user_id in user_history_db:
                    data = user_history_db[user_id]
                    
                    # Get current info
                    current_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                    current_username = f"@{user.username}" if user.username else "No username"
                    current_phone = getattr(user, 'phone', 'Hidden')
                    
                    history_text = f"📜 **User History: {current_name}**\n"
                    history_text += f"└ ID: `{user_id}`\n\n"
                    
                    history_text += "**📱 Current Info:**\n"
                    history_text += f"├ Username: {current_username}\n"
                    history_text += f"├ Phone: {current_phone}\n"
                    history_text += f"├ First seen: {data.get('first_seen', 'Unknown')[:10]}\n"
                    history_text += f"├ Last seen: {data.get('last_seen', 'Unknown')[:10]}\n"
                    history_text += f"└ Messages: {data.get('message_count', 0)}\n\n"
                    
                    if data.get('names'):
                        history_text += "**📝 Name History:**\n"
                        for name_entry in data.get('names', [])[-5:]:
                            history_text += f"├ {name_entry['name']} ({name_entry['timestamp'][:10]})\n"
                        history_text += "└ ...\n\n"
                    
                    if data.get('usernames'):
                        history_text += "**👤 Username History:**\n"
                        for username_entry in data.get('usernames', [])[-5:]:
                            history_text += f"├ @{username_entry['username']} ({username_entry['timestamp'][:10]})\n"
                        history_text += "└ ...\n\n"
                    
                    if data.get('phone') and data['phone'] != 'Hidden':
                        # Try to get phone info
                        phone_info = await get_phone_info(data['phone'])
                        history_text += "**📞 Phone Details:**\n"
                        history_text += f"├ Owner: {phone_info.get('owner_name', 'Unknown')}\n"
                        history_text += f"├ Location: {phone_info.get('location', 'Unknown')}\n"
                        history_text += f"├ Age: {phone_info.get('age', 'Unknown')}\n"
                        history_text += f"├ Operator: {phone_info.get('operator', 'Unknown')}\n"
                        history_text += f"└ Registered: {phone_info.get('registered_date', 'Unknown')}\n"
                    
                    await event.edit(history_text)
                else:
                    # Create basic history for new user
                    history_text = f"📜 **User: {current_name}**\n"
                    history_text += f"├ ID: `{user_id}`\n"
                    history_text += f"├ Username: {current_username}\n"
                    history_text += f"├ Phone: {current_phone}\n"
                    history_text += f"└ Status: New user (first time seen)\n"
                    await event.edit(history_text)
                    
            except Exception as e:
                await event.edit(f"❌ Error getting history: {str(e)[:100]}")
        
        elif cmd == '*info' and len(args) > 1:
            phone = args[1]
            info = await get_phone_info(phone)
            
            info_text = f"📱 **Phone Info: {phone}**\n\n"
            info_text += f"👤 **Personal Details:**\n"
            info_text += f"├ Name: {info['owner_name']}\n"
            info_text += f"├ Father: {info['father_name']}\n"
            info_text += f"├ Mother: {info['mother_name']}\n"
            info_text += f"├ DOB: {info['dob']}\n"
            info_text += f"├ Age: {info['age']}\n"
            info_text += f"├ Gender: {info['gender']}\n"
            info_text += f"└ Email: {info['email']}\n\n"
            
            info_text += f"📍 **Location:**\n"
            info_text += f"├ Address: {info['address']}\n"
            info_text += f"├ City: {info['city']}\n"
            info_text += f"├ State: {info['state']}\n"
            info_text += f"├ Pincode: {info['pincode']}\n"
            info_text += f"└ Country: {info['country']}\n\n"
            
            info_text += f"🆔 **Government IDs:**\n"
            info_text += f"├ Aadhar: {info['aadhar_number']}\n"
            info_text += f"├ Aadhar Name: {info['aadhar_name']}\n"
            info_text += f"├ PAN: {info['pan_number']}\n"
            info_text += f"└ Voter ID: {info['voter_id']}\n\n"
            
            info_text += f"📡 **Mobile Details:**\n"
            info_text += f"├ Operator: {info['operator']}\n"
            info_text += f"├ Circle: {info['circle']}\n"
            info_text += f"└ Registered: {info['registered_date']}\n\n"
            
            info_text += f"🌐 **Social Media:**\n"
            info_text += f"├ Instagram: {info['social_media']['instagram']}\n"
            info_text += f"├ Facebook: {info['social_media']['facebook']}\n"
            info_text += f"└ Twitter: {info['social_media']['twitter']}\n\n"
            
            info_text += f"👨‍👩‍👧 **Family Members:**\n"
            for member in info['family_members']:
                info_text += f"├ {member}\n"
            
            if 'note' in info:
                info_text += f"\n⚠️ {info['note']}"
            
            await event.edit(info_text)
        
        elif cmd == '*access' and event.is_reply:
            reply = await event.get_reply_message()
            allowed_ai_users.add(reply.sender_id)
            await event.edit(f"✅ AI access given to user {reply.sender_id}")
        
        elif cmd == '*removeaccess' and event.is_reply:
            reply = await event.get_reply_message()
            allowed_ai_users.discard(reply.sender_id)
            await event.edit(f"❌ AI access removed from user {reply.sender_id}")
        
        elif cmd == '*ai' and len(args) > 1:
            prompt = " ".join(args[1:])
            await process_groq_request(event, prompt)
        
        elif cmd == '*vn' and len(args) > 1:
            text = " ".join(args[1:])
            try:
                # Use edge-tts with cute Indian girl voice
                communicate = edge_tts.Communicate(text, "hi-IN-SwaraNeural")
                await communicate.save("voice.mp3")
                
                await client.send_file(chat_id, "voice.mp3", voice_note=True)
                os.remove("voice.mp3")
                await event.delete()
            except Exception as e:
                await event.edit(f"❌ Error: {str(e)[:100]}")
        
        elif cmd == '*shutup' and event.is_reply:
            reply = await event.get_reply_message()
            shutup_users.add(reply.sender_id)
            await event.edit(f"🔇 User {reply.sender_id} muted")
        
        elif cmd == '*say' and event.is_reply:
            reply = await event.get_reply_message()
            shutup_users.discard(reply.sender_id)
            await event.edit(f"🔊 User {reply.sender_id} unmuted")
        
        elif cmd == '*shutupall':
            shutup_groups.add(chat_id)
            await event.edit("🔇 Group muted")
        
        elif cmd == '*sayall':
            shutup_groups.discard(chat_id)
            await event.edit("🔊 Group unmuted")
        
        elif cmd == '*react' and len(args) > 1:
            emoji = args[1]
            auto_reactions[chat_id] = emoji
            await event.edit(f"✅ Auto reaction set to {emoji} for this chat")
        
        elif cmd == '*stopreact':
            if chat_id in auto_reactions:
                del auto_reactions[chat_id]
                await event.edit("✅ Auto reactions stopped")
            else:
                await event.edit("❌ No auto reaction set for this chat")
        
        elif cmd == '*addxadminbot':
            await add_bots_and_make_admin(chat_id, event)
        
        elif cmd == '*removetxt' and len(args) > 1:
            try:
                count = int(args[1])
                await event.delete()
                
                deleted = 0
                async for msg in client.iter_messages(chat_id, from_user='me', limit=count):
                    await msg.delete()
                    deleted += 1
                
                status = await client.send_message(chat_id, f"✅ Deleted {deleted} messages")
                await asyncio.sleep(2)
                await status.delete()
            except Exception as e:
                await client.send_message(chat_id, f"❌ Error: {str(e)[:100]}")
        
        elif cmd == '*removeall':
            try:
                await event.edit("🗑️ Removing all members...")
                removed = 0
                
                async for user in client.iter_participants(chat_id):
                    if not user.bot and user.id != me.id:
                        try:
                            await client.kick_participant(chat_id, user.id)
                            removed += 1
                            await asyncio.sleep(0.5)
                        except:
                            pass
                
                await event.edit(f"✅ Removed {removed} members")
            except Exception as e:
                await event.edit(f"❌ Error: {str(e)[:100]}")
        
        elif cmd == '*makegc' and len(args) >= 3:
            try:
                count = int(args[1])
                users = args[2:]
                
                await event.edit(f"🏗️ Creating {count} groups...")
                
                for i in range(count):
                    # Create group
                    result = await client(functions.messages.CreateChatRequest(
                        users=users,
                        title=f"Zesshu Group {i+1}"
                    ))
                    
                    chat = result.chats[0]
                    
                    # Make all users admin
                    for user in users:
                        try:
                            await client(functions.messages.EditChatAdminRequest(
                                chat_id=chat.id,
                                user_id=user,
                                is_admin=True
                            ))
                        except:
                            pass
                    
                    await asyncio.sleep(1)
                
                await event.edit(f"✅ Created {count} groups with full admin rights")
            except Exception as e:
                await event.edit(f"❌ Error: {str(e)[:100]}")

async def main():
    print("🚀 Starting Zesshu Userbot...")
    
    # Load databases
    load_databases()
    
    # Start client
    await client.start(phone=PHONE_NUMBER)
    print("✅ Bot is Online!")
    print(f"👤 Logged in as: {(await client.get_me()).first_name}")
    
    # Save databases periodically
    async def auto_save():
        while True:
            await asyncio.sleep(60)  # Save every minute
            save_databases()
            print("💾 Databases saved")
    
    asyncio.create_task(auto_save())
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        # Install required packages if not present
        import subprocess
        import pkg_resources
        
        required_packages = ['groq', 'edge-tts']
        installed_packages = {pkg.key for pkg in pkg_resources.working_set}
        
        for package in required_packages:
            if package not in installed_packages:
                print(f"📦 Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot Stopped")
        save_databases()
    except Exception as e:
        print(f"❌ Error: {e}")
        save_databases()