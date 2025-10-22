import re
import os
import time
import functools
from typing import Callable, Any
from collections.abc import Iterable

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction


def ttl_cache(func: Callable, ttl: int = 30) -> Callable:
    cached_data: dict[str, tuple[float, Any]] = {}

    @functools.wraps(func)
    def cached_func(*args: Any, **kwargs: Any) -> Any:
        # right now, search doesn't take any arguments
        # so I don't need to code any key generation
        # mechanism
        key = "fixed"
        now = time.time()

        if entry := cached_data.get(key):
            timestamp, value = entry
            if now - timestamp > ttl:
                value = func(*args, **kwargs)
                cached_data[key] = (now, value)
        else:
            value = func(*args, **kwargs)
            cached_data[key] = (now, value)

        return value

    return cached_func


def search(value: str) -> Iterable[str]:
    tokens = re.split(r"[ \/]", value.lower())

    for item in get_all_passwords():
        search_item = item.lower()
        if all(token in search_item for token in tokens):
            yield item


@ttl_cache
def get_all_passwords() -> list[str]:
    results = []
    path = os.path.expanduser("~/.password-store")
    for root, dirs, files in os.walk(path):
        relative_path = root.removeprefix(path)
        for file in files:
            if file.endswith(".gpg"):
                item = f"{relative_path}/{file}"
                item = item.removeprefix("/")
                item = item.removesuffix(".gpg")
                results.append(item)

    return results


class PassExtension(Extension):
    def __init__(self) -> None:
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(
        self,
        event: KeywordQueryEvent,
        extension: Extension,
    ) -> RenderResultListAction:
        argument = event.get_argument() or ""

        results: list[ExtensionResultItem] = []
        for entry in search(argument):
            results.append(ExtensionResultItem(
                icon="images/icon.png",
                name=entry,
                description=entry,
                # TODO: running with args does not seem to work
                # generating a string this way is definitely not ideal
                on_enter=RunScriptAction(f"pass -c {entry}"),
            ))
            if len(results) >= 5:
                break

        return RenderResultListAction(results)


if __name__ == "__main__":
    PassExtension().run()
