# Script to export members Telegram Groups and Channels to a CSV file and to add members to Telegram Groups or Channels.

> Exporting and adding members to channels requires the user from which the script is launched to be a Channel admin.

### Install dependencies

You'd need python3 and pip3 installed and available in your PATH.

Run `pip3 install -r requirements.txt` from the projects root directory.

### Telegram Configuration

1. To run it you need to generate API credentials for your Telegram user, you can do it [here](https://core.telegram.org/api/obtaining_api_id), and access your already created ones [here](https://my.telegram.org/apps)
2. Copy the example credentials file - `credentials.example.json` to `credentials.json`

   The filename has to be exactly `credentials.json` because the name is hard-coded into the script.
3. Add the credentials obtained in Step 1 to `credentials.json`

### Export users
Just follow the instructions in the script after running it from your the shell.

### Add users to groups

Users can be added using:
- **Username**: Gets temporarily banned with less requests.
- **User ID**: Gets temporarily banned with more requests.

> Temporarily bans last for up to a day in my experience.

Adding users by Username expects a CSV file with one username per line.
Adding users by User ID expects a CSV file such as: `username,user_id,user_access_hash`

> No headers are expected in the CSV files

Once you have your CSV prepared, just follow the instructions in the script.
