import argparse
import logging
import os

import pandas as pd
import requests
import shioaji as sj
from dotenv import load_dotenv
from shioaji import constant as sjc

from cbat.crawl import crawl_version_num_and_file_url
from cbat.excel_parser import get_cbs
from cbat.logging import setup_logging
from cbat.utils import line_notify, read_json, save_json

log = logging.getLogger("CB-Auto-Trade")

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--no-simulation", action="store_true", default=False)
arg_parser.add_argument("--money-per-transaction", type=int, default=10000)
arg_parser.add_argument("--buy", action="store_true", default=False)
args = arg_parser.parse_args()
no_simulation = args.no_simulation
money_per_transaction = args.money_per_transaction

load_dotenv()


def main() -> None:
    log.info(
        f"參數: no_simulation={no_simulation}, money_per_transaction={money_per_transaction}, buy={args.buy}"
    )

    line_notify_token = os.getenv("LINE_NOTIFY_TOKEN")
    if line_notify_token is None:
        log.warning("沒有找到 LINE Notify 的環境變數, 將無法發送 LINE Notify")

    log.info("正在爬取 Excel 版本號及檔案連結...")
    try:
        version, file_url = crawl_version_num_and_file_url()
    except Exception as e:
        log.error("爬取 Excel 版本號及檔案連結失敗", exc_info=e)
        line_notify(line_notify_token, "\n[錯誤] 爬取 Excel 版本號及檔案連結失敗")
        return

    saved = read_json("saved.json")
    if version == saved.get("version"):
        log.info(f"沒有找到新的版本, 當前版本: {version}")
        return

    log.info(f"發現新的版本號: {version}")
    log.info(f"正在從 {file_url} 下載 Excel...")
    try:
        df = pd.read_excel(file_url, header=2)
    except Exception as e:
        log.error("下載 Excel 檔案失敗", exc_info=e)
        line_notify(line_notify_token, "\n[錯誤] 下載 Excel 檔案失敗")
        return

    log.info("正在解析 Excel...")
    try:
        excel_cbs = get_cbs(df)
    except Exception as e:
        log.error("Excel 解析失敗", exc_info=e)
        line_notify(line_notify_token, "\n[錯誤] Excel 解析失敗")
        return
    log.info(f"在 Excel 內找到 {len(excel_cbs)} 個可轉債")

    saved_cbs = saved.get("cbs", {})

    log.info("正在儲存版本號和 Excel 內的可轉債...")
    saved["version"] = version
    saved["cbs"] = {cb.stock_id: cb.dump_json() for cb in excel_cbs}
    save_json("saved.json", saved)

    new_cbs = [cb for cb in excel_cbs if cb.stock_id not in saved_cbs]
    if not new_cbs:
        log.info("沒有新的可轉債, 正在退出...")
        return

    log.info(f"找到了 {len(new_cbs)} 個新的可轉債")
    if len(new_cbs) == len(excel_cbs):
        log.info("所有可轉債都是新的, 正在退出...")
        return
    for cb in new_cbs:
        line_notify(line_notify_token, f"\n[新的可轉債] {cb}\n[yahoo] {cb.yahoo_url}")

    if not args.buy:
        log.info("沒有指定 --buy 參數, 正在退出...")
        return

    try:
        api_key = os.environ["API_KEY"]
        api_secret = os.environ["API_SECRET"]
        ca_path = os.environ["CA_PATH"]
        ca_passwd = os.environ["CA_PASSWD"]
        person_id = os.environ["PERSON_ID"]
    except KeyError as e:
        log.error(f"找不到永豐金 API 的環境變數: {e}")
        line_notify(line_notify_token, f"\n[錯誤] 找不到永豐金 API 的環境變數: {e}")
        return

    log.info("正在登入永豐金 API...")
    api = sj.Shioaji(simulation=not no_simulation)
    try:
        api.login(api_key=api_key, secret_key=api_secret)
    except Exception as e:
        log.error("登入永豐金 API 失敗", exc_info=e)
        line_notify(line_notify_token, "\n[錯誤] 登入永豐金 API 失敗")
        return

    log.info("正在啟用憑證...")
    try:
        api.activate_ca(ca_path=ca_path, ca_passwd=ca_passwd, person_id=person_id)
    except Exception as e:
        log.error("憑證啟用失敗", exc_info=e)
        line_notify(line_notify_token, "\n[錯誤] 憑證啟用失敗")
        return

    log.info("正在取得帳戶餘額...")
    try:
        account_balance = api.account_balance().acc_balance
    except Exception as e:
        log.error("取得帳戶餘額失敗", exc_info=e)
        line_notify(line_notify_token, "\n[錯誤] 取得帳戶餘額失敗")
        return
    if not no_simulation:
        account_balance = 100000000
    log.info(f"帳戶餘額: NTD${account_balance}")

    log.info("正在購買新的可轉債...")
    for cb in new_cbs:
        log.info(f"正在下單 {cb}")
        if account_balance < money_per_transaction:
            log.info(f"帳戶餘額小於 NTD${money_per_transaction}, 正在退出...")
            return
        try:
            last_close_price = requests.get(
                f"https://stock-api.seriaati.xyz/history_trades/{cb.stock_id}?limit=1"
            ).json()[-1]["close_price"]
        except Exception as e:
            log.error(f"取得 {cb} 最後收盤價失敗", exc_info=e)
            line_notify(line_notify_token, f"\n[錯誤] 取得 {cb} 最後收盤價失敗")
            continue

        try:
            contract = api.Contracts.Stocks[cb.stock_id]
            quantity = money_per_transaction // last_close_price
            api.place_order(
                contract=contract,
                order=sj.Order(
                    price=last_close_price,
                    quantity=quantity,
                    action=sjc.Action.Buy,
                    price_type=sjc.StockPriceType.LMT,
                    order_type=sjc.OrderType.ROD,
                    order_lot=sjc.StockOrderLot.IntradayOdd,
                ),
            )
        except Exception as e:
            log.error(f"{cb} 下單失敗", exc_info=e)
            line_notify(line_notify_token, f"\n[錯誤] {cb} 下單失敗")
            continue

        spent = quantity * last_close_price
        account_balance -= spent
        log.info(
            f"下單成功 {cb}, 數量: {quantity} 股, 花費 NTD${spent}, 帳戶餘額: NTD${account_balance}"
        )
        line_notify(
            line_notify_token,
            f"\n[下單成功] {cb}\n\n數量: {quantity} 股\n收盤價: {last_close_price}\n花費 NTD${spent}\n帳戶餘額: NTD${account_balance}",
        )


with setup_logging():
    log.info("正在啟動...")
    try:
        main()
    except KeyboardInterrupt:
        log.info("用戶中止")
    except Exception as e:
        log.error("發生錯誤", exc_info=e)
    log.info("已退出")
