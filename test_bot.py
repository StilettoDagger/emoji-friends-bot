import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import discord

from cogs.status import StatusCog
from cogs.admin import AdminCog
from cogs.info import InfoCog
from utils.state import active_status_messages

@pytest.fixture(autouse=True)
def clear_active_status_messages():
    active_status_messages.clear()

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = 12345
    interaction.user.display_name = "TestUser"
    interaction.user.voice = None
    interaction.user.guild_permissions = MagicMock()
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.original_response = AsyncMock()
    interaction.channel = MagicMock()
    interaction.channel.fetch_message = AsyncMock()
    return interaction

@pytest.fixture
def status_cog():
    return StatusCog(MagicMock())

@pytest.fixture
def admin_cog():
    return AdminCog(MagicMock())

@pytest.fixture
def info_cog():
    return InfoCog(MagicMock())

@pytest.mark.asyncio
@patch('cogs.info.database')
async def test_whoami_with_status(mock_db, info_cog, mock_interaction):
    mock_db.get_user_status.return_value = ('😀', 'Hello')
    await info_cog.whoami.callback(info_cog, mock_interaction)
    
    mock_db.get_user_status.assert_called_once_with(12345)
    mock_interaction.response.send_message.assert_called_once()
    args, _ = mock_interaction.response.send_message.call_args
    assert '😀' in args[0]

@pytest.mark.asyncio
@patch('cogs.info.database')
async def test_whoami_none(mock_db, info_cog, mock_interaction):
    mock_db.get_user_status.return_value = (None, None)
    await info_cog.whoami.callback(info_cog, mock_interaction)
    
    args, _ = mock_interaction.response.send_message.call_args
    assert 'no assigned status' in args[0]

@pytest.mark.asyncio
@patch('cogs.info.database')
async def test_whois_list(mock_db, info_cog, mock_interaction):
    mock_db.get_all_user_ids.return_value = [123, 456]
    mock_db.get_user_status.side_effect = lambda uid: ('😀', 'Hello') if uid == 123 else ('😃', 'Hi')
    
    await info_cog.whois.callback(info_cog, mock_interaction)
    
    mock_interaction.response.send_message.assert_called_once()
    _, kwargs = mock_interaction.response.send_message.call_args
    embed = kwargs['embed']
    assert '<@123>: 😀 *Hello*' in embed.description
    assert '<@456>: 😃 *Hi*' in embed.description

@pytest.mark.asyncio
@patch('cogs.info.database')
async def test_whois_empty(mock_db, info_cog, mock_interaction):
    mock_db.get_all_user_ids.return_value = []
    await info_cog.whois.callback(info_cog, mock_interaction)
    
    _, kwargs = mock_interaction.response.send_message.call_args
    assert 'No users' in kwargs['embed'].description

@pytest.mark.asyncio
@patch('cogs.status.database')
@patch('cogs.status.generate_status_embed')
@patch('cogs.status.image_renderer', new_callable=AsyncMock)
async def test_status_current_channel(mock_image_renderer, mock_generate_status_embed, mock_db, status_cog, mock_interaction):
    # Setup channel with members
    mock_channel = MagicMock(spec=discord.VoiceChannel)
    mock_channel.name = "General"
    mock_channel.id = 999
    member1 = MagicMock(); member1.id = 1; member1.display_name = "User1"; member1.name = "User1"
    member2 = MagicMock(); member2.id = 2; member2.display_name = "User2"; member2.name = "User2"
    mock_channel.members = [member1, member2]
    
    mock_interaction.user.voice = MagicMock()
    mock_interaction.user.voice.channel = mock_channel
    
    mock_db.get_user_status.side_effect = lambda uid: ('😀', 'Hello') if uid == 1 else (None, None)
    mock_db.get_user_theme.return_value = "default"
    mock_image_renderer.generate_room_image.return_value = MagicMock()
    
    mock_embed = discord.Embed()
    mock_generate_status_embed.return_value = mock_embed
    
    await status_cog.status.callback(status_cog, mock_interaction, None)
    
    mock_interaction.response.defer.assert_called_once()
    mock_interaction.followup.send.assert_called_once()
    _, kwargs = mock_interaction.followup.send.call_args
    assert 'embed' in kwargs

@pytest.mark.asyncio
@patch('cogs.status.database')
@patch('cogs.status.update_vc_status', new_callable=AsyncMock)
async def test_set_status_valid(mock_update_vc_status, mock_db, status_cog, mock_interaction):
    # Setup voice state for update_vc_status to trigger
    mock_interaction.user.voice = MagicMock()
    mock_interaction.user.voice.channel = MagicMock()
    
    await status_cog.set_status.callback(status_cog, mock_interaction, '😀', 'Testing')
    
    # Verify db called
    mock_db.set_user_status.assert_called_once_with(12345, '😀', 'Testing')
    # Verify update_vc_status called
    mock_update_vc_status.assert_called_once_with(mock_interaction.user.voice.channel)
    # Verify response sent
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert '😀 Testing' in args[0]

@pytest.mark.asyncio
@patch('cogs.status.database')
async def test_set_status_invalid(mock_db, status_cog, mock_interaction):
    await status_cog.set_status.callback(status_cog, mock_interaction, '😀😃', 'Testing')
    
    # Verify db NOT called
    mock_db.set_user_status.assert_not_called()
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'exactly **one** valid emoji' in args[0]

@pytest.mark.asyncio
@patch('cogs.status.database')
@patch('cogs.status.update_vc_status', new_callable=AsyncMock)
async def test_clear_status(mock_update_vc_status, mock_db, status_cog, mock_interaction):
    # Setup voice state
    mock_interaction.user.voice = MagicMock()
    mock_interaction.user.voice.channel = MagicMock()
    
    await status_cog.clear_status.callback(status_cog, mock_interaction)
    
    mock_db.set_user_status.assert_called_once_with(12345, None, None)
    mock_update_vc_status.assert_called_once_with(mock_interaction.user.voice.channel)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'removed' in args[0]

@pytest.mark.asyncio
@patch('cogs.status.database')
async def test_status_no_channel(mock_db, status_cog, mock_interaction):
    # No channel provided, and user not in a voice channel
    mock_interaction.user.voice = None
    
    await status_cog.status.callback(status_cog, mock_interaction, None)
    
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'specify a channel or join one' in args[0]

@pytest.mark.asyncio
@patch('cogs.admin.database')
@patch('cogs.admin.update_vc_status', new_callable=AsyncMock)
async def test_toggle_status_enable(mock_update_vc_status, mock_db, admin_cog, mock_interaction):
    mock_db.toggle_vc_status.return_value = True # Becomes enabled
    
    mock_channel = AsyncMock(spec=discord.VoiceChannel)
    mock_channel.id = 999
    mock_channel.name = "Test Channel"
    mock_interaction.user.guild_permissions.manage_channels = True
    
    await admin_cog.toggle_status.callback(admin_cog, mock_interaction, mock_channel)
    
    mock_db.toggle_vc_status.assert_called_once_with(999)
    mock_update_vc_status.assert_called_once_with(mock_channel)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert '**enabled**' in args[0]

@pytest.mark.asyncio
@patch('cogs.admin.database')
async def test_toggle_status_disable(mock_db, admin_cog, mock_interaction):
    mock_db.toggle_vc_status.return_value = False # Becomes disabled
    
    mock_channel = AsyncMock(spec=discord.VoiceChannel)
    mock_channel.id = 999
    mock_channel.name = "Test Channel"
    mock_channel.members = []
    mock_interaction.user.guild_permissions.manage_channels = True
    
    await admin_cog.toggle_status.callback(admin_cog, mock_interaction, mock_channel)
    
    mock_db.toggle_vc_status.assert_called_once_with(999)
    mock_channel.edit.assert_called_once_with(status=None)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert '**disabled**' in args[0]

@pytest.mark.asyncio
@patch('cogs.admin.database')
async def test_toggle_status_no_permissions(mock_db, admin_cog, mock_interaction):
    mock_channel = AsyncMock(spec=discord.VoiceChannel)
    mock_interaction.user.guild_permissions.manage_channels = False
    
    await admin_cog.toggle_status.callback(admin_cog, mock_interaction, mock_channel)
    
    mock_db.toggle_vc_status.assert_not_called()
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "'Manage Channels' permissions" in args[0]
