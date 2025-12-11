#!/usr/bin/env python3.11
"""
1,000,000回のスピンシミュレーション（修正版）
5回スピンの合計点数と景品分布を分析

重要: config.jsonのprobは「そのシンボルが3つ揃う確率」
"""
import json
import random
from collections import defaultdict
from datetime import datetime

# 設定を読み込み
with open('data/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 景品設定を読み込み
with open('data/settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)
    prizes = settings.get('prizes', [])

symbols = config['symbols']
miss_prob = config.get('miss_probability', 20.0) / 100.0  # 20% → 0.2

# 通常シンボルとリーチシンボルを分類
normal_symbols = [s for s in symbols if not s.get('is_reach', False)]
reach_symbols = [s for s in symbols if s.get('is_reach', False)]

def choice_by_prob(symbols_list):
    """確率に基づいてシンボルを選択"""
    # probの合計を計算
    total_prob = sum(float(s['prob']) for s in symbols_list)
    if total_prob <= 0:
        return random.choice(symbols_list)
    
    # 乱数を生成
    r = random.random() * total_prob
    
    # 累積確率で選択
    cumulative = 0.0
    for s in symbols_list:
        cumulative += float(s['prob'])
        if r < cumulative:
            return s
    
    return symbols_list[-1]

def simulate_spin():
    """
    1回のスピンをシミュレート
    
    ロジック:
    1. ミスフラグ判定（miss_probability%）
       - True: 通常シンボルからランダムに選び、1,2コマ目を異なるものにする → 0点
    2. ミスフラグがFalse:
       - 全シンボル（通常+リーチ）から確率で選択
       - 通常シンボル: 3つ揃い → 配当あり
       - リーチシンボル: 1,2コマ目同じ、3コマ目異なる → 0点（リーチ演出）
    """
    # ミスフラグ判定
    if random.random() < miss_prob:
        # ハズレ: 1,2コマ目を異なるシンボルにする
        reel1 = random.choice(normal_symbols)
        other_symbols = [s for s in normal_symbols if s['id'] != reel1['id']]
        if other_symbols:
            reel2 = random.choice(other_symbols)
        else:
            reel2 = reel1
        reel3 = random.choice(normal_symbols)
        return 0, False  # 配当0、リーチなし
    
    # 通常の抽選: 全シンボルから確率で選択
    symbol = choice_by_prob(symbols)
    
    # リーチシンボルの場合
    if symbol.get('is_reach', False):
        # リーチハズレ: 配当0、リーチ演出あり
        return 0, True
    
    # 通常シンボルの場合: 3つ揃い
    payout = symbol.get('payout_3', 0)
    return payout, False

def simulate_5_spins():
    """5回スピンの合計点数を計算"""
    total = 0
    for _ in range(5):
        payout, is_reach = simulate_spin()
        total += payout
    return total

def get_prize_for_score(score):
    """点数から景品を判定"""
    for prize in prizes:
        min_score = prize.get('min_score', 0)
        max_score = prize.get('max_score', float('inf'))
        if max_score is None:
            max_score = float('inf')
        if min_score <= score <= max_score:
            return prize['rank']
    return '該当なし'

# シミュレーション実行
print("=" * 70)
print("シミュレーション開始: 1,000,000回の5スピンセット（修正版）")
print("=" * 70)
print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
print("設定情報:")
print(f"  - ミスフラグ確率: {miss_prob * 100:.1f}%")
print(f"  - 期待値（5回スピン）: {config.get('expected_total_5', 'N/A')}点")
print()

N = 1_000_000
score_distribution = defaultdict(int)
prize_distribution = defaultdict(int)

for i in range(N):
    if (i + 1) % 100000 == 0:
        print(f"進捗: {i + 1:,} / {N:,} ({(i + 1) / N * 100:.1f}%)")
    
    total_score = simulate_5_spins()
    score_distribution[total_score] += 1
    prize = get_prize_for_score(total_score)
    prize_distribution[prize] += 1

print()
print(f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 結果をファイルに保存
result = {
    'simulation_count': N,
    'timestamp': datetime.now().isoformat(),
    'config': config,
    'prizes': prizes,
    'score_distribution': dict(score_distribution),
    'prize_distribution': dict(prize_distribution)
}

with open('simulation_result_1m_correct.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# 結果を表示
print("=" * 70)
print("景品分布")
print("=" * 70)
for prize in prizes:
    rank = prize['rank']
    count = prize_distribution.get(rank, 0)
    percentage = count / N * 100
    min_score = prize.get('min_score', 0)
    max_score = prize.get('max_score', 'なし')
    print(f"{rank:8s} ({min_score:4d}～{str(max_score):>4s}点): {count:8,}回 ({percentage:6.3f}%)")

print()
print("=" * 70)
print("点数分布の統計")
print("=" * 70)

# 点数の統計
all_scores = []
for score, count in score_distribution.items():
    all_scores.extend([score] * count)

if all_scores:
    avg_score = sum(all_scores) / len(all_scores)
    max_score = max(all_scores)
    min_score = min(all_scores)
    print(f"平均点数: {avg_score:.2f}")
    print(f"最高点数: {max_score}")
    print(f"最低点数: {min_score}")
    print(f"期待値との比較: {avg_score:.2f} / {config.get('expected_total_5', 'N/A')}")

print()
print("=" * 70)
print("主要な点数帯の分布")
print("=" * 70)

# 点数帯ごとの集計
score_ranges = [
    (500, float('inf'), '500点以上（特賞）'),
    (300, 499, '300-499点（1等）'),
    (200, 299, '200-299点（2等）'),
    (150, 199, '150-199点（3等）'),
    (50, 149, '50-149点（4等）'),
    (0, 49, '0-49点（5等）'),
]

for min_s, max_s, label in score_ranges:
    count = sum(cnt for score, cnt in score_distribution.items() 
                if min_s <= score <= max_s)
    percentage = count / N * 100
    print(f"{label:25s}: {count:8,}回 ({percentage:6.3f}%)")

print()
print("=" * 70)
print("シンボル別の理論確率")
print("=" * 70)
print(f"{'シンボル':<10s} {'配当':>6s} {'3つ揃い確率':>12s}")
print("-" * 70)
for s in symbols:
    if not s.get('is_reach', False):
        print(f"{s['label']:<10s} {s.get('payout_3', 0):6.0f}点 {s['prob']:11.3f}%")
print()
print("リーチハズレシンボル:")
for s in symbols:
    if s.get('is_reach', False):
        reach_target = s.get('reach_symbol', '?')
        print(f"{s['label']:<10s} (リーチ) {s['prob']:11.3f}%  → {reach_target}のリーチミス")

print()
print("=" * 70)
print(f"結果は simulation_result_1m_correct.json に保存されました")
print("=" * 70)
