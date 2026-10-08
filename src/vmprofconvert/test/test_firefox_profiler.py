import os
from pathlib import Path

import pytest

from vmprofconvert import convert_stats, Converter, Thread, CATEGORY_JIT, CATEGORY_NATIVE


@pytest.mark.firefox_profiler
@pytest.mark.parametrize("conflicting_categories", [False, True])
def test_generated_profile_loads_in_firefox_profiler(tmp_path, conflicting_categories):
    playwright = pytest.importorskip("playwright.sync_api")

    source_profile = Path(__file__).parent / "profiles" / "example.prof"
    converted_profile = tmp_path / "example.json"
    converted_profile.write_text(
        convert_stats(os.fspath(source_profile)), encoding="utf-8"
    )

    if conflicting_categories:
        converter = Converter()
        thread = Thread()
        converter.threads[0] = thread
        # Model two frames of the same function with different categories.
        # Firefox merges them into one call node, requiring a fallback category.
        for i, category in enumerate([CATEGORY_JIT, CATEGORY_NATIVE]):
            frame = thread.add_frame("hot", 1, "example.py", category, -1, -1)
            _, symbol, line, _ = thread.frametable[frame]
            thread.frametable[frame] = (0, symbol, line, category)
            stack = thread.add_stack([frame], [category])
            thread.add_sample(stack, i)
        converted_profile.write_text(converter.dumps_static(), encoding="utf-8")

    browser_errors = []
    with playwright.sync_playwright() as browser_tools:
        launch_options = {}
        if executable_path := os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
            launch_options["executable_path"] = executable_path
        browser = browser_tools.chromium.launch(**launch_options)
        page = browser.new_page()
        page.on("pageerror", lambda error: browser_errors.append(str(error)))

        page.goto(
            "https://profiler.firefox.com/",
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        page.locator('input[type="file"]').set_input_files(
            {"name": "example.json", "mimeType": "application/json",
             "buffer": converted_profile.read_bytes()}
        )

        try:
            page.wait_for_function(
                """
                () => window.getState?.().app.view.phase === "DATA_LOADED"
                """,
                timeout=60_000,
            )
        except playwright.TimeoutError:
            pytest.fail(
                "Firefox Profiler did not load the generated profile.\n"
                f"Page contents:\n{page.locator('body').inner_text()}\n"
                f"JavaScript errors:\n{chr(10).join(browser_errors)}"
            )

        result = page.evaluate(
            """
            () => ({
                phase: window.getState().app.view.phase,
                importedFrom: window.profile.meta.importedFrom,
                threadCount: window.profile.threads.length,
                sampleCount: window.profile.threads.reduce(
                    (count, thread) => count + thread.samples.length,
                    0
                ),
            })
            """
        )
        for view in ("Flame Graph", "Stack Chart", "Call Tree"):
            page.get_by_text(view, exact=True).click()
            page.wait_for_timeout(500)
            assert "unknown error happened" not in page.locator("body").inner_text()
        page.locator('[role="treeitem"]').first.click()
        for _ in range(30):
            page.keyboard.press("ArrowRight")
            page.keyboard.press("ArrowDown")
        assert "unknown error happened" not in page.locator("body").inner_text()
        browser.close()

    assert result["phase"] == "DATA_LOADED"
    assert result["importedFrom"] == "VMProf"
    assert result["threadCount"] >= 1
    assert result["sampleCount"] > 0
    assert not browser_errors, "\n".join(browser_errors)
