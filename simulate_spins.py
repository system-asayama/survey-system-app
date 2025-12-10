#!/usr/bin/env python3.11
"""
スロットスピンのシミュレーションスクリプト
実際の/spinエンドポイントの動作を模倣して、期待値と確率分布を検証する
"""

import json
import random
from collections import Counter

def load_config():
    """設定ファイルを読み込む"""
    with open('data/config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def simulate_spin(config):
    """1回のスピン（5回転）をシミュレート"""
    symbols = config['symbols']
    miss_probability = config.get('miss_probability', 0.0)
    
    # 確率の正規化
    total_prob = sum(float(s['prob']) for s in symbols)
    if total_prob == 0:
        total_prob = 100.0
    
    normalized_symbols = []
    for s in symbols:
        normalized_symbols.append({
            'id': s['id'],
            'label': s['label'],
            'payout_3': s['payout_3'],
            'prob': float(s['prob']) / total_prob * 100.0
        })
    
    total_payout = 0.0
    miss_rate = miss_probability / 100.0
    
    # 5回スピン
    for _ in range(5):
        # まずハズレかどうかを判定
        if random.random() < miss_rate:
            # ハズレ：0点
            payout = 0
        else:
            # 当たり：確率に基づいてシンボルを選択
            rand_val = random.random() * 100.0
            cumulative = 0.0
            selected_symbol = normalized_symbols[0]
            
            for sym in normalized_symbols:
                cumulative += sym['prob']
                if rand_val <= cumulative:
                    selected_symbol = sym
                    break
            
            payout = selected_symbol['payout_3']
        
        total_payout += payout
    
    return total_payout

def main():
    """メイン処理"""
    config = load_config()
    
    print("=" * 60)
    print("スロットスピンシミュレーション")
    print("=" * 60)
    print(f"5回スピンの期待値設定: {config.get('expected_total_5', 100.0)}点")
    print(f"ハズレ確率: {config.get('miss_probability', 0.0)}%")
    print()
    
    # シミュレーション回数
    num_simulations = 10000
    print(f"シミュレーション回数: {num_simulations:,}回")
    print()
    
    # シミュレーション実行
    results = []
    for _ in range(num_simulations):
        total = simulate_spin(config)
        results.append(total)
    
    # 統計情報を計算
    average = sum(results) / len(results)
    min_val = min(results)
    max_val = max(results)
    
    print("=" * 60)
    print("シミュレーション結果")
    print("=" * 60)
    print(f"平均値: {average:.2f}点")
    print(f"最小値: {min_val:.0f}点")
    print(f"最大値: {max_val:.0f}点")
    print()
    
    # 点数範囲別の確率を計算
    ranges = [
        (0, 0, "ハズレ（0点）"),
        (1, 100, "1-100点"),
        (101, 200, "101-200点"),
        (201, 300, "201-300点"),
        (301, 500, "301-500点"),
        (501, 1000, "501点以上"),
    ]
    
    print("=" * 60)
    print("点数範囲別の確率分布")
    print("=" * 60)
    
    for min_score, max_score, label in ranges:
        count = sum(1 for r in results if min_score <= r <= max_score)
        probability = count / len(results) * 100
        print(f"{label:20s}: {probability:6.2f}% ({count:5d}回)")
    
    print()
    
    # 0-100点の範囲（ハズレ含む）
    count_0_100 = sum(1 for r in results if 0 <= r <= 100)
    prob_0_100 = count_0_100 / len(results) * 100
    print(f"0-100点（ハズレ含む）: {prob_0_100:.2f}%")
    
    # 期待値との比較
    expected = config.get('expected_total_5', 100.0)
    diff = average - expected
    diff_percent = (diff / expected) * 100 if expected > 0 else 0
    
    print()
    print("=" * 60)
    print("期待値との比較")
    print("=" * 60)
    print(f"理論値: {expected:.2f}点")
    print(f"実測値: {average:.2f}点")
    print(f"差分: {diff:+.2f}点 ({diff_percent:+.2f}%)")
    
    if abs(diff_percent) < 5:
        print("✓ 期待値は理論値と一致しています（誤差5%以内）")
    else:
        print("✗ 期待値が理論値と大きく乖離しています")

if __name__ == '__main__':
    main()
