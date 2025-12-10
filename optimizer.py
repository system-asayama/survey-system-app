"""
確率最適化アルゴリズム

目標確率と期待値から各シンボルの確率を最適化する
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import random


@dataclass
class Symbol:
    id: str
    label: str
    payout_3: float
    prob: float = 0.0
    is_reach: bool = False
    reach_symbol: Optional[str] = None


def optimize_symbol_probabilities(
    symbols: List[Symbol],
    target_probs: Dict[str, float],
    target_expected_value: float,
    miss_probability: float,
    max_iterations: int = 10000,
    tolerance: float = 0.01
) -> Optional[List[Symbol]]:
    """
    目標確率と期待値から各シンボルの確率を最適化する
    
    Args:
        symbols: シンボルのリスト
        target_probs: 各点数範囲の目標確率 {'500': 1.0, '300': 3.0, ...}
        target_expected_value: 5回スピンの目標期待値
        miss_probability: ハズレ確率 (%)
        max_iterations: 最大反復回数
        tolerance: 許容誤差
    
    Returns:
        最適化されたシンボルのリスト（失敗時はNone）
    """
    
    # シンボルを配当でグループ化
    symbol_groups = {}
    for symbol in symbols:
        payout = symbol.payout_3
        if payout not in symbol_groups:
            symbol_groups[payout] = []
        symbol_groups[payout].append(symbol)
    
    # 各点数範囲に対応する配当を特定
    payout_ranges = {}
    for range_key, target_prob in target_probs.items():
        # range_keyの形式: "min-max" または "min-999"
        parts = range_key.split('-')
        if len(parts) == 2:
            min_payout = int(parts[0])
            max_payout = int(parts[1])
            
            if max_payout >= 999:
                # 以上の場合
                payout_ranges[range_key] = [s for s in symbols if s.payout_3 >= min_payout]
            else:
                # 範囲の場合
                payout_ranges[range_key] = [s for s in symbols if min_payout <= s.payout_3 <= max_payout]
    
    # 初期確率を設定（均等分配）
    for range_key, range_symbols in payout_ranges.items():
        if range_symbols:
            target_prob = target_probs.get(range_key, 0.0)
            prob_per_symbol = target_prob / len(range_symbols)
            for symbol in range_symbols:
                symbol.prob = prob_per_symbol
    
    # 反復最適化
    best_symbols = [Symbol(s.id, s.label, s.payout_3, s.prob, s.is_reach, s.reach_symbol) for s in symbols]
    best_error = float('inf')
    
    for iteration in range(max_iterations):
        # 現在の期待値を計算
        current_expected = calculate_expected_value(symbols, miss_probability)
        
        # 各点数範囲の確率を計算
        current_range_probs = {}
        for range_key, range_symbols in payout_ranges.items():
            current_range_probs[range_key] = sum(s.prob for s in range_symbols)
        
        # 誤差を計算
        expected_error = abs(current_expected - target_expected_value)
        prob_errors = sum(abs(current_range_probs.get(k, 0) - v) for k, v in target_probs.items())
        total_error = expected_error + prob_errors * 10  # 確率誤差に重みを付ける
        
        # 最良解を更新
        if total_error < best_error:
            best_error = total_error
            best_symbols = [Symbol(s.id, s.label, s.payout_3, s.prob, s.is_reach, s.reach_symbol) for s in symbols]
        
        # 収束判定
        if total_error < tolerance:
            break
        
        # 確率を調整
        # 1. 期待値の調整
        if current_expected < target_expected_value:
            # 高配当シンボルの確率を上げる
            high_payout_symbols = sorted(symbols, key=lambda s: s.payout_3, reverse=True)[:3]
            for symbol in high_payout_symbols:
                symbol.prob *= 1.01
        else:
            # 低配当シンボルの確率を上げる
            low_payout_symbols = sorted(symbols, key=lambda s: s.payout_3)[:3]
            for symbol in low_payout_symbols:
                symbol.prob *= 1.01
        
        # 2. 各範囲の確率を調整
        for range_key, target_prob in target_probs.items():
            current_prob = current_range_probs.get(range_key, 0)
            if abs(current_prob - target_prob) > tolerance:
                adjustment_factor = target_prob / (current_prob + 1e-9)
                for symbol in payout_ranges.get(range_key, []):
                    symbol.prob *= adjustment_factor
        
        # 3. 確率を正規化（合計100%）
        total_prob = sum(s.prob for s in symbols)
        if total_prob > 0:
            for symbol in symbols:
                symbol.prob = symbol.prob / total_prob * 100.0
    
    # 最良解を返す
    if best_error < tolerance * 100:  # 許容範囲内
        return best_symbols
    else:
        # 許容範囲外でも最良解を返す（警告付き）
        return best_symbols


def calculate_expected_value(symbols: List[Symbol], miss_probability: float) -> float:
    """
    5回スピンの期待値を計算
    
    Args:
        symbols: シンボルのリスト
        miss_probability: ハズレ確率 (%)
    
    Returns:
        5回スピンの期待値
    """
    # 1回のスピンの期待値
    single_spin_expected = 0.0
    for symbol in symbols:
        # 実際の発生確率 = 抽選確率 × (100% - ハズレ確率)
        actual_prob = symbol.prob * (100.0 - miss_probability) / 100.0 / 100.0
        single_spin_expected += symbol.payout_3 * actual_prob
    
    # 5回スピンの期待値
    return single_spin_expected * 5.0
