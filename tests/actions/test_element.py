"""Contract tests for public element operation factories."""

import inspect
from dataclasses import FrozenInstanceError, dataclass
from typing import assert_type
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fp_ops import (
    BuildFieldError,
    Error,
    Ok,
    Operation,
    TraversalItemError,
    _,
    build,
    traverse,
)

import silk.actions.elements as element_actions
from silk.actions.elements import (
    Element,
    ElementScope,
    SelectorInput,
    WaitOptions,
    WaitPage,
    WaitSelectorInput,
    ElementExists as element_exists,
    ExtractTable as extract_table,
    GetAttribute as get_attribute,
    GetHtml as get_html,
    GetInnerText as get_inner_text,
    GetText as get_text,
    Query as query,
    QueryAll as query_all,
    RequireAttribute as require_attribute,
    RequireElement as require_element,
    WaitForElement as wait_for_element,
)
from silk.browsers.models import ElementHandle, Page
from silk.errors import AttributeNotFoundError, ElementNotFoundError
from silk.selectors.selector import (
    Selector,
    SelectorGroup,
    SelectorType,
    css,
    text,
    xpath,
)


@dataclass(frozen=True)
class Book:
    title: str
    price: str


def make_element(
    *,
    text: str = "text",
    inner_text: str = "inner text",
    html: str = "<div>text</div>",
) -> MagicMock:
    element = MagicMock(spec=ElementHandle)
    element.query_selector = AsyncMock(return_value=Ok(None))
    element.query_selector_all = AsyncMock(return_value=Ok([]))
    element.text = AsyncMock(return_value=Ok(text))
    element.inner_text = AsyncMock(return_value=Ok(inner_text))
    element.html = AsyncMock(return_value=Ok(html))
    element.attribute = AsyncMock(return_value=Ok(None))
    element.__deepcopy__.return_value = element
    return element


def make_page() -> MagicMock:
    page = MagicMock(spec=Page)
    page.query_selector = AsyncMock(return_value=Ok(None))
    page.query_selector_all = AsyncMock(return_value=Ok([]))
    page.wait_for_selector = AsyncMock(return_value=Ok(None))
    page.__deepcopy__.return_value = page
    return page


@pytest.mark.asyncio
async def test_query_returns_none_only_for_not_found() -> None:
    page = make_page()

    result = await query(".missing", _).run(page)

    assert result.is_ok()
    assert result.ok is None
    page.query_selector.assert_awaited_once_with(".missing")


@pytest.mark.asyncio
async def test_query_uses_an_element_as_the_explicit_scope() -> None:
    parent = make_element()
    child = make_element()
    parent.query_selector.return_value = Ok(child)

    result = await query(".child", _).run(parent)

    assert result.is_ok()
    assert result.ok is child
    parent.query_selector.assert_awaited_once_with(".child")


@pytest.mark.asyncio
async def test_query_preserves_a_browser_error_object() -> None:
    page = make_page()
    browser_error = RuntimeError("browser disconnected")
    page.query_selector.return_value = Error(browser_error)

    result = await query(".item", _).run(page)

    assert result.is_error()
    assert result.error is browser_error


@pytest.mark.parametrize(
    ("selector", "native_query"),
    [
        (css(".card"), ".card"),
        (xpath("//article"), "xpath=//article"),
        (text("Find me"), "text=Find me"),
        (Selector(SelectorType.ID, "account"), '[id="account"]'),
        (Selector(SelectorType.CLASS, "featured"), '[class~="featured"]'),
        (Selector(SelectorType.NAME, "email"), '[name="email"]'),
        (Selector(SelectorType.TAG, "article"), "article"),
        (
            Selector(SelectorType.LINK_TEXT, "Read more"),
            'a:text-is("Read more")',
        ),
    ],
)
@pytest.mark.asyncio
async def test_query_compiles_every_supported_selector_type(
    selector: Selector,
    native_query: str,
) -> None:
    page = make_page()

    result = await query(selector, _).run(page)

    assert result == Ok(None)
    page.query_selector.assert_awaited_once_with(native_query)


@pytest.mark.asyncio
async def test_selector_group_falls_back_only_on_absence() -> None:
    page = make_page()
    element = make_element()
    page.query_selector.side_effect = [Ok(None), Ok(None), Ok(element)]
    selectors = SelectorGroup(
        "item",
        css(".primary"),
        xpath("//article[@data-legacy]"),
        text("Fallback title"),
    )

    result = await query(selectors, _).run(page)

    assert result.is_ok()
    assert result.ok is element
    assert page.query_selector.await_args_list == [
        call(".primary"),
        call("xpath=//article[@data-legacy]"),
        call("text=Fallback title"),
    ]


@pytest.mark.asyncio
async def test_selector_group_does_not_swallow_browser_failure() -> None:
    page = make_page()
    browser_error = RuntimeError("selector engine failed")
    page.query_selector.side_effect = [Error(browser_error), Ok(make_element())]
    selectors = SelectorGroup(
        "item",
        xpath("//article"),
        text("Fallback title"),
    )

    result = await query(selectors, _).run(page)

    assert result.is_error()
    assert result.error is browser_error
    page.query_selector.assert_awaited_once_with("xpath=//article")


@pytest.mark.asyncio
async def test_query_all_returns_exact_first_nonempty_focus_list() -> None:
    parent = make_element()
    first = make_element(text="first")
    second = make_element(text="second")
    parent.query_selector_all.side_effect = [Ok([]), Ok([first, second])]
    selectors = SelectorGroup("cards", ".preferred", ".legacy")

    result = await query_all(selectors, _).run(parent)

    assert result.is_ok()
    assert result.ok == [first, second]
    assert parent.query_selector_all.await_args_list == [
        call(".preferred"),
        call(".legacy"),
    ]


@pytest.mark.asyncio
async def test_query_all_fails_fast_on_browser_error() -> None:
    page = make_page()
    browser_error = RuntimeError("query all failed")
    page.query_selector_all.side_effect = [
        Error(browser_error),
        Ok([make_element()]),
    ]
    selectors = SelectorGroup("cards", ".preferred", ".legacy")

    result = await query_all(selectors, _).run(page)

    assert result.is_error()
    assert result.error is browser_error
    page.query_selector_all.assert_awaited_once_with(".preferred")


@pytest.mark.asyncio
async def test_require_element_distinguishes_not_found_from_browser_failure() -> None:
    page = make_page()
    selectors = SelectorGroup("item", ".primary", ".fallback")

    missing = await require_element(selectors, _).run(page)

    assert missing.is_error()
    assert isinstance(missing.error, ElementNotFoundError)
    assert missing.error.selector == (".primary", ".fallback")

    browser_error = RuntimeError("connection lost")
    page.query_selector.side_effect = None
    page.query_selector.return_value = Error(browser_error)

    failed = await require_element(".item", _).run(page)

    assert failed.is_error()
    assert failed.error is browser_error


@pytest.mark.asyncio
async def test_selector_configuration_is_immutable_and_reusable() -> None:
    page = make_page()
    original = Selector(SelectorType.CSS, ".original")
    selectors = SelectorGroup("item", original)

    with pytest.raises(FrozenInstanceError):
        original.value = ".mutated"
    with pytest.raises(FrozenInstanceError):
        selectors.name = "changed"

    result = await query(selectors, _).run(page)

    assert result.is_ok()
    page.query_selector.assert_awaited_once_with(".original")


@pytest.mark.asyncio
async def test_query_accepts_the_selector_as_runtime_data() -> None:
    page = make_page()
    operation = query(_, page)
    assert_type(operation, Operation[SelectorInput, Element | None])

    result = await operation.run(text("Find me"))

    assert result == Ok(None)
    page.__deepcopy__.assert_called_once()
    page.query_selector.assert_awaited_once_with("text=Find me")


@pytest.mark.asyncio
async def test_wait_for_element_supports_both_placeholder_positions() -> None:
    page = make_page()
    element = make_element()
    options = WaitOptions(timeout=250, state="visible")
    page.wait_for_selector.return_value = Ok(element)
    page_hole = wait_for_element(".ready", _, options=options)
    selector_hole = wait_for_element(_, page, options=options)
    assert_type(page_hole, Operation[WaitPage, Element | None])
    assert_type(selector_hole, Operation[WaitSelectorInput, Element | None])

    first = await page_hole.run(page)
    second = await selector_hole.run(text("Ready"))

    assert first == Ok(element)
    assert second == Ok(element)
    assert page.wait_for_selector.await_args_list == [
        call(".ready", timeout_ms=250, state="visible"),
        call("text=Ready", timeout_ms=250, state="visible"),
    ]


@pytest.mark.asyncio
async def test_wait_for_element_returns_none_for_hidden_state() -> None:
    page = make_page()
    options = WaitOptions(timeout=250, state="hidden")

    result = await wait_for_element(".gone", _, options=options).run(page)

    assert result == Ok(None)
    page.wait_for_selector.assert_awaited_once_with(
        ".gone",
        timeout_ms=250,
        state="hidden",
    )


@pytest.mark.asyncio
async def test_wait_for_element_preserves_browser_error_identity() -> None:
    page = make_page()
    browser_error = RuntimeError("wait failed")
    page.wait_for_selector.return_value = Error(browser_error)

    result = await wait_for_element(".ready", _).run(page)

    assert result.is_error()
    assert result.error is browser_error


@pytest.mark.asyncio
async def test_wait_for_element_snapshots_selector_and_options() -> None:
    page = make_page()
    selector = css(".original")
    options = WaitOptions(timeout=250, state="visible")
    operation = wait_for_element(selector, _, options=options)
    with pytest.raises(FrozenInstanceError):
        selector.value = ".mutated"
    with pytest.raises(FrozenInstanceError):
        options.timeout = 999
    with pytest.raises(FrozenInstanceError):
        options.state = "hidden"

    result = await operation.run(page)

    assert result == Ok(None)
    (passed_selector,) = page.wait_for_selector.await_args.args
    assert passed_selector == ".original"
    assert page.wait_for_selector.await_args.kwargs == {
        "timeout_ms": 250,
        "state": "visible",
    }


def test_wait_for_element_preserves_template_metadata_and_export() -> None:
    assert wait_for_element.__name__ == "WaitForElement"
    signature = inspect.signature(wait_for_element)
    assert tuple(signature.parameters) == ("selector", "page", "options")
    assert signature.parameters["options"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["options"].default is None
    assert "WaitForElement" in element_actions.__all__
    assert not hasattr(element_actions, "wait_for_element")
    assert wait_for_element(".ready", _).name == "WaitForElement"


@pytest.mark.asyncio
async def test_get_inner_text_accepts_runtime_target_with_configured_parent() -> None:
    parent = make_element()
    child = make_element(inner_text="Visible child")
    parent.query_selector.return_value = Ok(child)
    operation = get_inner_text(_, parent)

    result = await operation.run(".child")

    assert result == Ok("Visible child")
    parent.query_selector.assert_awaited_once_with(".child")


@pytest.mark.asyncio
async def test_get_inner_text_accepts_runtime_scope_with_configured_target() -> None:
    parent = make_element()
    child = make_element(inner_text="Visible child")
    parent.query_selector.return_value = Ok(child)
    operation = get_inner_text(".child", _)

    result = await operation.run(parent)

    assert result == Ok("Visible child")
    parent.query_selector.assert_awaited_once_with(".child")


@pytest.mark.asyncio
async def test_strict_text_composes_across_page_and_element_focus() -> None:
    page = make_page()
    card = make_element()
    title = make_element(text="Silk")
    page.query_selector.return_value = Ok(card)
    card.query_selector.return_value = Ok(title)

    pipeline = require_element(".card", _).then(get_text(".title", _))
    assert_type(pipeline, Operation[ElementScope, str])

    result = await pipeline.run(page)

    assert result == Ok("Silk")
    page.query_selector.assert_awaited_once_with(".card")
    card.query_selector.assert_awaited_once_with(".title")


@pytest.mark.asyncio
async def test_get_text_is_strict_and_preserves_read_failure() -> None:
    page = make_page()

    missing = await get_text(".title", _).run(page)

    assert missing.is_error()
    assert isinstance(missing.error, ElementNotFoundError)

    title = make_element()
    browser_error = RuntimeError("text read failed")
    title.text.return_value = Error(browser_error)
    page.query_selector.return_value = Ok(title)

    failed = await get_text(".title", _).run(page)

    assert failed.is_error()
    assert failed.error is browser_error


@pytest.mark.asyncio
async def test_optional_and_required_attribute_have_distinct_absence_semantics() -> (
    None
):
    page = make_page()
    link = make_element()
    page.query_selector.return_value = Ok(link)
    link.attribute.return_value = Ok(None)

    optional = await get_attribute("a", _, attribute="href").run(page)
    required = await require_attribute("a", _, attribute="href").run(page)

    assert optional == Ok(None)
    assert required.is_error()
    assert isinstance(required.error, AttributeNotFoundError)
    assert required.error.selector == "a"
    assert required.error.attribute == "href"


@pytest.mark.asyncio
async def test_attribute_browser_failure_is_not_attribute_absence() -> None:
    page = make_page()
    link = make_element()
    browser_error = RuntimeError("attribute read failed")
    page.query_selector.return_value = Ok(link)
    link.attribute.return_value = Error(browser_error)

    optional = await get_attribute("a", _, attribute="href").run(page)
    required = await require_attribute("a", _, attribute="href").run(page)

    assert optional.is_error()
    assert optional.error is browser_error
    assert required.is_error()
    assert required.error is browser_error


@pytest.mark.asyncio
async def test_html_and_inner_text_delegate_to_the_selected_element() -> None:
    page = make_page()
    element = make_element(inner_text="Visible", html="inside")
    page.query_selector.return_value = Ok(element)

    html_result = await get_html(".content", _, outer=False).run(page)
    inner_text_result = await get_inner_text(".content", _).run(page)

    assert html_result == Ok("inside")
    assert inner_text_result == Ok("Visible")
    element.html.assert_awaited_once_with(outer=False)
    element.inner_text.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_element_exists_preserves_browser_failure() -> None:
    page = make_page()

    absent = await element_exists(".item", _).run(page)

    assert absent == Ok(False)

    browser_error = RuntimeError("existence query failed")
    page.query_selector.return_value = Error(browser_error)
    failed = await element_exists(".item", _).run(page)

    assert failed.is_error()
    assert failed.error is browser_error


@pytest.mark.asyncio
async def test_query_all_composes_with_typed_traversal() -> None:
    page = make_page()
    first_card = make_element()
    second_card = make_element()
    first_title = make_element(text="First")
    second_title = make_element(text="Second")
    page.query_selector_all.return_value = Ok([first_card, second_card])
    first_card.query_selector.return_value = Ok(first_title)
    second_card.query_selector.return_value = Ok(second_title)

    pipeline = query_all(".card", _).then(traverse(get_text(".title", _)))
    assert_type(pipeline, Operation[ElementScope, list[str]])

    result = await pipeline.run(page)

    assert result == Ok(["First", "Second"])


@pytest.mark.asyncio
async def test_books_pipeline_preserves_exact_browser_cause_chain() -> None:
    page = make_page()
    card = make_element()
    browser_error = RuntimeError("title lookup failed")
    page.query_selector_all.return_value = Ok([card])
    card.query_selector.return_value = Error(browser_error)
    extract_book = build(
        {
            "title": require_attribute("h3 > a", _, attribute="title"),
            "price": get_text("p.price_color", _),
        },
        Book,
    )
    pipeline = query_all("article.product_pod", _) >> traverse(extract_book)

    result = await pipeline.run(page)

    assert result.is_error()
    assert isinstance(result.error, TraversalItemError)
    build_error = result.error.cause
    assert isinstance(build_error, BuildFieldError)
    assert build_error.field == "title"
    assert build_error.cause is browser_error
    assert build_error.__cause__ is browser_error
    assert result.error.cause is build_error
    assert result.error.__cause__ is build_error
    card.query_selector.assert_awaited_once_with("h3 > a")


@pytest.mark.asyncio
async def test_extract_table_uses_nested_element_scopes() -> None:
    page = make_page()
    table = make_element()
    name_header = make_element(text=" Name ")
    price_header = make_element(text=" Price ")
    row = make_element()
    name_cell = make_element(text=" Silk ")
    price_cell = make_element(text=" $10 ")
    page.query_selector.return_value = Ok(table)

    async def table_query_all(selector: str) -> object:
        if selector == "thead th, th":
            return Ok([name_header, price_header])
        if selector == "tbody tr, tr":
            return Ok([row])
        return Ok([])

    table.query_selector_all.side_effect = table_query_all
    row.query_selector_all.return_value = Ok([name_cell, price_cell])

    result = await extract_table("table", _).run(page)

    assert result == Ok([{"Name": "Silk", "Price": "$10"}])
    page.query_selector.assert_awaited_once_with("table")
    row.query_selector_all.assert_awaited_once_with("td")


@pytest.mark.asyncio
async def test_every_supported_element_operand_position_executes() -> None:
    page = make_page()
    element = make_element(text="text", inner_text="inner", html="<div />")
    element.attribute.return_value = Ok("value")
    page.query_selector.return_value = Ok(element)
    page.query_selector_all.return_value = Ok([element])
    page.wait_for_selector.return_value = Ok(element)

    results = [
        await query(_, page).run(".item"),
        await query(".item", _).run(page),
        await require_element(_, page).run(".item"),
        await require_element(".item", _).run(page),
        await query_all(_, page).run(".item"),
        await query_all(".item", _).run(page),
        await element_exists(_, page).run(".item"),
        await element_exists(".item", _).run(page),
        await wait_for_element(_, page).run(".item"),
        await wait_for_element(".item", _).run(page),
        await get_text(_, element).run(element),
        await get_text(element, _).run(element),
        await get_inner_text(_, element).run(element),
        await get_inner_text(element, _).run(element),
        await get_html(_, element).run(element),
        await get_html(element, _).run(element),
        await get_attribute(_, element, attribute="href").run(element),
        await get_attribute(element, _, attribute="href").run(element),
        await require_attribute(_, element, attribute="href").run(element),
        await require_attribute(element, _, attribute="href").run(element),
        await extract_table(_, element).run(element),
        await extract_table(element, _).run(element),
    ]

    assert all(result.is_ok() for result in results)


def test_every_element_template_requires_exactly_one_direct_placeholder() -> None:
    page = make_page()
    element = make_element()
    zero_hole_calls = (
        lambda: query(".item", page),
        lambda: require_element(".item", page),
        lambda: query_all(".item", page),
        lambda: element_exists(".item", page),
        lambda: wait_for_element(".item", page),
        lambda: get_text(element, page),
        lambda: get_inner_text(element, page),
        lambda: get_html(element, page),
        lambda: get_attribute(element, page, attribute="href"),
        lambda: require_attribute(element, page, attribute="href"),
        lambda: extract_table(element, page),
    )
    multiple_hole_calls = (
        lambda: query(_, _),
        lambda: require_element(_, _),
        lambda: query_all(_, _),
        lambda: element_exists(_, _),
        lambda: wait_for_element(_, _),
        lambda: get_text(_, _),
        lambda: get_inner_text(_, _),
        lambda: get_html(_, _),
        lambda: get_attribute(_, _, attribute="href"),
        lambda: require_attribute(_, _, attribute="href"),
        lambda: extract_table(_, _),
    )

    for construct in (*zero_hole_calls, *multiple_hole_calls):
        with pytest.raises(TypeError, match="exactly one direct placeholder"):
            construct()
