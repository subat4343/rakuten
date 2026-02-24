import sys
import configparser
import os

def load_config():
    """設定ファイル(config.ini)を読み込み、辞書として返す"""
    config_file = 'config.ini'
    if not os.path.exists(config_file):
        print(f"エラー: 設定ファイル '{config_file}' が見つかりません。")
        sys.exit(1)

    config = configparser.RawConfigParser()
    config.read(config_file, 'utf-8')

    try:
        # --- 基本設定、商品情報などの読み込み (変更なし) ---
        settings = {
            'headless': config.getboolean('SETTINGS', 'HeadlessMode', fallback=True),
            'interval': config.getint('SETTINGS', 'CheckIntervalSeconds'),
            'wait_timeout': config.getint('SETTINGS', 'WaitTimeoutSeconds'),
            'notification_method': config.get('SETTINGS', 'NotificationMethod', fallback='none').lower(),
            'window_width': config.getint('SETTINGS', 'WindowWidth', fallback=1920),
            'window_height': config.getint('SETTINGS', 'WindowHeight', fallback=1080),
            'persistent_mode': config.getboolean('SETTINGS', 'PersistentMode', fallback=False),
            'sale_start_time': config.get('SETTINGS', 'SaleStartTime'),
            'pre_sale_wait_seconds': config.getint('SETTINGS', 'PreSaleWaitSeconds', fallback=180),
            'polling_interval_ms': config.getint('SETTINGS', 'PollingIntervalMilliseconds', fallback=100),
            'max_price': config.getint('PRODUCT', 'MaxPrice'),
            'auto_purchase': config.getboolean('PURCHASE', 'AutoPurchaseEnabled'),
            'login_id': config.get('ACCOUNT_INFO', 'LoginID'),
            'password': config.get('ACCOUNT_INFO', 'Password').strip('"\''),
            'base_url': config.get('URLS', 'BaseURL'),
            'login_url': config.get('URLS', 'LoginPageURL'),
            'target_product_url': config.get('URLS', 'TargetProductURL'),
            'cart_url': config.get('URLS', 'CartURL'),
            'ss_success_path': config.get('FILE_PATHS', 'SuccessScreenshot'),
            'ss_error_path': config.get('FILE_PATHS', 'ErrorScreenshot'),
        }
        
        # ★★★★★ ここからが修正箇所 ★★★★★

        # --- 通知設定の読み込みとバリデーション ---
        method = settings['notification_method']
        
        if method == 'line':
            print("通知方法: LINE")
            token = config.get('LINE', 'ChannelAccessToken', fallback='').strip()
            group_id = config.get('LINE', 'TargetGroupID', fallback='').strip()
            
            # バリデーションチェック
            is_valid = True
            if not token or token.startswith("ここに"):
                print("警告: config.ini の [LINE] ChannelAccessToken が正しく設定されていません。")
                is_valid = False
            if not group_id or not group_id.startswith(('C', 'U')): # GroupIDは'C', UserIDは'U'で始まる
                print("警告: config.ini の [LINE] TargetGroupID が正しく設定されていません。")
                is_valid = False

            if is_valid:
                settings['token'] = token
                settings['group_id'] = group_id
            else:
                print("-> LINE通知を無効にして処理を続行します。")
                settings['notification_method'] = 'none'

        elif method == 'discord':
            print("通知方法: Discord")
            webhook_url = config.get('DISCORD', 'WebhookURL', fallback='').strip()

            # バリデーションチェック
            if webhook_url and webhook_url.startswith('https://discord.com/api/webhooks/'):
                settings['webhook_url'] = webhook_url
            else:
                print("警告: config.ini の [DISCORD] WebhookURL が正しく設定されていません。")
                print("-> Discord通知を無効にして処理を続行します。")
                settings['notification_method'] = 'none'

        elif method == 'none':
            # 何もしない (通知無効が意図通り)
            pass
        else:
            print(f"警告: config.ini で不明な通知方法 '{method}' が指定されています。通知は行われません。")
            settings['notification_method'] = 'none'
        
        # ★★★★★ 修正箇所ここまで ★★★★★

        # --- アカウント情報のバリデーション (変更なし) ---
        if settings['auto_purchase'] and (not settings['login_id'] or not settings['password']):
            print("エラー: 自動購入が有効ですが、LoginID または Password が設定されていません。")
            sys.exit(1)
            
        return settings
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"エラー: 設定ファイル '{config_file}' の読み込みに失敗しました。項目が不足している可能性があります: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: 設定ファイル '{config_file}' の読み込み中に予期せぬエラーが発生しました: {e}")
        sys.exit(1)