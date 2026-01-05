import functools
import logging
import os
import re
import time
from collections.abc import Iterable
from typing import Any, Callable

from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem

logger = logging.getLogger(__name__)

cached_data: dict[str, tuple[float, Any]] = {}


def ttl_cache(func: Callable, ttl: int = 30) -> Callable:
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
        keyword = event.get_keyword()

        match keyword:
            case "p":
                results = get_search_results(argument, pass_location, max_results)
            case "pg":
                results = generate_password(argument)

        return RenderResultListAction(results)


def generate_password(
    argument: str,
) -> list[ExtensionResultItem]:
    if not argument:
        return []

    return [
        ExtensionResultItem(
            icon="images/generate.png",
            name=f"Generate password: {argument}",
            description=f"Generate a password for {argument}",
            on_enter=RunScriptAction(
                f"pass generate -c {argument} && notify-send 'Password generated' 'Password for {argument} generated and copied to clipboard'"
            ),
        )
    ]


def get_search_results(
    argument: str,
    pass_location: str,
    max_results: int,
) -> list[ExtensionResultItem]:
    results: list[ExtensionResultItem] = []

    for entry in search(argument, pass_location):
        results.append(
            ExtensionResultItem(
                icon="images/icon.png",
                name=entry,
                description=entry,
                # TODO: running with args does not seem to work
                # generating a string this way is definitely not ideal
                on_enter=RunScriptAction(
                    f"pass -c {entry} && notify-send 'Password copied' 'Password for {entry} copied to clipboard'"
                ),
            )
        )
        if len(results) >= max_results:
            break
    return results


if __name__ == "__main__":
    PassExtension().run()
