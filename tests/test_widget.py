"""Tests for Widget and WidgetMode."""

from concierge.core.widget import Widget, WidgetMode


class TestWidgetMode:
    def test_modes_are_distinct(self):
        modes = [
            WidgetMode.HTML,
            WidgetMode.URL,
            WidgetMode.ENTRYPOINT,
            WidgetMode.DYNAMIC,
        ]
        assert len(set(modes)) == 4


class TestWidget:
    def test_html_mode(self):
        w = Widget(uri="/dashboard", html="<div>Hello</div>")
        assert w.mode == WidgetMode.HTML
        assert w.html == "<div>Hello</div>"

    def test_url_mode(self):
        w = Widget(uri="/external", url="https://example.com")
        assert w.mode == WidgetMode.URL
        assert w.url == "https://example.com"

    def test_entrypoint_mode(self):
        w = Widget(uri="/app", entrypoint="main.html")
        assert w.mode == WidgetMode.ENTRYPOINT
        assert w.entrypoint == "main.html"

    def test_dynamic_mode(self):
        def gen_html():
            return "<div>Dynamic</div>"

        w = Widget(uri="/live", html_fn=gen_html)
        assert w.mode == WidgetMode.DYNAMIC
        assert w.html_fn is gen_html

    def test_default_uri(self):
        w = Widget(uri="/test", html="<p>hi</p>")
        assert w.uri == "/test"
