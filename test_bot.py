import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import discord

# Import the commands from the bot module.
from bot import set_emoji, unset_emoji, status, toggle_status

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = 12345
    interaction.user.voice = None
    interaction.user.guild_permissions = MagicMock()
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    return interaction

@pytest.mark.asyncio
@patch('bot.database')
@patch('bot.update_vc_status', new_callable=AsyncMock)
async def test_set_emoji_valid(mock_update_vc_status, mock_db, mock_interaction):
    # Setup voice state for update_vc_status to trigger
    mock_interaction.user.voice = MagicMock()
    mock_interaction.user.voice.channel = MagicMock()
    
    await set_emoji.callback(mock_interaction, '😀')
    
    # Verify db called
    mock_db.set_user_emoji.assert_called_once_with(12345, '😀')
    # Verify update_vc_status called
    mock_update_vc_status.assert_called_once_with(mock_interaction.user.voice.channel)
    # Verify response sent
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert '😀' in args[0]

@pytest.mark.asyncio
@patch('bot.database')
async def test_set_emoji_invalid(mock_db, mock_interaction):
    await set_emoji.callback(mock_interaction, '😀😃')
    
    # Verify db NOT called
    mock_db.set_user_emoji.assert_not_called()
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'exactly **one** valid emoji' in args[0]

@pytest.mark.asyncio
@patch('bot.database')
@patch('bot.update_vc_status', new_callable=AsyncMock)
async def test_unset_emoji(mock_update_vc_status, mock_db, mock_interaction):
    # Setup voice state
    mock_interaction.user.voice = MagicMock()
    mock_interaction.user.voice.channel = MagicMock()
    
    await unset_emoji.callback(mock_interaction)
    
    mock_db.set_user_emoji.assert_called_once_with(12345, None)
    mock_update_vc_status.assert_called_once_with(mock_interaction.user.voice.channel)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'removed' in args[0]

@pytest.mark.asyncio
@patch('bot.database')
async def test_status_enabled(mock_db, mock_interaction):
    mock_db.is_vc_enabled.return_value = True
    
    mock_channel = MagicMock(spec=discord.VoiceChannel)
    mock_channel.id = 999
    mock_channel.name = "Test Channel"
    
    await status.callback(mock_interaction, mock_channel)
    
    mock_db.is_vc_enabled.assert_called_once_with(999)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert '**enabled**' in args[0]

@pytest.mark.asyncio
@patch('bot.database')
async def test_status_no_channel(mock_db, mock_interaction):
    # No channel provided, and user not in a voice channel
    mock_interaction.user.voice = None
    
    await status.callback(mock_interaction, None)
    
    mock_db.is_vc_enabled.assert_not_called()
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'specify a channel or join one' in args[0]

@pytest.mark.asyncio
@patch('bot.database')
@patch('bot.update_vc_status', new_callable=AsyncMock)
async def test_toggle_status_enable(mock_update_vc_status, mock_db, mock_interaction):
    mock_db.toggle_vc_status.return_value = True # Becomes enabled
    
    mock_channel = AsyncMock(spec=discord.VoiceChannel)
    mock_channel.id = 999
    mock_channel.name = "Test Channel"
    mock_interaction.user.guild_permissions.manage_channels = True
    
    await toggle_status.callback(mock_interaction, mock_channel)
    
    mock_db.toggle_vc_status.assert_called_once_with(999)
    mock_update_vc_status.assert_called_once_with(mock_channel)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert '**enabled**' in args[0]

@pytest.mark.asyncio
@patch('bot.database')
async def test_toggle_status_disable(mock_db, mock_interaction):
    mock_db.toggle_vc_status.return_value = False # Becomes disabled
    
    mock_channel = AsyncMock(spec=discord.VoiceChannel)
    mock_channel.id = 999
    mock_channel.name = "Test Channel"
    mock_interaction.user.guild_permissions.manage_channels = True
    
    await toggle_status.callback(mock_interaction, mock_channel)
    
    mock_db.toggle_vc_status.assert_called_once_with(999)
    mock_channel.edit.assert_called_once_with(status=None)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert '**disabled**' in args[0]

@pytest.mark.asyncio
@patch('bot.database')
async def test_toggle_status_no_permissions(mock_db, mock_interaction):
    mock_channel = AsyncMock(spec=discord.VoiceChannel)
    mock_interaction.user.guild_permissions.manage_channels = False
    
    await toggle_status.callback(mock_interaction, mock_channel)
    
    mock_db.toggle_vc_status.assert_not_called()
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "'Manage Channels' permissions" in args[0]
