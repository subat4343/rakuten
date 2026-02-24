import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def _click_if_exists(driver, by, selector, description):
    """
    要素が存在し、表示されていればクリックするヘルパー関数
    """
    try:
        elements = driver.find_elements(by, selector)
        for element in elements:
            if element.is_displayed() and element.is_enabled():
                # 重なり防止のためJavaScriptでクリック
                driver.execute_script("arguments[0].click();", element)
                print(f"-> 「{description}」をクリックしました。")
                return True
    except Exception:
        pass
    return False

def purchase_from_cart(driver, config):
    """
    (高速版専用) 買い物かご以降のフローを動的に判定して実行する。
    URLと画面要素の両方を見て、最適なアクションを行う。
    """
    wait_timeout = config.get('wait_timeout', 20)
    wait = WebDriverWait(driver, wait_timeout)
    
    try:
        # --- STEP 1: 買い物かごページで「購入手続き」ボタンをクリック ---
        print("[PURCHASE-STEP 1] 買い物かごページで「購入手続き」ボタンを探します...")
        
        cart_btn_selectors = [
            (By.CSS_SELECTOR, "button[aria-label='購入手続き']"),
            (By.CSS_SELECTOR, "button[aria-label='ご購入手続き']"),
            (By.XPATH, "//button[contains(., '購入手続き')]"), # テキスト検索追加
            (By.CSS_SELECTOR, "input.purchaseButton")
        ]
        
        clicked_cart = False
        for by, selector in cart_btn_selectors:
            if _click_if_exists(driver, by, selector, "購入手続き"):
                clicked_cart = True
                break
        
        if not clicked_cart:
            try:
                # 少し待ってから再試行
                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='購入手続き'], input.purchaseButton")))
                driver.execute_script("arguments[0].click();", btn)
                print("-> 「購入手続き」ボタンをクリックしました (Wait後)。")
            except TimeoutException:
                raise Exception("買い物かごの「購入手続き」ボタンが見つかりませんでした。")

        # --- STEP 2 ～ 3: 遷移先に応じた動的対応 (ループ処理) ---
        print("\n[PURCHASE-STEP 2-3] ページ遷移を監視し、適切なアクションを実行します...")
        
        # 最大試行時間
        end_time = time.time() + 60 
        
        while time.time() < end_time:
            # 現在のURLを取得して、ある程度の位置を推測する
            current_url = driver.current_url
            
            # エラー画面に到達していないかチェック
            if "error" in current_url:
                print("⚠️ エラー画面を検出しました。処理を中断する可能性があります。")
            
            # ---------------------------------------------------
            # 1. 最終確認画面 (注文確定) の判定
            # ---------------------------------------------------
            # URLに 'confirm' が含まれるか、確定ボタンがあるか
            commit_selectors = [
                (By.CSS_SELECTOR, "button[aria-label='注文を確定する']"),
                (By.XPATH, "//button[contains(., '注文を確定する')]"), # テキスト検索追加
                (By.CSS_SELECTOR, "input[name='commit']"),
                (By.ID, "commit")
            ]
            
            for by, sel in commit_selectors:
                if _click_if_exists(driver, by, sel, "注文を確定する"):
                    print("-> 最終確認画面でボタンを押下しました。完了を待ちます。")
                    
                    # ダミーモード確認
                    if not config.get('auto_purchase', False):
                        print("【ダミーモード】実際には注文しませんでした。")
                        return True, "【ダミーモード】最終確認ページ到達成功"

                    time.sleep(3)
                    driver.save_screenshot(config['ss_success_path'])
                    print(f"-> 完了時のスクリーンショットを保存しました: {config['ss_success_path']}")
                    return True, "自動購入処理が完了しました！"

            # ---------------------------------------------------
            # 2. 届け先指定画面 (スキップ) の判定
            # ---------------------------------------------------
            # URLに 'shipping' が含まれるか、次へボタンがあるか
            next_selectors = [
                (By.CSS_SELECTOR, "button[aria-label='次へ']"),
                (By.XPATH, "//button[contains(., '次へ')]"), # テキスト検索追加
                (By.CSS_SELECTOR, "input[value='次へ']")
            ]
            
            for by, sel in next_selectors:
                if _click_if_exists(driver, by, sel, "次へ（届け先指定）"):
                    time.sleep(0.2) # 遷移待ち
                    continue # ループ先頭へ戻る

            # ---------------------------------------------------
            # 3. ログイン画面 (ID/パスワード入力) の判定
            # ---------------------------------------------------
            # パスワード入力欄が見えているか確認
            try:
                # ID入力欄がある場合 (IDから求められるパターン)
                user_ids = driver.find_elements(By.ID, "user_id")
                if user_ids and user_ids[0].is_displayed():
                    print("-> ログイン画面(ID入力)を検出。")
                    user_ids[0].clear()
                    user_ids[0].send_keys(config['login_id'])
                    _click_if_exists(driver, By.ID, "cta001", "次へ(ログインID)")
                    time.sleep(0.2)
                    continue

                # パスワード入力欄がある場合
                pws = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                target_pw = None
                for pw in pws:
                    if pw.is_displayed():
                        target_pw = pw
                        break
                
                if target_pw:
                    print("-> ログイン画面(パスワード入力)を検出。")
                    target_pw.clear()
                    target_pw.send_keys(config['password'])
                    
                    # ログインボタン候補 (新旧網羅)
                    login_btn_selectors = [
                        (By.ID, "cta011"),
                        (By.ID, "login_submit"),
                        (By.XPATH, "//button[contains(., 'ログイン')]"),
                        (By.CSS_SELECTOR, "input[type='submit']")
                    ]
                    
                    for by, sel in login_btn_selectors:
                        if _click_if_exists(driver, by, sel, "ログイン実行"):
                            break
                    time.sleep(0.2)
                    continue

            except Exception:
                pass

            # 少し待機して再監視 (高速化のため0.1秒)
            time.sleep(0.1)

        raise TimeoutException("最終確認画面または次のアクションが見つからないままタイムアウトしました。")

    except Exception as e:
        error_msg = f"購入処理中にエラーが発生しました: {e}"
        print(error_msg)
        driver.save_screenshot(config['ss_error_path'])
        return False, error_msg
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass