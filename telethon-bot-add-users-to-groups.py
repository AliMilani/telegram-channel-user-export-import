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
logger.setLevel(logging.INFO)
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
    global client

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

def add_users_to_group(input_file, target_group, add_mode = 0, start_index = 0):
    global client

    mode = 0
    error_count = 0
    user_add_count = 0

    mode_set = False
    isChannel = False

    # validate mode when in auto-add mode
    if add_mode in [1, 2]:
        mode = int(add_mode)
        mode_set = True
    elif add_mode != 0:
        logger.error('Invalid Add Mode')

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
            print('Add By:\n1. username\n2. user ID ( requires access hash to be in CSV )\n3. Auto-detect from CSV header')
            mode = int(input('How do you want to add users? '))
            mode_set = True
        except:
            logger.error('ValueError: invalid literal \n')
            continue

        # auto-detect mode from CSV header
        if mode == 3:
            csv_header_fieldnames = csv.DictReader(
                                        open(input_file, encoding='UTF-8'),
                                        delimiter=",",
                                        lineterminator="\n",
                                        skipinitialspace=True
                                    ).fieldnames
            logger.debug(csv_header_fieldnames)
            if len(csv_header_fieldnames) > 1:
                logger.error('CSV file has more than one column. Cannot auto-detect add mode. \n')
                mode_set = False
                continue
            elif csv_header_fieldnames[0] == 'username':
                mode = 1
            elif csv_header_fieldnames[0] == 'user id':
                mode = 2
            else:
                logger.error('Could not detect add mode from CSV file. Try again. \n')
                mode_set = False
                continue

        if mode not in [1, 2]:
            logger.error('Invalid Mode Selected. Try Again. \n')
            mode_set = False

    with open(input_file, encoding='UTF-8') as f:
        # convert csv dict into a list
        # to index it by an integer
        # to be able to resume from arbitrary points
        # https://stackoverflow.com/a/55790863
        users = list(csv.DictReader(f, delimiter=",", lineterminator="\n"))
        for i in range(start_index, len(users)):
            user = users[i]

            logger.debug('### ===== BEGIN USER ===== ###')
            logger.debug(user)

            if mode == 1:
                if user['username'] == "":
                    logger.warning("%s doesn't have a username", user)
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
                user_add_count += 1
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
                    start_index + user_add_count
                )
                exit(6)
            except Exception as e:
                logger.exception(e.__class__.__name__)
                error_count += 1
                if error_count > 10:
                    sys.exit('too many errors')
                continue

            logger.debug('### ===== END USER ===== ### \n')

def export_users(target_group):
    global client

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

if 2 < len(sys.argv) <= 5:
    logger.debug('got more than 1 argument; auto-selecting add mode')
    mode = 2
    mode_set = True

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
    export_users(target_group)
elif mode == 2:
    add_mode = 0
    start_index = 0

    if len(sys.argv) < 2:
        logger.error('did not get input CSV file as argument')
        exit(1)
    elif len(sys.argv) > 5:
        logger.warning('too many arguments. using only first 5')

    input_file = sys.argv[1]

    client = log_into_telegram()
    if len(sys.argv) > 2:
        target_group = client.get_entity(int(sys.argv[2]))
    else:
        target_group = select_group()

    if len(sys.argv) > 3:
        add_mode = int(sys.argv[3])
    if len(sys.argv) > 4:
        start_index = int(sys.argv[4])

    add_users_to_group(input_file, target_group, add_mode, start_index)
elif mode == 3:
    if len(sys.argv) < 2:
        logger.error('did not get input CSV file as argument')
        exit(1)
    printCSV(sys.argv[1])
elif mode == 4:
    exit()
