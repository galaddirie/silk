"""Live Chromium contracts for Silk's public input-action templates."""

from urllib.parse import quote

import pytest
from fp_ops import _

from silk.actions.elements import RequireElement as require_element
from silk.actions.input import (
    DragOptions,
    Click as click,
    Drag as drag,
    Fill as fill,
    KeyDown as key_down,
    KeyPress as key_press,
    KeyUp as key_up,
    MouseMove as mouse_move,
    MouseMoveTo as mouse_move_to,
    ScrollTo as scroll_to,
    SelectText as select_text,
    SelectValue as select_value,
    TypeText as type_text,
)
from silk.actions.navigation import Evaluate as evaluate, Navigate as navigate
from silk.browsers.sessions import BrowserSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_input_templates_drive_real_dom_from_each_focus_position(
    browser_session: BrowserSession,
) -> None:
    context = browser_session.context

    try:
        page_result = await context.new_page()
        assert page_result.is_ok(), page_result
        page = page_result.ok

        document = """
            <style>
              body { min-height: 2400px; }
              #source, #target {
                position: absolute;
                top: 20px;
                width: 80px;
                height: 50px;
              }
              #source { left: 20px; background: steelblue; }
              #target { left: 240px; background: tomato; }
              #hover {
                position: absolute;
                left: 400px;
                top: 20px;
                width: 100px;
                height: 40px;
                background: gold;
              }
              #form { position: absolute; top: 120px; }
            </style>
            <div id="source" draggable="true">drag me</div>
            <div id="target" data-drops="0">drop here</div>
            <div id="hover" data-moves="0">hover here</div>
            <div id="form">
              <input id="field" />
              <select id="choice">
                <option value="">Empty value</option>
                <option value="blank-label"></option>
                <option value="one">One</option>
                <option value="two">Two</option>
              </select>
              <button id="button">Click</button>
              <output id="clicked">no</output>
            </div>
            <script>
              const source = document.querySelector("#source");
              const target = document.querySelector("#target");
              source.addEventListener("dragstart", event => {
                event.dataTransfer.setData("text/plain", "silk");
              });
              target.addEventListener("dragover", event => event.preventDefault());
              target.addEventListener("drop", event => {
                event.preventDefault();
                target.dataset.drops = String(Number(target.dataset.drops) + 1);
              });
              document.querySelector("#button").addEventListener("click", () => {
                document.querySelector("#clicked").textContent = "yes";
              });
              document.querySelector("#hover").addEventListener("mousemove", event => {
                const hover = document.querySelector("#hover");
                hover.dataset.moves = String(Number(hover.dataset.moves) + 1);
                hover.dataset.pointer = `${event.clientX},${event.clientY}`;
              });
              document.addEventListener("mousemove", event => {
                document.body.dataset.pointer = `${event.clientX},${event.clientY}`;
              });
              document.addEventListener("keydown", event => {
                const previous = document.body.dataset.keys || "";
                document.body.dataset.keys = `${previous}|down:${event.key}`;
              });
              document.addEventListener("keyup", event => {
                const previous = document.body.dataset.keys || "";
                document.body.dataset.keys = `${previous}|up:${event.key}`;
              });
            </script>
            """
        content_result = await navigate(
            _,
            f"data:text/html,{quote(document)}",
        ).run(page)
        assert content_result.is_ok(), content_result

        source_result = await require_element("#source", _).run(page)
        target_result = await require_element("#target", _).run(page)
        assert source_result.is_ok()
        assert target_result.is_ok()
        source = source_result.ok
        target = target_result.ok

        source_hole = await drag(_, target, options=DragOptions(steps=12)).run(source)
        target_hole = await drag(source, _, options=DragOptions(steps=12)).run(target)
        assert source_hole.is_ok() and source_hole.ok is source
        assert target_hole.is_ok() and target_hole.ok is source

        hover_target = await mouse_move_to(
            _,
            page,
            offset=(1, 2),
            center=True,
            steps=3,
        ).run("#hover")
        hover_scope = await mouse_move_to(
            "#hover",
            _,
            offset=(2, 3),
            center=False,
            steps=2,
        ).run(page)
        assert hover_target.is_ok()
        assert hover_scope.is_ok()
        hover_state = await evaluate(
            _,
            """() => ({
              moves: document.querySelector("#hover").dataset.moves,
              pointer: document.querySelector("#hover").dataset.pointer
            })""",
        ).run(page)
        assert hover_state.is_ok()
        assert hover_state.ok == {"moves": "3", "pointer": "402,23"}

        filled = await fill("#field", _, page).run("hello")
        typed = await type_text(_, " world", page).run("#field")
        empty_value = await select_value("#choice", _, page).run("")
        assert empty_value.is_ok()
        selected_empty_value = await evaluate(
            _,
            '() => document.querySelector("#choice").value',
        ).run(page)
        assert selected_empty_value.is_ok()
        assert selected_empty_value.ok == ""
        empty_text = await select_text("#choice", _, page).run("")
        assert empty_text.is_ok()
        selected_empty_text = await evaluate(
            _,
            '() => document.querySelector("#choice").value',
        ).run(page)
        assert selected_empty_text.is_ok()
        assert selected_empty_text.ok == "blank-label"
        selected = await select_text("#choice", _, page).run("Two")
        clicked = await click("#button", _).run(page)
        assert filled.is_ok() and filled.ok.selector == "#field"
        assert typed.is_ok() and typed.ok.selector == "#field"
        assert selected.is_ok() and selected.ok.selector == "#choice"
        assert clicked.is_ok() and clicked.ok.selector == "#button"

        focused = await click("#field", _).run(page)
        assert focused.is_ok()
        reset_trace = await evaluate(
            _,
            """() => {
              document.body.dataset.pointer = "";
              document.body.dataset.keys = "";
            }""",
        ).run(page)
        assert reset_trace.is_ok(), reset_trace

        moved_position = await mouse_move(_, page, steps=2).run((32, 48))
        moved_page = await mouse_move((64, 80), _, steps=3).run(page)
        pressed_key = await key_press(_, page, delay_ms=5).run("ArrowLeft")
        pressed_page = await key_press("ArrowRight", _).run(page)
        held = await key_down(_, page).run("Shift")
        released = await key_up("Shift", _).run(page)
        assert moved_position.is_ok() and moved_position.ok is page
        assert moved_page.is_ok() and moved_page.ok is page
        assert pressed_key.is_ok() and pressed_key.ok is page
        assert pressed_page.is_ok() and pressed_page.ok is page
        assert held.is_ok() and held.ok is page
        assert released.is_ok() and released.ok is page

        scrolled_position = await scroll_to(_, page).run((0, 400))
        scrolled_page = await scroll_to((0, 800), _).run(page)
        assert scrolled_position.is_ok() and scrolled_position.ok is page
        assert scrolled_page.is_ok() and scrolled_page.ok is page

        state_result = await evaluate(
            _,
            """() => ({
              drops: document.querySelector("#target").dataset.drops,
              field: document.querySelector("#field").value,
              choice: document.querySelector("#choice").value,
              clicked: document.querySelector("#clicked").textContent,
              pointer: document.body.dataset.pointer,
              keys: document.body.dataset.keys,
              scrollY: window.scrollY
            })""",
        ).run(page)
        assert state_result.is_ok(), state_result
        assert state_result.ok == {
            "drops": "2",
            "field": "hello world",
            "choice": "two",
            "clicked": "yes",
            "pointer": "64,80",
            "keys": (
                "|down:ArrowLeft|up:ArrowLeft"
                "|down:ArrowRight|up:ArrowRight|down:Shift|up:Shift"
            ),
            "scrollY": 800,
        }
    finally:
        close_result = await context.close()
        assert close_result.is_ok(), close_result
