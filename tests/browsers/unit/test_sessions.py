import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from silk.browsers.sessions import BrowserSession
from silk.browsers.models import BrowserOptions, ActionContext, Driver, BrowserContext, Page
from expression import Ok, Error

@pytest.fixture
def mock_driver_class():
    driver_instance = AsyncMock(spec=Driver)
    driver_instance.launch = AsyncMock(return_value=Ok(None))

    mock_page_instance = AsyncMock(spec=Page)
    mock_page_instance.page_id = "test_page_id"
    mock_page_instance.close = AsyncMock(return_value=Ok(None))

    mock_context_instance = AsyncMock(spec=BrowserContext)
    mock_context_instance.new_page = AsyncMock(return_value=Ok(mock_page_instance))
    mock_context_instance.context_id = "test_context_id"
    mock_context_instance.close = AsyncMock(return_value=Ok(None))

    driver_instance.new_context = AsyncMock(return_value=Ok(mock_context_instance))
    driver_instance.close = AsyncMock(return_value=Ok(None))
    
    mock_class = MagicMock(return_value=driver_instance)
    mock_class.__name__ = "TestDriver"
    return mock_class

@pytest.mark.asyncio
async def test_browser_session_start_and_close(mock_driver_class):
    session = BrowserSession(driver_class=mock_driver_class)
    
    assert session.driver is None
    assert session.browser_context is None
    assert session.page is None
    assert session.context is None
    assert not session._started

    action_context = await session.start()

    assert session.driver is not None
    assert session.browser_context is not None
    assert session.page is not None
    assert session.context is not None
    assert session._started
    assert isinstance(action_context, ActionContext)
    assert action_context.driver is session.driver
    assert action_context.context is session.browser_context
    assert action_context.page is session.page
    assert action_context.driver_type == mock_driver_class.__name__.lower().replace('driver', '')
    assert action_context.context_id == "test_context_id"
    assert action_context.page_id == "test_page_id"

    session.driver_class.assert_called_once()
    session.driver.launch.assert_called_once()
    session.driver.new_context.assert_called_once()
    session.browser_context.new_page.assert_called_once()

    driver_instance = session.driver

    await session.close()

    assert session.page is None
    assert session.browser_context is None
    assert session.driver is None
    assert session.context is None
    assert not session._started

    driver_instance.close.assert_called_once()

@pytest.mark.asyncio
async def test_browser_session_async_context_manager(mock_driver_class):
    session = BrowserSession(driver_class=mock_driver_class)
    
    async with session as ctx:
        assert session.driver is not None
        assert session.browser_context is not None
        assert session.page is not None
        assert session.context is not None
        assert session._started
        assert isinstance(ctx, ActionContext)
        session.driver_class.assert_called_once()
        session.driver.launch.assert_called_once()
        session.driver.new_context.assert_called_once()
        session.browser_context.new_page.assert_called_once()

    assert session.page is None
    assert session.browser_context is None
    assert session.driver is None
    assert session.context is None
    assert not session._started

@pytest.mark.asyncio
async def test_browser_session_start_raises_if_already_started(mock_driver_class):
    session = BrowserSession(driver_class=mock_driver_class)
    await session.start()
    with pytest.raises(RuntimeError, match="Session already started"):
        await session.start()
    await session.close()

@pytest.mark.asyncio
async def test_browser_session_no_driver_class_raises_value_error():
    with pytest.raises(ValueError, match="driver_class must be provided"):
        BrowserSession()

@pytest.mark.asyncio
async def test_browser_session_start_handles_launch_error(mock_driver_class):
    mock_driver_class.return_value.launch = AsyncMock(return_value=Error(Exception("Launch failed")))
    session = BrowserSession(driver_class=mock_driver_class)
    with pytest.raises(Exception, match="Launch failed"):
        await session.start()
    assert not session._started
    mock_driver_class.return_value.close.assert_called_once()

@pytest.mark.asyncio
async def test_browser_session_start_handles_new_context_error(mock_driver_class):
    mock_driver_class.return_value.new_context = AsyncMock(return_value=Error(Exception("Context creation failed")))
    session = BrowserSession(driver_class=mock_driver_class)
    with pytest.raises(Exception, match="Context creation failed"):
        await session.start()
    assert not session._started
    mock_driver_class.return_value.launch.assert_called_once()
    mock_driver_class.return_value.close.assert_called_once()

@pytest.mark.asyncio
async def test_browser_session_start_handles_new_page_error(mock_driver_class):
    mock_context = AsyncMock(spec=BrowserContext)
    mock_context.new_page = AsyncMock(return_value=Error(Exception("Page creation failed")))
    mock_context.context_id = "test_context_id_page_error"
    mock_context.close = AsyncMock(return_value=Ok(None))
    mock_driver_class.return_value.new_context = AsyncMock(return_value=Ok(mock_context))
    
    session = BrowserSession(driver_class=mock_driver_class)
    with pytest.raises(Exception, match="Page creation failed"):
        await session.start()
    
    assert not session._started
    mock_driver_class.return_value.launch.assert_called_once()
    mock_driver_class.return_value.new_context.assert_called_once()
    mock_context.close.assert_called_once()
    mock_driver_class.return_value.close.assert_called_once()

@pytest.mark.asyncio
async def test_browser_session_creation_flags_respected(mock_driver_class):
    session_no_context = BrowserSession(driver_class=mock_driver_class, create_context=False, create_page=False)
    ctx_no_context = await session_no_context.start()
    assert session_no_context.browser_context is None
    assert session_no_context.page is None
    assert ctx_no_context.context is None
    assert ctx_no_context.page is None
    session_no_context.driver.new_context.assert_not_called()
    await session_no_context.close()

    session_no_page = BrowserSession(driver_class=mock_driver_class, create_page=False)
    ctx_no_page = await session_no_page.start()
    assert session_no_page.browser_context is not None
    assert session_no_page.page is None
    assert ctx_no_page.context is not None
    assert ctx_no_page.page is None
    session_no_page.driver.new_context.assert_called_once()
    session_no_page.browser_context.new_page.assert_not_called()
    await session_no_page.close()
