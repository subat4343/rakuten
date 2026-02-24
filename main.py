# main.py (購入手続きボタン専用・最終版)
import sys
import time
import traceback
from datetime import datetime

# --- モジュールインポート ---
from config_loader import load_config
from driver_setup import setup_driver
from notifier import send_notification
from rakuten_login import user_login, ensure_sudo_mode
from fast_monitor import wait_for_sale_and_api_add_to_cart 
from rakuten_purchase import purchase_from_cart
from rakuten_monitor import extract_cart_form_data
from rakuten_purchase import purchase_from_cart

def main():
    """(API高速化版) 指定時刻に商品を監視し、APIでカート追加して最速で購入する"""
    print(f"--- 楽天 自動購入プログラム (API高速待機版) ---")
    
    config = load_config()

    try:
        sale_time_str = config['sale_start_time'].strip('"\'')
        sale_time = datetime.strptime(sale_time_str, "%H:%M:%S").time()
        print(f"目標時刻: {sale_time_str}")
    except (ValueError, KeyError):
        print("エラー: config.iniのSaleStartTimeが 'HH:MM:SS' 形式で正しく設定されていません。")
        sys.exit(1)

    driver = None
    try:
        driver = setup_driver(headless=config['headless'])
        print("\nSTEP 1: ログイン処理を開始します...")
        if not user_login(driver, config):
            message = "ログインに失敗しました。処理を中断します。"
            send_notification(config, f"【❌ログイン失敗】\n{message}")
            sys.exit(1)
        print("-> ログイン成功！")

        # ★★★ 追加点: 事前認証で「購入時の再ログイン」を回避する ★★★
        ensure_sudo_mode(driver, config)
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        
        print(f"\nSTEP 2: 販売ページに事前にアクセスし、API情報を取得します...")
        driver.get(config['target_product_url'])
        
        # ★★★ APIデータの自動抽出 ★★★
        # ここで商品ページからフォーム情報をスクレイピングする
        api_info = extract_cart_form_data(driver)
        
        if not api_info:
            print("❌ エラー: カートAPI情報の取得に失敗しました。")
            print("   ページ構造が想定と異なるか、在庫切れ表示などでフォームが存在しない可能性があります。")
            send_notification(config, "【⚠️準備エラー】\nカートAPI情報の取得に失敗したため、処理を終了します。")
            return
        
        print(f"-> API情報取得成功。待機モードへ移行します。")

        print("\nSTEP 3: 販売開始時刻まで高速API待機ループに入ります...")
        
        # ★★★ API版の待機関数を実行 ★★★
        success = wait_for_sale_and_api_add_to_cart(driver, config, sale_time, api_info)

        if not success:
            print("-> カート追加に失敗したか、エラーが発生しました。処理を終了します。")
            send_notification(config, "【⚠️待機終了】\nAPIによるカート追加に失敗しました。")
            return

        print("\nSTEP 4: 最速購入フローを開始します！")
        # ★ 変更なし：wait_for_sale_and_api_add_to_cart 内でカートURLへ遷移済み
        success, message = purchase_from_cart(driver, config)

        if success:
            result_message = f"【✅購入成功報告✅】\n■ URL: {config['target_product_url']}\n■ 結果: {message}"
            send_notification(config, result_message, config['ss_success_path'])
        else:
            error_message = f"【❌購入失敗】\n■ URL: {config['target_product_url']}\n■ 理由: {message}"
            send_notification(config, error_message, config['ss_error_path'])

    except KeyboardInterrupt:
        print("\nユーザーによって処理が中断されました。")
    except Exception as e:
        print(f"\n予期せぬエラーにより処理が中断されました: {e}")
        traceback.print_exc()
        send_notification(config, f"【❌重大エラー】\n予期せぬエラーが発生し、プログラムが停止しました。\n理由: {e}")
    finally:
        if driver:
            print("\nWebDriverを終了します。")
            driver.quit()
        print("プログラムを終了します。")

if __name__ == '__main__':
    main()