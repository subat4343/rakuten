# rakuten_monitor.py (最終修正版)
import re
import time
import json # 追加
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def _find_element_with_multiple_selectors(driver, selectors):
    """
    (修正) driverオブジェクトを直接受け取るように変更。
    複数のCSSセレクタをリストで受け取り、最初に見つかった要素を返す。
    """
    for selector in selectors:
        try:
            # 要素が見つかるまで最大2秒待つ
            short_wait = WebDriverWait(driver, timeout=2) # 正しくdriverを使用
            return short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            continue
    return None

def find_target_product(driver, config):
    """
    (高精度・複数ページ対応版)
    人間の操作に近い手順で在庫を判定する。
    """
    wait = WebDriverWait(driver, config['wait_timeout'])
    product_url = config['target_product_url']
    
    try:
        # --- STEP 1: 商品ページにアクセス ---
        print(f"指定された商品URLにアクセスします...")
        print(f"  URL: {product_url}")
        driver.get(product_url)

        # --- STEP 2: 在庫状況を確認 ---
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            sold_out_keywords = ["売り切れ", "販売期間外", "販売期間が終了しました", "在庫切れ", "再入荷お知らせ"]
            for keyword in sold_out_keywords:
                if keyword in body_text:
                    print(f"-> 在庫がありません。理由: 「{keyword}」の表示を検知")
                    return None
        except Exception:
            pass

        buy_button = None
        buy_button_selectors = [
            "#AddToCartPurchaseButtonFixed button[aria-label='かごに追加']",
            "button[aria-label='かごに追加']",
            "button.b-cart-btn",
            "button[aria-label='購入手続きへ']"
        ]

        for selector in buy_button_selectors:
            try:
                temp_button = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", temp_button)
                time.sleep(0.5)
                buy_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                if buy_button:
                    print(f"-> 在庫を確認しました。（購入可能ボタンを発見: {selector}）")
                    break
            except TimeoutException:
                continue

        if not buy_button:
            print("-> 在庫がありません。（購入ボタンがクリック不可能な状態です）")
            driver.save_screenshot(config['ss_error_path'])
            print(f"  デバッグ用のスクリーンショットを '{config['ss_error_path']}' として保存しました。")
            return None

        # --- STEP 3: 価格と商品名を取得 (複数セレクタ対応) ---
        name_selectors = ["#item-name-area span.normal_reserve_item_name", "h1.item_name"]
        price_selectors = ["#itemPrice div.number--50WuC", "span.price2", "span.sale_price"]

        # (修正) ヘルパー関数に wait オブジェクトではなく driver オブジェクトを渡す
        name_element = _find_element_with_multiple_selectors(driver, name_selectors)
        if not name_element:
            raise Exception("商品名が見つかりませんでした。")
        product_name = name_element.text.strip()

        # (修正) ヘルパー関数に wait オブジェクトではなく driver オブジェクトを渡す
        price_element = _find_element_with_multiple_selectors(driver, price_selectors)
        if not price_element:
            raise Exception("価格が見つかりませんでした。")
        price_text = price_element.text
        price = int(re.sub(r'[¥￥,円]', '', price_text))

        # --- STEP 4: 条件を判定 ---
        if price <= config['max_price']:
            product_info = {
                'name': product_name,
                'url': product_url,
                'price': price,
            }
            print(f"\n🎉 条件に一致する商品を発見しました！")
            print(f"  商品名: {product_info['name']}")
            print(f"  価格: {product_info['price']}円 (上限: {config['max_price']}円)")
            return product_info
        else:
            print(f"-> 価格が上限を超えています。(現在価格: {price}円, 上限: {config['max_price']}円)")
            return None

    except Exception as e:
        print(f"商品チェック中に予期せぬエラーが発生しました: {e}")
        driver.save_screenshot(config['ss_error_path'])
        return None
    
def extract_cart_form_data(driver):
    """
    (最終強化版) 商品ページのJSONデータを解析し、APIリクエストデータを生成する。
    バリエーションがない(SKUが取れない)場合は、単一商品として variant_id なしで構成する。
    """
    try:
        # JSON取得
        try:
            script_elem = driver.find_element(By.ID, "item-page-app-data")
        except NoSuchElementException:
            print("エラー: 商品データ(item-page-app-data)が見つかりません。")
            return None

        json_text = script_elem.get_attribute("innerHTML")
        data = json.loads(json_text)
        
        # データの位置を探索
        sku_info = data.get("newApi", {}).get("itemInfoSku", {})
        if not sku_info:
            sku_info = data.get("api", {}).get("data", {}).get("itemInfoSku", {})
            
        if not sku_info:
            print("エラー: JSONデータから商品情報(itemInfoSku)が見つかりませんでした。")
            return None

        # 1. 基本ID
        shop_id = sku_info.get("shopId")
        item_id = sku_info.get("itemId")
        
        if not shop_id or not item_id:
             print("エラー: ShopIDまたはItemIDが取得できませんでした。")
             return None

        # 2. API URL
        action_url = "https://t.direct.step.rakuten.co.jp/rms/mall/cartAdd/"
        if "purchaseInfo" in sku_info:
             settings = sku_info["purchaseInfo"].get("purchaseBySellType", {}).get("basketSettings", {})
             if "directDomain" in settings:
                 action_url = settings["directDomain"]

        form_data = {
            "shopid": shop_id,
            "itemid": item_id,
            "units": "1", 
            "device": "pc",
            "userid": "itempage",
            "response_encode": "utf8"
        }

        # --- 3. SKU (バリエーション) の収集と選択 ---
        sku_list = sku_info.get("sku", [])
        target_variant_id = None
        
        # 単一商品かバリエーション商品かを判断
        inventory_type = sku_info.get("inventoryType", "normal") # "normal" or "multiple"
        
        print(f"  商品タイプ: {inventory_type} (SKU数: {len(sku_list) if sku_list else 0})")

        if not sku_list:
            # SKUリストがない場合は「単一商品」として扱う
            print("ℹ️ バリエーション情報がないため、単一商品として処理します (variant_idなし)。")
        
        else:
            # SKUリストがある場合の処理
            candidate_skus = []
            for s in sku_list:
                purchase_sku = s.get("newPurchaseSku", {})
                stock_cond = purchase_sku.get("stockCondition", "")
                qty = purchase_sku.get("quantity")
                
                # 在庫あり条件 (売り切れでなく、かつ 数量がNoneまたは1以上)
                if stock_cond != "sold-out" and (qty is None or qty > 0):
                    candidate_skus.append(s)
            
            # 在庫ありが見つからない場合は全商品を候補にする（販売前対策）
            if not candidate_skus:
                print("⚠️ 在庫ありのSKUが見つかりませんでした（販売前または売り切れ）。全SKUを候補にします。")
                candidate_skus = sku_list

            # 候補からの選択処理
            if len(candidate_skus) == 1:
                s = candidate_skus[0]
                # selectorValuesが空の場合は説明なしになる
                desc = " ".join(s.get("selectorValues", []))
                if not desc: desc = "標準(バリエーションなし)"
                
                print(f"ℹ️ 対象SKUを自動選択しました: {desc}")
                target_variant_id = s.get("variantId")
            else:
                # 複数ある場合はユーザー選択
                print("\n" + "="*60)
                print(f"【 商品選択: バリエーション一覧 】")
                print("="*60)
                for index, s in enumerate(candidate_skus):
                    desc = " ".join(s.get("selectorValues", []))
                    if not desc: desc = f"パターン {index+1}"
                    
                    p_sku = s.get("newPurchaseSku", {})
                    status = "在庫あり"
                    if p_sku.get("stockCondition") == "sold-out":
                        status = "×売り切れ(または販売前)"
                    elif p_sku.get("quantity") == 0:
                        status = "×在庫なし"
                    print(f" [{index}] {desc} ... {status}")
                print("="*60)
                
                while True:
                    user_input = input(">> 購入したい商品の番号を入力してください: ")
                    try:
                        idx = int(user_input)
                        if 0 <= idx < len(candidate_skus):
                            target_variant_id = candidate_skus[idx].get("variantId")
                            print(f"\n✅ 選択しました: ID {target_variant_id}")
                            break
                        else:
                            print("⚠️ リストにある番号を入力してください。")
                    except ValueError:
                        print("⚠️ 数字を入力してください。")

            # variant_idが見つかった場合のみセット
            if target_variant_id:
                form_data["variant_id"] = target_variant_id

        # --- 4. オプション (choice) の自動選択 ---
        options = sku_info.get("customizationOptions", [])
        if options:
            choices = []
            for opt in options:
                # 必須項目(required=True)かどうかチェックしても良いが、念のため全て選択しておく
                selections = opt.get("selections", [])
                if selections:
                    val = selections[0].get("value")
                    if val:
                        choices.append(val)
            
            if choices:
                form_data["choice[]"] = choices 
                print(f"  -> 必須オプションを自動設定しました: {choices}")

        # 結果確認ログ
        print(f"APIデータ構築完了: {action_url}")
        return {
            "url": action_url,
            "data": form_data
        }

    except Exception as e:
        print(f"データ抽出中に予期せぬエラーが発生しました: {e}")
        import traceback
        traceback.print_exc() # 詳細エラーを出力
        return None