#!/usr/bin/env python3
"""
口コミ投稿促進設定のリマインド送信スクリプト
high_rating_only設定の店舗に対して、30日ごとにリマインドを送信
"""
import sys
from datetime import datetime
from review_prompt_settings import get_stores_needing_reminder, record_reminder_sent, get_review_prompt_mode
from db_config import get_db_connection, get_cursor
from utils import _sql

def send_reminder_email(store_id, store_name, admin_emails):
    """
    リマインドメールを送信（実装例）
    
    Args:
        store_id: 店舗ID
        store_name: 店舗名
        admin_emails: 管理者メールアドレスのリスト
    """
    subject = f"【重要】{store_name} - 口コミ投稿促進設定のリマインド"
    
    body = f"""
{store_name} の管理者様

口コミ投稿促進設定について、定期リマインドをお送りします。

現在の設定：「星4以上のみ投稿を促す」

この設定は以下のリスクがあります：

【Googleによるペナルティ】
- 全レビューの非公開化
- 新規レビュー受付停止
- 警告メッセージの表示
- ビジネスプロフィールの削除

【ステマ規制法違反】
- 措置命令
- 罰金（最大300万円）
- 社名公表

【推奨する対応】
安全な設定「全ての評価に投稿を促す」への変更をご検討ください。

設定変更はこちら：
https://your-domain.com/admin/store_settings/{store_id}/review_prompt

このリマインドは30日ごとに送信されます。

---
アンケートシステム管理者
"""
    
    print(f"[リマインド送信] 店舗: {store_name} (ID: {store_id})")
    print(f"  宛先: {', '.join(admin_emails)}")
    print(f"  件名: {subject}")
    
    # 実際のメール送信処理をここに実装
    # 例: SMTPライブラリを使用してメール送信
    # send_email(to=admin_emails, subject=subject, body=body)
    
    # デモ用：メール内容をログに出力
    print(f"  本文:\n{body}\n")
    
    return True

def get_store_admins(store_id):
    """
    店舗の管理者メールアドレスを取得
    
    Args:
        store_id: 店舗ID
    
    Returns:
        list: 管理者メールアドレスのリスト
    """
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    try:
        # 店舗のテナントIDを取得
        cur.execute(_sql(conn, '''
            SELECT tenant_id FROM "T_店舗" WHERE id = %s
        '''), (store_id,))
        
        row = cur.fetchone()
        if not row:
            return []
        
        tenant_id = row[0]
        
        # テナント管理者のメールアドレスを取得
        cur.execute(_sql(conn, '''
            SELECT DISTINCT a.email
            FROM "T_テナント管理者" a
            JOIN "T_テナント管理者_テナント" at ON a.id = at.tenant_admin_id
            WHERE at.tenant_id = %s AND a.active = 1
        '''), (tenant_id,))
        
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

def main():
    """メイン処理"""
    print("=" * 60)
    print("口コミ投稿促進設定リマインド送信")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # リマインドが必要な店舗を取得
    stores = get_stores_needing_reminder()
    
    if not stores:
        print("リマインドが必要な店舗はありません。")
        return
    
    print(f"\nリマインド対象店舗: {len(stores)}件\n")
    
    success_count = 0
    error_count = 0
    
    for store in stores:
        store_id = store['store_id']
        store_name = store['store_name']
        
        try:
            # 管理者メールアドレスを取得
            admin_emails = get_store_admins(store_id)
            
            if not admin_emails:
                print(f"[警告] 店舗 {store_name} (ID: {store_id}) の管理者メールアドレスが見つかりません")
                continue
            
            # リマインドメールを送信
            if send_reminder_email(store_id, store_name, admin_emails):
                # 送信記録を保存
                record_reminder_sent(store_id, action_taken='email_sent')
                success_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            print(f"[エラー] 店舗 {store_name} (ID: {store_id}) の処理中にエラー: {e}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"送信完了: {success_count}件")
    print(f"エラー: {error_count}件")
    print("=" * 60)

if __name__ == '__main__':
    main()
