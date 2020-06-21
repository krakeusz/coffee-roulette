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
TODO


