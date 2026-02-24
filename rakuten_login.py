# rakuten_login.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def user_login(driver, config):
    """
    楽天のログイン処理（2段階フロー・ログアウト確認対応版）
    """
    wait = WebDriverWait(driver, config['wait_timeout'])
    login_id = config['login_id']
    password = config['password']
    
    print("--- 楽天 ログイン処理を開始します ---")

    try:
        # STEP 1: ログインページにアクセス
        print(f"[STEP 1] ログインページにアクセスします: {config['login_url']}")
        driver.get(config['login_url'])

        # STEP 2: ユーザIDを入力
        print("[STEP 2] ユーザID入力フィールドの表示を待ちます。")
        id_field = wait.until(EC.presence_of_element_located((By.ID, "user_id")))
        print("[STEP 3] ユーザIDを入力します。")
        id_field.send_keys(login_id)
        
        # STEP 4: 「次へ」ボタンをクリック
        print("[STEP 4] 「次へ」ボタンをクリックします。")
        wait.until(EC.element_to_be_clickable((By.ID, "cta001"))).click()

        # STEP 5: パスワードを入力
        print("[STEP 5] パスワード入力フィールドの表示を待ちます。")
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password_current")))
        print("[STEP 6] パスワードを入力します。")
        password_field.send_keys(password)

        # STEP 7: ログインボタンをクリック
        print("[STEP 7] ログインボタンをクリックします。")
        wait.until(EC.element_to_be_clickable((By.ID, "cta011"))).click()

        # ★★★★★★★★★★★★★★★★★★★ ここが修正点 ★★★★★★★★★★★★★★★★★★★
        # STEP 8: ログイン成功の確認
        # ログイン成功の証として「ログアウト」リンクが表示されるのを待つ
        member_page_link_selector = "a[href*='my.rakuten.co.jp']"
        print(f"[STEP 8] ログイン成功の証として「会員情報」リンクが表示されるのを待ちます...")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, member_page_link_selector)))
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

        print("-> 「会員情報」リンクの表示を確認。ログインに成功しました！")
        return True

    except TimeoutException:
        print("-> ログイン処理中にタイムアウトが発生しました。")
        print("   ID、パスワード、またはページ要素のセレクタが間違っている可能性があります。")
        driver.save_screenshot(config['ss_error_path'])
        print(f"  エラー時のスクリーンショットを '{config['ss_error_path']}' として保存しました。")
        return False
    except Exception as e:
        print(f"ログイン処理中に予期せぬエラーが発生しました: {e.__class__.__name__}")
        driver.save_screenshot(config['ss_error_path'])
        return False
    
def ensure_sudo_mode(driver, config):
    """
    【追加機能】購入直前のパスワード再入力を防ぐため、
    事前に「購入履歴」ページへアクセスし、高セキュリティ認証(Sudoモード)を済ませておく。
    """
    print("\n--- 高セキュリティ認証(Sudoモード)の事前取得を開始します ---")
    wait = WebDriverWait(driver, 5) # 短めのタイムアウト
    
    try:
        # 購入履歴ページへアクセス（ここは必ず認証を求められるエリア）
        driver.get("https://order.my.rakuten.co.jp/")
        
        # パスワード入力欄があるか確認
        try:
            # 汎用的にパスワード欄を探す
            password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            print("-> 再認証画面を検知しました。パスワードを入力して認証を更新します。")
            
            password_field.clear()
            password_field.send_keys(config['password'])
            
            # ログインボタンを探してクリック
            # rakuten_purchase.py と同様のロジックでボタンを探す
            login_selectors = [
                (By.ID, "cta011"), # 新仕様
                (By.ID, "login_submit"), # 旧仕様
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(., 'ログイン')]")
            ]
            
            clicked = False
            for by, selector in login_selectors:
                try:
                    btn = driver.find_element(by, selector)
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        print(f"-> 認証ボタンをクリックしました ({selector})")
                        break
                except NoSuchElementException:
                    continue
            
            if not clicked:
                print("⚠️ 認証ボタンが見つかりませんでした。スキップします。")
                return True # エラーにはせず進む

            # 遷移待ち（購入履歴一覧などの要素が出るまで）
            try:
                wait.until(EC.presence_of_element_located((By.ID, "ratAccountId"))) # ページ固有のIDなどを待つ
                print("-> 認証を通過しました。")
            except TimeoutException:
                print("-> 遷移を確認できませんでしたが、処理を続行します。")

        except TimeoutException:
            print("-> パスワード入力欄が出現しませんでした（既に認証済みと判断）。")
        
        return True

    except Exception as e:
        print(f"⚠️ 事前認証処理中にエラーが発生しましたが、メイン処理には影響しません: {e}")
        return True # ここでの失敗は致命的ではないのでTrueを返す