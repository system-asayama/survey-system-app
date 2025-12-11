#!/usr/bin/env python3.11
"""
1,000,000回のスピンシミュレーション
5回スピンの合計点数と景品分布を分析
"""
import json
import secrets
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
miss_prob = config.get('miss_probability', 20.0)

# ミスフラグの確率（20%）
MISS_FLAG_PROB = 20.0

def choice_by_prob(symbols_list):
    """確率に基づいてシンボルを選択"""
    buckets = []
    acc = 0
    for s in symbols_list:
        w = max(0, int(round(float(s['prob']) * 100)))
        acc += w
        buckets.append((acc, s))
    if acc <= 0:
        return symbols_list[-1]
    r = secrets.randbelow(acc)
    for edge, s in buckets:
        if r < edge:
            return s
    return symbols_list[-1]

def simulate_spin():
    """1回のスピンをシミュレート（3リール）"""
    # ミスフラグ判定（20%）
    miss_flag = secrets.randbelow(10000) < (MISS_FLAG_PROB * 100)
    
    if miss_flag:
        # ミスフラグ: 最初の2リールを異なるシンボルにする
        reel1 = choice_by_prob(symbols)
        reel2 = choice_by_prob(symbols)
        # reel1とreel2が同じ場合は再選択
        while reel2['id'] == reel1['id']:
            reel2 = choice_by_prob(symbols)
        reel3 = choice_by_prob(symbols)
        return [reel1, reel2, reel3], 0, False
    
    # 通常の選択
    reel1 = choice_by_prob(symbols)
    reel2 = choice_by_prob(symbols)
    reel3 = choice_by_prob(symbols)
    
    # リーチシンボルの処理
    if reel1.get('is_reach') and reel2.get('is_reach'):
        # 両方リーチシンボルの場合、元のシンボルで判定
        base_symbol1 = reel1.get('reach_symbol')
        base_symbol2 = reel2.get('reach_symbol')
        if base_symbol1 == base_symbol2:
            # リーチミス
            return [reel1, reel2, reel3], 0, True
    
    # 通常の揃い判定
    if reel1['id'] == reel2['id'] == reel3['id']:
        payout = reel1.get('payout_3', 0)
        return [reel1, reel2, reel3], payout, False
    
    # ハズレ
    return [reel1, reel2, reel3], 0, False

def simulate_5_spins():
    """5回スピンの合計点数を計算"""
    total = 0
    for _ in range(5):
        reels, payout, is_reach = simulate_spin()
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
print("シミュレーション開始: 1,000,000回の5スピンセット")
print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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

with open('simulation_result_1m.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# 結果を表示
print("=" * 60)
print("景品分布")
print("=" * 60)
for prize in prizes:
    rank = prize['rank']
    count = prize_distribution.get(rank, 0)
    percentage = count / N * 100
    print(f"{rank:8s}: {count:8,}回 ({percentage:6.3f}%)")

print()
print("=" * 60)
print("点数分布の統計")
print("=" * 60)

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

print()
print("=" * 60)
print("主要な点数帯の分布")
print("=" * 60)

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
    print(f"{label:20s}: {count:8,}回 ({percentage:6.3f}%)")

print()
print("結果は simulation_result_1m.json に保存されました")
