"""スロット景品判定ロジック"""
import json
import os

def get_prize_for_score(score, settings_path="data/settings.json"):
    """
    スロットの点数に応じた景品を判定する
    
    Args:
        score: スロットの合計点数
        settings_path: 設定ファイルのパス
    
    Returns:
        dict: {"rank": "1等", "name": "ランチ無料券"} または None
    """
    # 設定ファイルから景品リストを読み込み
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            prizes = settings.get("prizes", [])
    else:
        prizes = []
    
    # 景品が設定されていない場合はNone
    if not prizes:
        return None
    
    # 点数が高い順にソート済みと仮定し、該当する景品を探す
    for prize in prizes:
        if score >= prize["min_score"]:
            return {
                "rank": prize["rank"],
                "name": prize["name"]
            }
    
    # 該当する景品がない場合はNone
    return None
