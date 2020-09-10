# coffee-roulette
A Django website for generating matches for coffee roulette, with Slack integration

## Introduction
'Coffee Roulette' is an initiative where people in a company are encouraged to get to know each other at a coffee meeting. Here's how it works:
1. The Coffee Roulette organizer informs the workers that the next roulette is going to be held.
2. Co-workers vote if they want to participate or not.
3. The organizer matches the co-workers in pairs.
4. The co-workers should meet at a coffee with the second person from the pair, at any time.

This web application facilitates organizing such Coffee Roulettes with minimal effort. For example, the organizer has a web interface where he/she can manage roulettes: start them, modify the participant list, and generate final matchings. The co-workers, on the other hand, can vote whether they want to take part in the event by posting votes on a Slack thread. Then, matchings (pairs) are found in a smart way, so that the users have a high chance of meeting different people with every new roulette. In the end, final participants are notified about the matches on Slack.

## Architecture sketch
![coffee roulette architecture diagram](/docs/coffee-roulette-architecture.svg)

From now on, 'Users' are people that can be matched in coffee roulette. 'Admin' is a person that organizes the roulette, and has more privileges. There can be more than one Admin in the system. If an Admin wants to take part in coffee too, he/she needs to create a separate User account for this purpose.

## Requirements
- A server that can run this Django application. This server doesn't need to be visible from public Internet, it only needs to be accessible by the admin(s) via web browser. The app has been tested on Windows, MacOS and Ubuntu Linux.
- (optional) A slack workspace where a custom Slack Bot will run. The bot will send voting invitation messages on a channel you choose, and private messages to the users that participate in the roulette. You will have enough Slack privileges to add this bot if you're the workspace owner. Note that Slack integration is optional. Given no Slack bot, the user votes can only be changed by the admin in web interface.

## Required Slack bot permissions (scopes)
The application has been tested only with all these permissions enabled in the bot configuration.
| Permission name | Slack detailed explanation | Our explanation |
| --------------- | -------------------------- | --------------- |
| channels:history | View messages and other content in public channels that Coffee Roulette has been added to | When a Coffee Roulette starts, users will vote. This scope allows the bot to read users' votes. |
| groups:history | View messages and other content in private channels that Coffee Roulette has been added to | This is similar to the above scope, but this works in private channels as well. |
| chat:write | Send messages as @coffeebot | This scope allows to create a new thread with initial message when a Coffee Roulette starts. |
| im:write | Start direct messages with people | When the matchings (pairs) are generated, the bot notifies each user about the results via IM. |
| users:read | View people in the workspace | This is only a prerequisite scope for 'users:read.email'. |
| users:read.email | View email addresses of people in the workspace | Thanks to this scope, the bot can corellate email addresses of users, provided by the Admin and stored in Sqlite database, with the users on Slack. Without it, the Admin would need to manually look at user IDs on Slack and type them into the web app. With this permission, he only needs to provide emails (and visible user names). |

It's worth noting that the bot sees (and can write to) only the channels to which he was explicitly added. In practice, the bot uses only one channel, specified by the Admin.

## Installation
### Web app

1. Download the ZIP from the master branch and unpack it, or clone the git repository.
2. Install Python3. This project has been tested with Python 3.8. Note: on \*nix, you should use 'python3' and 'pip3' commands instead of 'python' and 'pip'.
3. Install SQLite and, possibly, python database bindings. You could use a different database, but only SQLite has been tested against. This is described in [Django documentation on databases](https://docs.djangoproject.com/en/3.0/topics/install/#get-your-database-running).
4. Go to the root folder of repository (or unpacked archive), then create a virtual Python environment:
```bash
cd coffee-roulette
python -m venv .venv
```
5. Activate the virtualenv.
- On Windows:
```bash
.venv\Scripts\activate.bat
```
- On Linux/MacOS:
```bash
source .venv/bin/activate
```
6. Install required python packages:
```bash
pip install -r requirements.txt
```
7. Create your secret key for Django:
```bash
cd src/roulette
cp settings/django_local.example settings/django_local.py
python
>>> from django.core.management.utils import get_random_secret_key
>>> get_random_secret_key()
### Copy the output into settings/django_local.py, under SECRET_KEY.
>>> exit()
```
8. Check if everything went OK so far by running tests:
```bash
python manage.py test
```
9. Create the database tables:
```bash
python manage.py migrate
```
10. Create a Django superuser. You can use this account to manage the website, or the roulettes. You can always create new admin accounts if you want.
```bash
python manage.py createsuperuser
```
11. Now it's time to start the server. For testing purposes, you can use built-in Django webserver, which is simple but not really safe or robust.
```bash
python manage.py runserver
```
This server will listen by default on port 8000.
For real deployment, consult [Django documentation on deployment](https://docs.djangoproject.com/en/3.0/howto/deployment/).

12. Open your browser and go to localhost:8000 (assuming you started the built-in server), go and look around.
13. You'll want to add new users (go to 'Other settings' link in the top-right corner of any page), and then create a roulette! Remember that when the voting deadline comes, you need to initiate the matching by hand.

### Slack integration (optional)
Thanks to Slack integration, users will be able to vote, instead of relying on admin.
First, you'll create a new Slack App, which will be used as a bot. The preferred installation scheme is the workspace installation. Your bot
(app) will be installed only to your Slack workspace. If ever in doubt, check out [the official Slack tutorial about bots](https://api.slack.com/bot-users#getting-started). Please note that the Slack administration GUI changes from time to time, so you might see different options then what's in this README or even what's in official documentation.

You should have enough Slack permissions to be able to install an app. These permissions are configured by your workspace's Owners and possibly Admins, under workspace settings, App Directory, "Require App Approval".

1. Start by [creating your Slack App](https://api.slack.com/apps/new). Suggested App Name is 'Coffee Roulette'. Choose your workspace as Development Slack Workspace.
2. Configure your bot permissions inside the Slack app.

Under your app settings, click the tab "App home", then "Review Scopes to Add". Under "Bot Token Scopes", add all the permissions mentioned [earlier in this README](#required-slack-bot-permissions-scopes)</a>.

3. Change the bot's names.

Again, go to "App home". You should be able to edit Display Name (suggested: Coffee Bot), username (suggested: coffeebot).

4. Change your bot icon.

Go to "Basic information", "Display information". An example icon is [in the repository](/src/roulette/matcher/static/matcher/local_cafe-512px.png).

5. Finally, install the bot to your workspace.

Go to "OAuth & Permissions", then "Install App to Workspace". Review the permissions, and "Allow". You should see the Bot User OAuth Access Token. This needs to be
inserted into coffee-roulette web application.

Go to coffee-roulette website, enter "Slack settings" in the top navigation bar, then "connect now". Type in the token
from Slack, and choose a channel where bot will communicate its messages. If it's a new channel, you need to create it on Slack. You can reuse one of your old channels,
if you want to.

Now you only need to add the bot to your channel on Slack - it needs Slack permission. Go to Slack workspace, under "Apps" select your bot, "Details", "More", "Add this app to a channel...". Alternatively, if that method doesn't work, try going to the Slack, enter your channel, and click the "Add Bot" option.

6. (suggested) Connect your admin coffee-roulette account with Slack account. This will let you receive Slack IMs in case of errors, and test if Slack integration works.

In coffee-roulette web page, go to 'Other settings', 'Users', select your username, and type "Slack user ID" at the bottom. You can get your ID by going to your Slack web client, click on your user name, then "View profile", "More", "Copy member ID".

Then, go to main coffee-roulete web page, under "Slack settings", click "Send a test message to all admins on Slack". You should receive a message from your new bot.

