from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


MANAGE_URL = "https://www.fanbox.cc/manage/relationships?status=supporter"
RELATIONSHIP_PATH = re.compile(r"/manage/relationships/(\d+)(?:[/?#]|$)")
LOAD_MORE_LABELS = {"もっと見る", "さらに表示", "show more", "load more"}


class AuthenticationRequired(RuntimeError):
    pass


def default_profile_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / "FanboxSupporterUpdater" / "ChromeProfile"


def build_driver(profile_dir: Path, *, headless: bool) -> webdriver.Chrome:
    profile_dir.mkdir(parents=True, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--window-size=1400,1200")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-search-engine-choice-screen")
    if headless:
        options.add_argument("--headless=new")

    return webdriver.Chrome(options=options)


def relationship_user_id(url: str) -> str | None:
    match = RELATIONSHIP_PATH.search(urlparse(url).path)
    return match.group(1) if match else None


def clean_name(element) -> str | None:
    values: list[str] = []

    # FANBOX has historically rendered the user name in a TextEllipsis child.
    # This is only a preference; the relationship URL is the stable identifier.
    try:
        for child in element.find_elements(By.CSS_SELECTOR, "[class*='TextEllipsis']"):
            values.append(child.text)
    except StaleElementReferenceException:
        return None

    try:
        values.extend(
            [
                element.get_attribute("aria-label") or "",
                element.get_attribute("title") or "",
                element.text,
            ]
        )
    except StaleElementReferenceException:
        return None

    for value in values:
        for line in value.splitlines():
            name = " ".join(line.split()).strip()
            if 0 < len(name) <= 200:
                return name
    return None


def collect_visible_supporters(driver: webdriver.Chrome) -> dict[str, str]:
    supporters: dict[str, str] = {}
    for element in driver.find_elements(By.CSS_SELECTOR, "a[href*='/manage/relationships/']"):
        try:
            href = element.get_attribute("href") or ""
        except StaleElementReferenceException:
            continue
        user_id = relationship_user_id(href)
        if not user_id:
            continue
        name = clean_name(element)
        if name:
            supporters.setdefault(user_id, name)
    return supporters


def click_load_more(driver: webdriver.Chrome) -> bool:
    for element in driver.find_elements(By.CSS_SELECTOR, "button, [role='button']"):
        try:
            label = " ".join(element.text.split()).strip().casefold()
            if label in LOAD_MORE_LABELS and element.is_displayed() and element.is_enabled():
                driver.execute_script("arguments[0].click()", element)
                return True
        except (StaleElementReferenceException, WebDriverException):
            continue
    return False


def is_authentication_page(driver: webdriver.Chrome) -> bool:
    parsed = urlparse(driver.current_url)
    path = parsed.path.casefold()
    return (
        "accounts.pixiv.net" in parsed.netloc.casefold()
        or "/login" in path
        or "/signin" in path
    )


def wait_for_login(driver: webdriver.Chrome, timeout: int) -> None:
    logging.info("FANBOXへのログインを待っています。表示された画面でログインしてください。")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if "/manage/relationships" in urlparse(driver.current_url).path:
            return
        time.sleep(1)
    raise AuthenticationRequired("ログイン完了を確認できませんでした。もう一度セットアップを実行してください。")


def scrape_supporters(driver: webdriver.Chrome, *, setup: bool, timeout: int) -> list[str]:
    driver.get(MANAGE_URL)
    WebDriverWait(driver, timeout).until(
        lambda current: current.execute_script("return document.readyState") == "complete"
    )

    if setup:
        wait_for_login(driver, max(timeout, 600))
    elif is_authentication_page(driver):
        raise AuthenticationRequired(
            "FANBOXのログイン期限が切れています。setup_login.bat を実行して再ログインしてください。"
        )

    # A login can return to a URL without the supporter filter.
    if driver.current_url.split("#", 1)[0] != MANAGE_URL:
        driver.get(MANAGE_URL)

    deadline = time.monotonic() + timeout
    supporters: dict[str, str] = {}
    stable_rounds = 0
    previous_state: tuple[int, int] | None = None

    while time.monotonic() < deadline:
        if is_authentication_page(driver):
            raise AuthenticationRequired(
                "FANBOXのログイン期限が切れています。setup_login.bat を実行して再ログインしてください。"
            )

        supporters.update(collect_visible_supporters(driver))
        clicked = click_load_more(driver)
        height = int(driver.execute_script("return document.body.scrollHeight") or 0)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        state = (len(supporters), height)

        if state == previous_state and not clicked:
            stable_rounds += 1
        else:
            stable_rounds = 0
        previous_state = state

        if supporters and stable_rounds >= 3:
            break
        time.sleep(1.5)

    if not supporters:
        raise RuntimeError(
            "支援者を1件も取得できませんでした。既存ファイルは変更していません。"
            "FANBOXの画面変更またはログイン切れを確認してください。"
        )

    logging.info("支援者を%d件取得しました。", len(supporters))
    return list(supporters.values())


def write_if_changed(output: Path, names: list[str]) -> bool:
    content = "".join(f"{name}\n" for name in names)
    old_content = output.read_text(encoding="utf-8") if output.exists() else None
    if old_content == content:
        logging.info("支援者一覧に変更はありません。")
        return False

    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary, output)
    logging.info("%s を更新しました。", output.name)
    return True


def parse_args() -> argparse.Namespace:
    project_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="FANBOXの支援者名を取得します。")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="専用Chromeを表示し、初回ログインまたは再ログインを行います。",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="通常更新でもChrome画面を表示します。",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=default_profile_dir(),
        help="ログイン状態を保存する専用Chromeプロファイルの場所。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "PatronName.txt",
        help="出力ファイル。",
    )
    parser.add_argument("--timeout", type=int, default=90, help="ページ読み込みの待機秒数。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    driver = None
    try:
        driver = build_driver(args.profile_dir.resolve(), headless=not (args.setup or args.visible))
        names = scrape_supporters(driver, setup=args.setup, timeout=args.timeout)
        write_if_changed(args.output.resolve(), names)
        return 0
    except AuthenticationRequired as exc:
        logging.error("%s", exc)
        return 2
    except Exception as exc:
        logging.exception("更新に失敗しました: %s", exc)
        return 1
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    sys.exit(main())
