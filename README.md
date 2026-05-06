# Emoji Friends Discord Bot

A Discord bot that allows users to assign an emoji and a custom text status to their username. When users join a Voice Channel with "emoji status" enabled, the bot dynamically generates and updates a Tamagotchi-inspired "virtual room" image showing all users' emojis and text bubbles!

## Features

- **Tamagotchi-Style Virtual Environment**: Generates a composite, retro-inspired virtual room image of all users in a VC, rendering their assigned Unicode or Custom Discord emojis.
- **Dynamic Teleportation Updates**: The bot automatically refreshes the virtual room image every 10 seconds, causing user emojis to teleport around the room, keeping the environment feeling alive.
- **Text Speech Bubbles**: Users can set an optional text status that renders as a speech bubble above their emoji in the virtual room.
- **Performance Optimized**: Uses in-memory caching to prevent redundant downloading of emoji images from Twemoji or Discord CDNs.
- **Persistence**: Remembers user emojis and channel settings across restarts using SQLite.

### Slash Commands
- `/set_status <emoji> [text]`: Assign an emoji and optional text.
- `/clear_status`: Remove your assigned status.
- `/status [channel]`: Generates and displays the virtual room image for the VC.
- `/toggle_status [channel]`: Enable or disable dynamic status tracking for a voice channel.
- `/whoami`: Get your assigned emoji and text.
- `/whois <user>`: Get a user's assigned emoji and text.
- `/top_emojis`: Show the top 10 most used emojis by users in the server.

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

## Running with Docker (Recommended for 24/7)

If you want the bot to run in the background and restart automatically:

1. **Install Docker and Docker Compose**.
2. **Setup .env**: Ensure your `.env` file contains your `DISCORD_TOKEN`.
3. **Build and Start**:
   ```bash
   docker-compose up -d --build
   ```
4. **View Logs**:
   ```bash
   docker logs -f emoji-friends-bot
   ```
5. **Stop**:
   ```bash
   docker-compose down
   ```

The database will be persisted in your project folder as `database.db`.

## Development Workflow

This project was built with a clean git history:
1. Initial scaffolding and git configuration.
2. SQLite database logic implementation.
3. Core bot logic including slash commands and voice state listeners.
