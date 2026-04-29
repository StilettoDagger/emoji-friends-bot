# Emoji Friends Discord Bot

A Discord bot that allows users to assign an emoji to their username. When users join a Voice Channel with "emoji status" enabled, their assigned emoji is automatically added to the channel's status.

## Features

- `/set_emoji <emoji>`: Assign your personal emoji.
- `/toggle_status`: Enable or disable emoji status tracking for the voice channel you are currently in.
- **Dynamic Updates**: Statuses update in real-time as users join or leave the VC.
- **Persistence**: Remembers user emojis and channel settings across restarts using SQLite.

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**:
   - Rename `.env.template` to `.env`.
   - Add your Discord Bot Token to the `.env` file.

3. **Bot Permissions**:
   - Ensure the bot has the following OAuth2 Scopes: `bot`, `applications.commands`.
   - Ensure the bot has the following Bot Permissions: `Manage Channels` (to edit VC status), `Read Messages/View Channels`, `Connect`, `Speak`.
   - **Privileged Gateway Intents**: Enable `Server Members Intent` and `Voice State Intent` in the Discord Developer Portal.

4. **Run the Bot**:
   ```bash
   python bot.py
   ```

## Development Workflow

This project was built with a clean git history:
1. Initial scaffolding and git configuration.
2. SQLite database logic implementation.
3. Core bot logic including slash commands and voice state listeners.
