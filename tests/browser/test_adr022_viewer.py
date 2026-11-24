"""The report viewer checked in a real browser, over reports of real runs of shipped examples. See ADR 022.

The model under the viewer is covered by `tests/test_adr022_report.py`; these tests cover what only a
browser shows: which tab is on screen, what folds, what opens, what the themes, a narrow screen and
printing do, and that the page says what it needs when scripts are off.
"""

import re
from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Browser, Page, expect

from tests.browser.conftest import BUDGET, Report

pytestmark = pytest.mark.browser

CASES = ["completed", "failed", "budget", "question"]
TABS = ["graph", "path", "parameters", "artifacts", "journal"]

Opener = Callable[..., Page]


@pytest.fixture
def open_report(page: Page, reports: dict[str, Report]) -> Iterator[Opener]:
    """Open a report by case, optionally at an anchor; no test ends with an error in the console."""
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

    def open_(case: str, anchor: str = "") -> Page:
        page.goto(reports[case].url + (f"#{anchor}" if anchor else ""))
        expect(page.locator("header.run h1")).to_be_visible()
        return page

    yield open_
    assert errors == []


def shown_panels(page: Page) -> list[str]:
    return [panel.get_attribute("id") or "" for panel in page.locator('section[role="tabpanel"]:visible').all()]


@pytest.mark.parametrize("case", CASES)
def test_the_report_opens_on_the_graph_with_one_panel_shown(open_report: Opener, case: str):
    page = open_report(case)

    assert shown_panels(page) == ["graph"]
    expect(page.locator("#tab-graph")).to_have_attribute("aria-selected", "true")
    expect(page.locator(".diagram svg a.gn").first).to_be_visible()


@pytest.mark.parametrize(
    ("case", "ending"),
    [
        ("completed", "Completed at WRITE_REPORT after 18 node visits."),
        ("failed", "Failed at WRITE_TABLE under pretty_table_no_data"),
        ("budget", f"the session budget of {BUDGET} node visits is spent."),
        ("question", "Paused at ASK_APPROVAL, waiting for an answer."),
    ],
)
def test_the_header_states_the_ending(open_report: Opener, case: str, ending: str):
    expect(open_report(case).locator("header.run .ending")).to_contain_text(ending)


@pytest.mark.parametrize(
    ("case", "heading"), [("budget", "session budget spent"), ("question", "waiting for an answer")]
)
def test_a_paused_session_shows_its_pending_block_with_the_command(open_report: Opener, case: str, heading: str):
    page = open_report(case)

    pending = page.locator("#pending")
    expect(pending.locator("h2")).to_contain_text(heading)
    expect(pending.locator(".cmd pre")).to_contain_text(reports_session(page))


@pytest.mark.parametrize("case", ["completed", "failed"])
def test_a_concluded_session_has_no_pending_block(open_report: Opener, case: str):
    expect(open_report(case).locator("#pending")).to_have_count(0)


def test_the_question_switches_between_as_presented_and_as_written(open_report: Opener):
    page = open_report("question")
    presented = page.get_by_role("button", name="As presented")
    written = page.get_by_role("button", name="As written")
    expect(presented).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#pending .tmpl .ref")).to_have_count(0)

    written.click()

    expect(written).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#pending .tmpl .ref").first).to_be_visible()


def test_every_tab_shows_its_own_panel_alone(open_report: Opener):
    page = open_report("completed")

    for tab in TABS:
        page.locator(f"#tab-{tab}").click()
        expect(page.locator(f"#tab-{tab}")).to_have_attribute("aria-selected", "true")
        assert shown_panels(page) == [tab]


def test_the_arrow_keys_move_between_tabs(open_report: Opener):
    page = open_report("completed")
    page.locator("#tab-graph").focus()

    page.keyboard.press("ArrowRight")
    expect(page.locator("#tab-path")).to_be_focused()
    assert shown_panels(page) == ["path"]

    page.keyboard.press("ArrowLeft")
    expect(page.locator("#tab-graph")).to_be_focused()
    assert shown_panels(page) == ["graph"]


def test_the_loop_of_the_path_folds_and_unfolds(open_report: Opener):
    page = open_report("completed")
    page.locator("#tab-path").click()
    head = page.locator(".loop-head")
    body = page.locator(".loop-body")
    expect(head).to_contain_text("Loop at POP_NEXT")
    expect(body).to_be_hidden()

    head.click()
    expect(page.locator(".loop-head")).to_have_attribute("aria-expanded", "true")
    expect(page.locator(".loop-body")).to_be_visible()
    expect(page.locator(".pass-body").first).to_be_hidden()

    page.locator(".pass-head").first.click()
    expect(page.locator(".pass-body").first).to_be_visible()

    page.locator(".loop-head").click()
    expect(page.locator(".loop-body")).to_be_hidden()


def test_a_node_opens_in_its_dialog_with_both_views_and_closes_by_keyboard(open_report: Opener):
    page = open_report("completed")

    page.locator("a.gn", has_text="WRITE_TABLE").click()

    dialog = page.locator("#node-dlg")
    expect(dialog).to_be_visible()
    expect(dialog.locator("h3")).to_have_text("WRITE_TABLE")
    expect(dialog.get_by_text("As written")).to_be_visible()
    expect(dialog.get_by_text("As built · effective transitions in order")).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog).to_be_hidden()
    expect(page).not_to_have_url(re.compile(r"#node-"))


def test_the_graph_list_view_opens_the_same_dialog(open_report: Opener):
    page = open_report("completed")
    page.get_by_role("button", name="List").click()

    page.locator(".graph a.node", has_text="POP_NEXT").click()

    expect(page.locator("#node-dlg h3")).to_have_text("POP_NEXT")


def test_a_node_anchor_opens_its_dialog(open_report: Opener):
    page = open_report("question", "node-ask-approval")

    expect(page.locator("#node-dlg")).to_be_visible()
    expect(page.locator("#node-dlg h3")).to_have_text("ASK_APPROVAL")


def test_a_visit_anchor_inside_the_loop_opens_the_path_at_that_visit(open_report: Opener):
    page = open_report("completed")
    visit = page.locator(".loop .visit").last.get_attribute("id")
    assert visit

    page = open_report("completed", visit)

    expect(page.locator("#tab-path")).to_have_attribute("aria-selected", "true")
    expect(page.locator(f"#{visit}")).to_be_visible()


def test_a_parameter_anchor_opens_the_parameters_at_that_row(open_report: Opener):
    page = open_report("completed", "param-scan-root")

    assert shown_panels(page) == ["parameters"]
    expect(page.locator("#param-scan-root")).to_be_visible()
    expect(page.locator("#param-scan-root")).to_contain_text("input")


@pytest.mark.parametrize(("scheme", "background"), [("light", "rgb(246, 247, 249)"), ("dark", "rgb(18, 21, 28)")])
def test_the_page_follows_the_colour_scheme(open_report: Opener, page: Page, scheme: str, background: str):
    page.emulate_media(color_scheme=scheme)

    expect(open_report("completed").locator("body")).to_have_css("background-color", background)


@pytest.mark.parametrize("case", CASES)
def test_a_narrow_screen_scrolls_no_panel_sideways(open_report: Opener, page: Page, case: str):
    page.set_viewport_size({"width": 360, "height": 800})
    page = open_report(case)

    for tab in TABS:
        page.locator(f"#tab-{tab}").click()
        expect(page.locator(f"section#{tab}")).to_be_visible()
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 0, f"{tab} is {overflow}px wider than the screen"


def test_printing_shows_every_panel_and_no_navigation(open_report: Opener, page: Page):
    page = open_report("completed")

    page.emulate_media(media="print")

    assert shown_panels(page) == ["path", "graph", "parameters", "artifacts", "journal"]
    expect(page.locator("nav.sections")).to_be_hidden()
    expect(page.locator(".loop-body")).to_be_visible()
    expect(page.locator(".print-only .nodecard")).to_have_count(9)


def test_with_scripts_disabled_the_page_says_it_needs_javascript(browser: Browser, reports: dict[str, Report]):
    context = browser.new_context(java_script_enabled=False)
    try:
        page = context.new_page()
        page.goto(reports["completed"].url)

        # The text engine of Playwright does not search inside <noscript>; the body's text is what shows.
        assert "Open it with JavaScript enabled" in page.inner_text("body")
        expect(page.locator("#app")).to_be_empty()
    finally:
        context.close()


def reports_session(page: Page) -> str:
    return (page.locator("header.run .sid").text_content() or "").removeprefix("session ")
