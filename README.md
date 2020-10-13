# Script to export members Telegram Groups and Channels to a CSV file and to add members to Telegram Groups or Channels.

> Exporting and adding members to channels requires the user from which the script is launched to be a Channel admin.

### Install dependencies

This script requires [telethon](https://pypi.org/project/Telethon/) ( [github](https://github.com/LonamiWebs/Telethon) ) to run.

You'd need python3 and pip3 installed and available in your PATH.

Run `pip3 install -r requirements.txt` from the projects root directory.

### Telegram Configuration

1. To run it you need to generate API credentials for your Telegram user, you can do it [here](https://core.telegram.org/api/obtaining_api_id), and access your already created ones [here](https://my.telegram.org/apps)
2. Copy the example credentials file - `credentials.example.json` to `credentials.json`

   The filename has to be exactly `credentials.json` because the name is hard-coded into the script.
3. Add the credentials obtained in Step 1 to `credentials.json`

### Running the Script

The script is mostly interactive. It can be started in the most basic form :
```bash
python3 telethon-bot-add-users-to-groups.py
```

The script has 3 main features :
- Export users from group
- Add users to group
- print CSV

#### Export users

The export feature writes a comma-separated values (CSV) file with the filename of the form `<group-name>-members.csv`. The CSV can then later be used as an input file to the add users or print CSV features.

#### Add users to groups

Users can be added using:
- **Username**: Gets temporarily banned with less requests.
- **User ID**: Gets temporarily banned with more requests.

> Temporary restrictions may last for up to a day.

The script expects a CSV file with input values ( one per line ).

The CSV file **MUST** have a header with at least one of the following fields
- `username` for adding by username
- `user id` for adding by user ID

Header values are compatible with the CSV that is generated with the same script.

Note : The values for the header is hard-coded in the application and is case-sensitive. The values must be in lower-case only

##### Auto-detect add mode

The script is capable of auto-detecting the add mode if the CSV file has only one column and the header is appropriately named as mentioned above

##### Resume capability

The script can also smartly resume from a certain offset point. This is useful when resuming operation after a cooldown period of a `PeerFloodError`. The script prints the command after handling a `PeerFloodError`. It looks similar to :
```
python3 telethon-bot-add-users-to-groups.py members.csv 1234567890 1 50
```
where the arguments correspond to :

```
argv[1] => input_file      | input CSV file
argv[2] => target_group.id | ID of group to add users
argv[3] => add_mode        | add by [1]. username or [2]. user ID
argv[4] => start_index     | offset to restart adding users
```

While the script is interactive by default, using this argument structure can trigger a non-interactive automatic add mode with the given parameters.
