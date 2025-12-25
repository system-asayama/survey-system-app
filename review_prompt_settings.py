"""
口コミ投稿促進設定のバックエンドロジック
"""
from enum import Enum
from datetime import datetime
from typing import Optional
from db_config import get_db_connection, get_cursor
from utils import _sql

class ReviewPromptMode(Enum):
    """口コミ投稿促進モード"""
    ALL = 'all'  # 全ての評価に投稿を促す（推奨・デフォルト）
    HIGH_RATING_ONLY = 'high_rating_only'  # 星4以上のみ投稿を促す（リスクあり）


def get_review_prompt_mode(store_id: int) -> str:
    """
    店舗の口コミ投稿促進モードを取得
    
    Args:
        store_id: 店舗ID
    
    Returns:
        str: 'all' または 'high_rating_only'（デフォルト: 'all'）
    """
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    try:
        cur.execute(_sql(conn, '''
            SELECT review_prompt_mode 
            FROM "T_店舗_口コミ投稿促進設定" 
            WHERE store_id = %s
        '''), (store_id,))
        
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        else:
            # デフォルトは 'all'
            return ReviewPromptMode.ALL.value
    finally:
        conn.close()


def should_show_review_button(store_id: int, rating: int) -> bool:
    """
    レビュー投稿ボタンを表示すべきかどうかを判定
    
    Args:
        store_id: 店舗ID
        rating: 評価（1〜5）
    
    Returns:
        bool: 表示すべきかどうか
    """
    mode = get_review_prompt_mode(store_id)
    
    if mode == ReviewPromptMode.ALL.value:
        # 全ての評価に対して表示
        return True
    elif mode == ReviewPromptMode.HIGH_RATING_ONLY.value:
        # 星4以上のみ表示
        return rating >= 4
    else:
        # デフォルトは全ての評価
        return True


def save_review_prompt_mode(
    store_id: int, 
    mode: str, 
    admin_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    warnings_shown: bool = False,
    checkboxes_confirmed: bool = False
) -> None:
    """
    店舗の口コミ投稿促進モードを保存
    
    Args:
        store_id: 店舗ID
        mode: 'all' または 'high_rating_only'
        admin_id: 管理者ID（オプション）
        ip_address: IPアドレス（オプション）
        user_agent: ユーザーエージェント（オプション）
        warnings_shown: 警告を表示したかどうか
        checkboxes_confirmed: チェックボックスで確認したかどうか
    """
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    try:
        # 現在の設定を取得
        cur.execute(_sql(conn, '''
            SELECT review_prompt_mode 
            FROM "T_店舗_口コミ投稿促進設定" 
            WHERE store_id = %s
        '''), (store_id,))
        
        row = cur.fetchone()
        old_value = row[0] if row and row[0] else ReviewPromptMode.ALL.value
        
        # 設定を更新
        cur.execute(_sql(conn, '''
            UPDATE "T_店舗_口コミ投稿促進設定" 
            SET review_prompt_mode = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE store_id = %s
        '''), (mode, store_id))
        
        # レコードが存在しない場合は作成
        if cur.rowcount == 0:
            cur.execute(_sql(conn, '''
                INSERT INTO "T_店舗_口コミ投稿促進設定" (store_id, review_prompt_mode)
                VALUES (%s, %s)
            '''), (store_id, mode))
        
        # ログを記録
        log_review_prompt_mode_change(
            conn=conn,
            store_id=store_id,
            admin_id=admin_id,
            old_value=old_value,
            new_value=mode,
            ip_address=ip_address,
            user_agent=user_agent,
            warnings_shown=warnings_shown,
            checkboxes_confirmed=checkboxes_confirmed
        )
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def log_review_prompt_mode_change(
    conn,
    store_id: int,
    admin_id: Optional[int],
    old_value: str,
    new_value: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    warnings_shown: bool = False,
    checkboxes_confirmed: bool = False
) -> None:
    """
    口コミ投稿促進モードの変更ログを記録
    
    Args:
        conn: データベース接続
        store_id: 店舗ID
        admin_id: 管理者ID
        old_value: 変更前の値
        new_value: 変更後の値
        ip_address: IPアドレス
        user_agent: ユーザーエージェント
        warnings_shown: 警告を表示したかどうか
        checkboxes_confirmed: チェックボックスで確認したかどうか
    """
    cur = get_cursor(conn)
    
    cur.execute(_sql(conn, '''
        INSERT INTO "T_口コミ投稿促進設定ログ" (
            store_id, user_id, review_prompt_mode, warnings_shown, checkboxes_confirmed
        )
        VALUES (%s, %s, %s, %s, %s)
    '''), (
        store_id, 
        admin_id, 
        new_value,
        warnings_shown,
        checkboxes_confirmed
    ))


def get_stores_needing_reminder() -> list:
    """
    リマインドが必要な店舗のリストを取得
    （high_rating_only設定で、30日以上リマインドされていない店舗）
    
    Returns:
        list: 店舗IDのリスト
    """
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    try:
        cur.execute(_sql(conn, '''
            SELECT g.store_id, s.名称
            FROM "T_店舗_口コミ投稿促進設定" g
            JOIN "T_店舗" s ON g.store_id = s.id
            WHERE g.review_prompt_mode = %s
        '''), (ReviewPromptMode.HIGH_RATING_ONLY.value,))
        
        return [{'store_id': row[0], 'store_name': row[1]} for row in cur.fetchall()]
    finally:
        conn.close()


def record_reminder_sent(store_id: int, action_taken: Optional[str] = None) -> None:
    """
    リマインド送信を記録
    
    Args:
        store_id: 店舗ID
        action_taken: 実行されたアクション（オプション）
    """
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    try:
        mode = get_review_prompt_mode(store_id)
        
        cur.execute(_sql(conn, '''
            INSERT INTO "T_店舗_Google設定_リマインド" (
                store_id, review_prompt_mode, action_taken
            )
            VALUES (%s, %s, %s)
        '''), (store_id, mode, action_taken))
        
        conn.commit()
    finally:
        conn.close()
