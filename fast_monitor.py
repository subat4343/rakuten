# fast_monitor.py (最終確定版・ポップアップセレクタ修正)
import time
import requests  # 追加
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def click_add_to_cart_once(driver, selectors):
    """
    「かごに追加」ボタンを一度だけクリック試行する。
    """
    for by, selector in selectors:
        try:
            button = driver.find_element(by, selector)
            driver.execute_script("arguments[0].click();", button)
            print(f"-> 「かごに追加」ボタンのクリック命令を送信 ({selector})")
            return True
        except (NoSuchElementException, StaleElementReferenceException):
            continue
    return False

def wait_for_sale_and_click_proceed_only(driver, config, sale_time):
    """
    (最終版) 販売時刻に「かごに追加」を1回クリックし、
    ポップアップ表示を待ってから成功と判断する。
    その後は後続の purchase_from_cart に任せるため、買い物かごURLへ遷移する。
    """
    # --- 設定値の読み込み ---
    polling_interval = config.get('polling_interval_ms', 50) / 1000.0
    wait_timeout = config.get('wait_timeout', 10)

    # --- 時刻設定 ---
    if isinstance(sale_time, str):
        sale_time = datetime.strptime(sale_time, "%H:%M:%S").time()
    sale_datetime = datetime.combine(datetime.today(), sale_time)

    # --- 販売開始時刻まで待機 ---
    print(f"販売開始時刻: {sale_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("販売開始時刻まで待機します...")
    while datetime.now() < sale_datetime:
        time.sleep(0.01)

    print(f"販売時刻 {datetime.now().strftime('%H:%M:%S.%f')} - 購入処理を開始！")

    # STEP 1: 「かごに追加」ボタンのセレクタを定義
    add_to_cart_selectors = [
        (By.XPATH, "//span[contains(text(), 'かごに追加')]/ancestor::button"),
        (By.XPATH, "//button[contains(., 'かごに追加')]"),
    ]

    # STEP 2: 改行コードに強いポップアップのセレクタに修正
    success_popup_selector = (By.XPATH, "//*[contains(., '商品をかごに') and contains(., '追加しました')]")

    # STEP 3: タイムアウトループ処理
    timeout_limit = time.time() + 30
    clicked = False

    while time.time() < timeout_limit:
        if not clicked:
            if click_add_to_cart_once(driver, add_to_cart_selectors):
                clicked = True
                print("-> 「かごに追加」クリック成功。ポップアップの表示を待ちます...")

        if clicked:
            try:
                short_wait = WebDriverWait(driver, 0.5)
                short_wait.until(EC.visibility_of_element_located(success_popup_selector))

                print(f"\n成功！「商品をかごに追加しました」ポップアップを確認。時刻: {datetime.now().strftime('%H:%M:%S.%f')}")
                print("-> 買い物かごページへ遷移します...")

                driver.get(config['cart_url'])
                return True

            except TimeoutException:
                time.sleep(polling_interval)
                continue

    print("\nタイムアウトしました。「かごに追加」の成功を確認できませんでした。")
    error_path = config.get('ss_error_path', 'error_capture.png')
    driver.save_screenshot(error_path)
    print(f"タイムアウト時のスクリーンショットを '{error_path}' として保存しました。")
    return False

def wait_for_sale_and_api_add_to_cart(driver, config, sale_time, api_info):
    """
    (API版・リトライ機能付き) 指定時刻まで待機し、APIリクエストでカートに追加する。
    失敗時は指定回数リトライを行う。
    """
    # --- 設定 ---
    MAX_RETRIES = 10       # 最大リトライ回数
    RETRY_INTERVAL = 0.1   # リトライ間隔(秒)

    # --- 時刻設定 ---
    if isinstance(sale_time, str):
        sale_time = datetime.strptime(sale_time, "%H:%M:%S").time()
    sale_datetime = datetime.combine(datetime.today(), sale_time)

    # --- Session構築 ---
    selenium_cookies = driver.get_cookies()
    session = requests.Session()
    for cookie in selenium_cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))
    
    user_agent = driver.execute_script("return navigator.userAgent;")
    headers = {
        "User-Agent": user_agent,
        "Referer": config['target_product_url'],
        "Origin": "https://item.rakuten.co.jp",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # --- 待機ループ ---
    print(f"販売開始時刻: {sale_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("販売開始時刻までAPI待機モードに入ります (Request準備完了)...")
    
    while datetime.now() < sale_datetime:
        time.sleep(0.01)

    print(f"販売時刻 {datetime.now().strftime('%H:%M:%S.%f')} - APIリクエスト送信開始！")

    # --- API実行 (リトライループ) ---
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[{attempt}/{MAX_RETRIES}] API送信試行中...")
            
            response = session.post(
                api_info['url'],
                data=api_info['data'],
                headers=headers,
                timeout=5  # タイムアウトは短めに設定して次へ行く
            )
            
            # --- レスポンス解析 ---
            is_success = False
            
            if response.status_code == 200:
                try:
                    res_json = response.json()
                    result_code = res_json.get("resultCode", "")
                    
                    # 楽天APIのエラー判定
                    if result_code and result_code.startswith("R"):
                        err_msg = res_json.get("resultMessage", "").replace("<br>", " ")
                        print(f"  ❌ APIエラー: {err_msg} (Code: {result_code})")
                        
                        # 「売り切れ」の場合はリトライしても無駄なことが多いが、
                        # 復活を期待してリトライするか、ここで終了するかは戦略次第。
                        # 今回は「失敗したら再実行」の要望通りリトライを継続します。
                        is_success = False
                    else:
                        is_success = True
                except:
                    # JSONパース失敗時はHTMLが返っている可能性がある
                    if "error" not in response.url:
                        is_success = True
            else:
                print(f"  ❌ HTTPエラー: ステータス {response.status_code}")
                is_success = False

            # --- 成功時の処理 ---
            if is_success:
                print(f"-> [成功] APIリクエスト成功！(試行回数: {attempt})")
                
                # Cookie同期
                try:
                    for cookie in session.cookies:
                        try:
                            driver.add_cookie({
                                'name': cookie.name,
                                'value': cookie.value,
                                'path': '/',
                            })
                        except Exception:
                            pass
                except Exception:
                    pass

                print("-> 買い物かごページへ遷移します...")
                driver.get(config['cart_url'])
                return True
            
            # --- 失敗時 (ループ継続) ---
            # 最後の試行でなければ待機して次へ
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_INTERVAL)

        except Exception as e:
            print(f"  ❌ 通信エラー発生: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_INTERVAL)

    # 全リトライ失敗
    print(f"-> 諦めます。{MAX_RETRIES}回のリトライすべてに失敗しました。")
    return False