from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest, AddChatUserRequest
from telethon.tl.types import InputPeerEmpty, Chat, InputPeerChat, ChatForbidden, Channel, InputPeerChannel, ChannelForbidden
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError
from telethon.tl.functions.channels import InviteToChannelRequest
import sys
import csv
import traceback
import time
import random
import re
import json

def log_into_telegram():
    credential_file = 'credentials.json' # Relative path of file which consists Telegram credentials - api_id, api_hash, phone

    try:
        credentials = json.load(open(credential_file, 'r'))
    except:
        print('credentials.json file not present in the directory')
        exit(2)

    try:
        client = TelegramClient(credentials['phone'], credentials['api_id'], credentials['api_hash'])
        client.connect()
    except:
        print('Could not create `TelegramClient`, please check your credentials in credentials.json')
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


    g_index = int(input("Choose group: "))
    target_group = chats[g_index]
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
        print(target_group.__class__.__name__, "is not a valid InputPeer")
        exit(5)

    while not mode_set:
        try:
            print('Add By:\n1. username\n2. user ID ( requires access hash to be in CSV )')
            mode = int(input('How do you want to add users? '))
            mode_set = True
        except ValueError:
            print('ValueError: invalid literal\n')
            continue

        if mode not in [1, 2]:
            print('Invalid Mode Selected. Try Again.\n')
            mode_set = False

    with open(input_file, encoding='UTF-8') as f:
        users = csv.DictReader(f, delimiter=",", lineterminator="\n")

        for user in users:
            print ("Adding {}".format(user['username']))
            if mode == 1:
                if user['username'] == "":
                    continue
                user_to_add = client.get_input_entity(user['username'])
            elif mode == 2:
                user_to_add = client.get_input_entity(int(user['user id']))
            else:
                sys.exit("Invalid Mode Selected. Please Try Again.")

            try:
                if isChannel:
                    client(InviteToChannelRequest(target_group_entity, [user_to_add]))
                else:
                    client(AddChatUserRequest(target_group_entity.chat_id, user_to_add, fwd_limit=1000000000))
                wait_time = random.randrange(60, 300)
                print("Waiting for", wait_time, "seconds...")
                time.sleep(wait_time)
            except PeerFloodError:
                print('Getting Flood Error from telegram. Script is stopping now. Please try again after some time.')
                exit(6)
            except UserPrivacyRestrictedError:
                print('Sorry, the user restricted who can add them to chats in their privacy settings.')
            except:
                traceback.print_exc()
                print("Unexpected Error")
                error_count += 1
                if error_count > 10:
                    sys.exit('too many errors')
                continue

def scrape_users(target_group, client):
    print('Scraping Members from', target_group.title)

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
    print('Members scraped successfully.')

def printCSV():
    input_file = sys.argv[1]
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


# print('Fetching Members...')
# all_participants = []
# all_participants = client.get_participants(target_group, aggressive=True)
print('What do you want to do:')
mode = int(input("Enter \n1-List users in a group\n2-Add users from CSV to Group (CSV must be passed as a parameter to the script\n3-Show CSV\n\nYour option:  "))

if mode == 1:
    client = log_into_telegram()
    target_group = select_group()
    scrape_users(target_group, client)
elif mode == 2:
    if len(sys.argv) < 2:
        print('did not get input CSV file\nplease pass the CSV file as argument to the script')
        exit(1)
    client = log_into_telegram()
    target_group = select_group()
    add_users_to_group(sys.argv[1], target_group, client)
elif mode == 3:
    printCSV()
