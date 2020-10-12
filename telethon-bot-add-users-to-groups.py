import sys
import csv
import traceback
import time
import random
import re
import json

from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest, AddChatUserRequest
from telethon.tl.types import InputPeerEmpty, Chat, InputPeerChat, ChatForbidden, Channel, InputPeerChannel, ChannelForbidden
from telethon.errors.rpcerrorlist import PeerFloodError, InputUserDeactivatedError, UserNotMutualContactError, UserPrivacyRestrictedError

# Set up logging
import logging
logger = logging.getLogger('telethon-add-users-to-groups')
# logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
format = logging.Formatter('%(levelname)s | %(asctime)s | %(message)s')
ch.setFormatter(format)
logger.addHandler(ch)

def log_into_telegram():
    credential_file = 'credentials.json' # Relative path of file which consists Telegram credentials - api_id, api_hash, phone

    try:
        credentials = json.load(open(credential_file, 'r'))
    except FileNotFoundError:
        logger.error('credentials file not found')
        exit(2)

    try:
        client = TelegramClient(credentials['phone'], credentials['api_id'], credentials['api_hash'])
        client.connect()
    except ConnectionError as e:
        logger.error("%s: %s", e.__class__.__name__, e)
        exit(3)

    return client

def select_group():
    chats = []
    last_date = None
    chunk_size = 200
    dialog_iterator = 0

    for dialog in client.iter_dialogs(
            offset_date=last_date,
            offset_id=0,
            offset_peer=InputPeerEmpty(),
            limit=chunk_size,
        ):

        if dialog.is_group:
            if not isinstance(dialog.entity, ChatForbidden) and not isinstance(dialog.entity, ChannelForbidden):
                print(str(dialog_iterator) + '. ' + dialog.entity.title)
                chats.append(dialog.entity)
                dialog_iterator += 1

    try:
        g_index = int(input("Choose group: "))
        target_group = chats[g_index]
    except IndexError as e:
        logger.error("%s: %s", e.__class__.__name__, e)
        exit(4)
    except ValueError:
        logger.error('ValueError: invalid literal')
        exit(4)

    print('\n\nChosen group: ' + target_group.title)
    return target_group

def add_users_to_group(input_file, target_group, client):
    error_count = 0
    mode_set = False
    isChannel = False

    # convert target_group to InputPeer
    if isinstance(target_group, Chat):
        target_group_entity = InputPeerChat(target_group.id)
        isChannel = False
    elif isinstance(target_group, Channel):
        target_group_entity = InputPeerChannel(target_group.id, target_group.access_hash)
        isChannel = True
    else:
        logger.error("%s is not a valid InputPeer", target_group.__class__.__name__)
        exit(5)

    while not mode_set:
        try:
            print('Add By:\n1. username\n2. user ID ( requires access hash to be in CSV )')
            mode = int(input('How do you want to add users? '))
            mode_set = True
        except:
            logger.error('ValueError: invalid literal \n')
            continue

        if mode not in [1, 2]:
            logger.error('Invalid Mode Selected. Try Again. \n')
            mode_set = False

    with open(input_file, encoding='UTF-8') as f:
        users = csv.DictReader(f, delimiter=",", lineterminator="\n")

        for user in users:
            logger.debug('### ===== BEGIN USER ===== ###')
            logger.debug(user)

            if mode == 1:
                if user['username'] == "":
                    logger.error("user doesn't have a username")
                    continue
                user_to_add = client.get_input_entity(user['username'])
                logger.debug("Adding @%s", user['username'])
            elif mode == 2:
                try:
                    user_to_add = client.get_input_entity(int(user['user id']))
                except:
                    logger.error("User ID %s is invalid", user['user id'])
            else:
                sys.exit("Invalid Mode Selected. Please Try Again.")
            logger.debug(user_to_add)

            try:
                if isChannel:
                    updates = client(InviteToChannelRequest(target_group_entity, [user_to_add]))
                    logger.debug(updates.stringify())
                else:
                    updates = client(AddChatUserRequest(target_group_entity.chat_id, user_to_add, fwd_limit=1000000000))
                    logger.debug(updates.stringify())
                wait_time = random.randrange(60, 300)
                logger.debug("Waiting for %s seconds", wait_time)
                time.sleep(wait_time)
            except (
                    InputUserDeactivatedError,
                    UserNotMutualContactError,
                    UserPrivacyRestrictedError
                   ) as e:
                message = re.search('(?<=user).*', str(e)).group(0)
                logger.error("%s: %s%s", e.__class__.__name__, user_to_add, message)
            except PeerFloodError as e:
                logger.error("%s: %s", e.__class__.__name__, e)
                logger.info("to continue from the last position, run:\n\tpython3 %s %s %s %s %s",
                    sys.argv[0],
                    input_file,
                    target_group.id,
                    mode,
                    user_add_count
                )
                exit(6)
            except Exception as e:
                logger.exception(e.__class__.__name__)
                error_count += 1
                if error_count > 10:
                    sys.exit('too many errors')
                continue

            logger.debug('### ===== END USER ===== ### \n')

def scrape_users(target_group, client):
    logger.debug('Scraping Members from %s', target_group.title)

    sanitized_group_name = re.sub(' ', '-', str.lower(target_group.title).encode('ascii', 'ignore').decode('ascii').strip())
    if sanitized_group_name:
        members_file_name = sanitized_group_name + '-members.csv'
    else:
        members_file_name = 'group-members.csv'

    with open(members_file_name, 'w', encoding='UTF-8') as f:
        writer = csv.writer(f,delimiter=",",lineterminator="\n")
        writer.writerow(['username','user id', 'access hash','name','group', 'group id'])
        for user in client.iter_participants(int(target_group.id)):
            if user.username:
                username= user.username
            else:
                username= ""
            if user.first_name:
                first_name= user.first_name
            else:
                first_name= ""
            if user.last_name:
                last_name= user.last_name
            else:
                last_name= ""
            name= (first_name + ' ' + last_name).strip()
            writer.writerow([username,user.id,user.access_hash,name,target_group.title, target_group.id])      
    logger.debug('Members scraped successfully.')

def printCSV(input_file):
    users = []
    with open(input_file, encoding='UTF-8') as f:
        rows = csv.reader(f,delimiter=",",lineterminator="\n")
        next(rows, None)
        for row in rows:
            user = {}
            user['username'] = row[0]
            user['id'] = int(row[1])
            user['access_hash'] = int(row[2])
            users.append(user)
            print(row)
            print(user)
    sys.exit('FINITO')

mode = 0
mode_set = False

while not mode_set:
    try:
        print('Actions\n1. Scrape users from group\n2. Add users from CSV to Group (CSV must be passed as argument)\n3. Show CSV\n4. Quit')
        mode = int(input("What do you want to do? "))
        mode_set = True
    except ValueError as e:
        logger.error('ValueError: invalid literal')
        continue

if mode == 1:
    client = log_into_telegram()
    target_group = select_group()
    scrape_users(target_group, client)
elif mode == 2:
    if len(sys.argv) < 2:
        logger.error('did not get input CSV file as argument')
        exit(1)
    client = log_into_telegram()
    target_group = select_group()
    add_users_to_group(sys.argv[1], target_group, client)
elif mode == 3:
    if len(sys.argv) < 2:
        logger.error('did not get input CSV file as argument')
        exit(1)
    printCSV(sys.argv[1])
elif mode == 4:
    exit()
