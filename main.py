import re
import logging
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


logger = logging.getLogger(__name__)


def ttl_cache(func: Callable, ttl: int = 30) -> Callable:
    cached_data: dict[str, tuple[float, Any]] = {}

    @functools.wraps(func)
    def cached_func(*args: Any, **kwargs: Any) -> Any:
        key = "|".join(args)
        key += "|".join(f"{k}={v}" for k, v in kwargs.items())
        now = time.time()

        if entry := cached_data.get(key):
            timestamp, value = entry
            if now - timestamp > ttl:
                logger.debug("cache entry expired for: %s", key)
                value = func(*args, **kwargs)
                cached_data[key] = (now, value)
        else:
            logger.debug("cache empty for: %s", key)
            value = func(*args, **kwargs)
            cached_data[key] = (now, value)

        return value

    return cached_func


def search(value: str, pass_location: str) -> Iterable[str]:
    tokens = re.split(r"[ \/]", value.lower())

    for item in get_all_passwords(pass_location):
        search_item = item.lower()
        if all(token in search_item for token in tokens):
            yield item


@ttl_cache
def get_all_passwords(pass_location: str) -> list[str]:
    results = []
    path = os.path.expanduser(pass_location)
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
        pass_location = extension.preferences["pass_location"]

        try:
            max_results_value = extension.preferences["max_results"]
            max_results = int(max_results_value)
        except ValueError:
            # don't crash the entire extension if this is invalid
            logger.error(
                "Invalid value for max_results: %s",
                max_results_value,
            )
            max_results = 5

        argument = event.get_argument() or ""

        results: list[ExtensionResultItem] = []
        for entry in search(argument, pass_location):
            results.append(ExtensionResultItem(
                icon="images/icon.png",
                name=entry,
                description=entry,
                # TODO: running with args does not seem to work
                # generating a string this way is definitely not ideal
                on_enter=RunScriptAction(f"pass -c {entry}"),
            ))
            if len(results) >= max_results:
                break

        return RenderResultListAction(results)


if __name__ == "__main__":
    PassExtension().run()
