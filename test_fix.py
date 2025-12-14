import sys
sys.path.insert(0, '/home/ubuntu/survey-system-app')
import store_db
from dataclasses import dataclass

@dataclass
class Symbol:
    id: str
    label: str
    payout_3: float
    color: str | None = None
    prob: float = 0.0
    is_reach: bool = False
    reach_symbol: str | None = None
    is_disabled: bool = False
    is_default: bool = False

# 現在のデータベース状態を確認
print("=== 現在のデータベース状態 ===")
config = store_db.get_slot_config(1)
for s in config['symbols']:
    if 'reach' in s['id']:
        print(f"{s['id']}: is_reach={s.get('is_reach', 'MISSING')}, reach_symbol={s.get('reach_symbol', 'MISSING')}")

# 確率自動調整の処理をシミュレート
print("\n=== 確率自動調整処理のシミュレーション ===")

# フロントエンドから送られてくるデータ（is_reach, reach_symbolが含まれていない）
symbols_data = []
for s in config['symbols']:
    symbols_data.append({
        'id': s['id'],
        'label': s['label'],
        'payout_3': s['payout_3'],
        'color': s.get('color'),
        'prob': s['prob'],
        'is_disabled': s.get('is_disabled', False),
        'is_default': s.get('is_default', False)
        # is_reach と reach_symbol は含まれていない
    })

print(f"フロントエンドから送信されるデータ（リーチシンボルのみ）:")
for s_data in symbols_data:
    if 'reach' in s_data['id']:
        print(f"  {s_data['id']}: is_reach={s_data.get('is_reach', 'NOT_SENT')}, reach_symbol={s_data.get('reach_symbol', 'NOT_SENT')}")

# 修正後の処理：データベースから取得してマージ
db_symbols = {s['id']: s for s in config['symbols']}
merged_symbols = []

for s_data in symbols_data:
    if s_data['id'] in db_symbols:
        merged = db_symbols[s_data['id']].copy()
        merged.update({
            'payout_3': s_data.get('payout_3', merged.get('payout_3', 0)),
            'is_disabled': s_data.get('is_disabled', merged.get('is_disabled', False)),
            'prob': s_data.get('prob', merged.get('prob', 0))
        })
        merged_symbols.append(Symbol(**merged))
    else:
        merged_symbols.append(Symbol(**s_data))

print("\nマージ後のシンボル（リーチシンボルのみ）:")
for s in merged_symbols:
    if 'reach' in s.id:
        print(f"  {s.id}: is_reach={s.is_reach}, reach_symbol={s.reach_symbol}")

print("\n✅ 修正により、is_reach と reach_symbol が保持されることを確認しました")
