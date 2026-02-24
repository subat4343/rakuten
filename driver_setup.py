# driver_setup.py
import pickle
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver(headless=True, width=1920, height=1080, use_cookies=False):
    """
    Selenium WebDriverをセットアップする共通関数
    :param headless: Trueならブラウザ非表示、Falseなら表示
    :param use_cookies: Trueなら保存されたクッキーを読み込む
    """
    options = Options()
    if headless:
        options.add_argument('--headless')
    # ★★★ 変更点: 引数から受け取った値でウインドウサイズを設定します ★★★
    options.add_argument(f'--window-size={width},{height}')
    
    # --- 高速化のためのオプション ---
    # 起動速度を向上させるため、不要な機能を無効化します。
    options.add_argument('--disable-gpu') # GPUアクセラレーションを無効化
    options.add_argument('--no-sandbox') # セキュリティサンドボックスを無効化（ただしセキュリティリスクは上がる）
    options.add_argument('--disable-dev-shm-usage') # `/dev/shm` の使用を無効化
    options.add_argument('--disable-extensions') # ブラウザ拡張機能を無効化
    options.add_argument('--dns-prefetch-disable') # DNSプリフェッチを無効化
    options.add_argument('--disable-infobars') # 「Chromeは自動テストソフトウェアによって制御されています」のメッセージ非表示
    options.add_experimental_option('excludeSwitches', ['enable-automation']) # Automationフラグを削除
    options.add_experimental_option('useAutomationExtension', False) # AutomationExtensionを無効化
    # -----------------------------
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # ★★★ use_cookies 引数によって処理を分岐 ★★★ 今後の強化のために実装
    if use_cookies:
        cookie_file = "cookies.pkl"
        if os.path.exists(cookie_file):
            # クッキーを設定するために、先にドメインを開く
            driver.get("https://players.pokemon-card.com/") # クッキーを適用したいドメインを事前に開く
            
            cookies = pickle.load(open(cookie_file, "rb"))
            for cookie in cookies:
                # 'expiry' キーがfloatでない場合があるため、チェックして変換または削除
                if 'expiry' in cookie and (cookie['expiry'] is None or not isinstance(cookie['expiry'], (int, float))):
                    del cookie['expiry'] # 無効なexpiryを削除
                driver.add_cookie(cookie)
            print("🍪 保存されたクッキーを読み込みました。")
            driver.refresh() # クッキー適用後にページをリフレッシュして反映させる
            print("🍪 ページをリフレッシュしました。")
        else:
            print("⚠️ クッキーファイル 'cookies.pkl' が見つかりませんでした。")

    # bot検知対策スクリプト（共通）
    driver.execute_cdp_cmd(
        'Page.addScriptToEvaluateOnNewDocument',
        {'source': '''Object.defineProperty(navigator, 'webdriver', {get: () => undefined});'''}
    )
    return driver