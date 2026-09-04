import importlib.util
from pathlib import Path
from types import ModuleType
from typing import cast

MODULE_PATH = Path(__file__).resolve().parents[1] / "plugins" / "bazaar_plugin" / "card_image_helper.py"


def load_helper() -> ModuleType:
    spec = importlib.util.spec_from_file_location("card_image_helper_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(ModuleType, module)


def test_stale_cached_art_url_is_not_returned(monkeypatch):
    helper = load_helper()
    helper._CACHE = {
        "cards": {
            "pipe-organ": {
                "internalName": "Pipe Organ",
                "artLarge": "https://s.bazaardb.gg/v1/z17.0/stale@400L.webp",
            }
        }
    }

    monkeypatch.setattr(helper, "_url_is_reachable", lambda url: False)

    assert helper.get_art_url(
        card_id="pipe-organ", internal_name="Pipe Organ", size="artLarge"
    ) is None


def test_reachable_cached_art_url_is_returned(monkeypatch):
    helper = load_helper()
    url = "https://s.bazaardb.gg/v1/z18.0/current@400L.webp"
    helper._CACHE = {
        "cards": {
            "pipe-organ": {
                "internalName": "Pipe Organ",
                "artLarge": url,
            }
        }
    }

    monkeypatch.setattr(helper, "_url_is_reachable", lambda candidate: candidate == url)

    assert helper.get_art_url(
        card_id="pipe-organ", internal_name="Pipe Organ", size="artLarge"
    ) == url


def test_reachability_result_is_cached(monkeypatch):
    helper = load_helper()
    url = "https://s.bazaardb.gg/v1/z18.0/current@400L.webp"
    calls = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        return Response()

    monkeypatch.setattr(helper.urllib.request, "urlopen", fake_urlopen)
    helper._URL_STATUS_CACHE.clear()

    assert helper._url_is_reachable(url) is True
    assert helper._url_is_reachable(url) is True
    assert len(calls) == 1
