# message_formatter.py
import json
import os
import sys

# --- モジュールレベルでのテンプレート読み込み ---
def _load_templates():
    """メッセージテンプレートをJSONファイルから読み込む"""
    template_file = 'message_templates.json'
    if not os.path.exists(template_file):
        print(f"エラー: メッセージテンプレートファイル '{template_file}' が見つかりません。")
        sys.exit(1)
    
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            templates = json.load(f)
        print("メッセージテンプレートを読み込みました。")
        return templates
    except json.JSONDecodeError:
        print(f"エラー: '{template_file}' のJSON形式が正しくありません。")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: テンプレートファイル '{template_file}' の読み込みに失敗しました: {e}")
        sys.exit(1)

MESSAGE_TEMPLATES = _load_templates()

def _format_message(template_lines, params):
    """テンプレートとパラメータから最終的なメッセージ文字列を生成する内部関数"""
    if not template_lines:
        return "メッセージテンプレートが設定されていません。"
        
    message = "\n".join(template_lines)
    return message.format(**params)


def create_discovery_message(notification_method, event):
    """イベント発見通知メッセージを作成する"""
    template_lines = MESSAGE_TEMPLATES.get('discovery', {}).get(notification_method, [])
    
    params = {
        'title': event['title'],
        'url': event['url']
    }
    
    return _format_message(template_lines, params)


def create_result_message(notification_method, event, player_id, success, apply_message):
    """自動応募結果の通知メッセージを作成する"""
    template_lines = MESSAGE_TEMPLATES.get('result', {}).get(notification_method, [])

    # ★★★ LINE通知かつ応募成功の場合、メッセージに注釈を追加 ★★★
    if success and notification_method == 'line':
        apply_message += f"\n\n[確認] スクリーンショットを 'applied_{player_id}.png' として保存しました。"

    params = {
        'title': event['title'],
        'player_id': player_id,
        'status_icon': '🎉' if success else '❌',
        'apply_message': apply_message
    }

    return _format_message(template_lines, params)