# line_notifier.py
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    TextMessage,
    PushMessageRequest
)

def send_line_message(token, group_id, message):
    """指定された単一のグループIDにプッシュメッセージを送信する"""
    if not token or not group_id:
        print("LINE通知スキップ: トークンまたはグループIDがありません。")
        return

    configuration = Configuration(access_token=token)
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        push_message_request = PushMessageRequest(
            to=group_id,
            messages=[TextMessage(text=message.strip())]
        )

        try:
            messaging_api.push_message(push_message_request)
            print(f"LINEグループ (ID: {group_id[:10]}...) にメッセージを送信しました。")
        except Exception as e:
            error_body = getattr(e, 'body', 'N/A')
            error_status = getattr(e, 'status', 'N/A')
            print(f"LINEへのメッセージ送信に失敗しました。")
            print(f"  ステータス: {error_status}")
            print(f"  詳細: {error_body}")