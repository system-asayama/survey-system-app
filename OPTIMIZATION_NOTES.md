# アンケート機能最適化ノート

## 修正日時
2025年12月9日

## 修正内容

### 問題点
当初の実装では、すべての星評価（1-5）に対してAI投稿文を生成していました。しかし、星3以下の低評価の場合はGoogle口コミへの投稿を行わないため、AI投稿文の生成が不要でした。

### 修正内容
星評価による条件分岐を追加し、以下のように動作を最適化しました：

#### 星4以上の場合
1. アンケート回答を受信
2. **OpenAI APIでAI投稿文を生成**
3. 口コミ確認ページへ遷移
4. Google口コミ投稿ボタンを表示
5. スロットページへ遷移

#### 星3以下の場合
1. アンケート回答を受信
2. **AI投稿文生成をスキップ**
3. 内部保存のみ実行
4. **直接スロットページへ遷移**（口コミ確認ページをスキップ）
5. 感謝メッセージをアラート表示

## 修正したファイル

### 1. `app.py`
```python
# 修正前
generated_review = _generate_review_text(body)

# 修正後
rating = body.get('rating', 3)

# 星4以上の場合のみAI投稿文を生成
if rating >= 4:
    generated_review = _generate_review_text(body)
    body['generated_review'] = generated_review
else:
    # 星3以下の場合はAI生成をスキップ
    generated_review = ''
    body['generated_review'] = ''

# 星3以下の場合は直接スロットページへ
if rating <= 3:
    return jsonify({
        "ok": True, 
        "message": "貴重なご意見をありがとうございます。社内で改善に活用させていただきます。",
        "rating": rating,
        "redirect_url": url_for('slot_page')
    })

# 星4以上の場合は口コミ確認ページへ
return jsonify({
    "ok": True, 
    "message": "アンケートを受け付けました",
    "rating": rating,
    "generated_review": generated_review,
    "redirect_url": url_for('review_confirm')
})
```

### 2. `static/survey.js`
```javascript
// 修正前
if (result.ok) {
    window.location.href = result.redirect_url || '/review_confirm';
}

// 修正後
if (result.ok) {
    // 星3以下の場合はメッセージを表示してからリダイレクト
    if (result.rating <= 3) {
        alert(result.message);
    }
    // 成功したら指定されたページへリダイレクト
    window.location.href = result.redirect_url || '/slot';
}
```

## 最適化の効果

### 1. APIコスト削減
- **削減率**: 低評価の割合に応じて変動
- **例**: 低評価が30%の場合、OpenAI APIコールが30%削減
- **年間コスト削減**: アンケート回答数とAPI料金に依存

### 2. 処理速度向上
- **AI生成時間**: 約2-5秒（スキップ）
- **ページ遷移削減**: 口コミ確認ページをスキップ
- **体感速度**: 低評価時は即座にスロットへアクセス可能

### 3. ユーザー体験の向上
- **不要な画面遷移の削減**: 低評価時は口コミ確認ページを表示しない
- **明確なフィードバック**: 感謝メッセージで内部保存を明示
- **スムーズな導線**: アンケート → スロット（1ステップ削減）

### 4. データ品質の向上
- **意図の明確化**: 高評価のみAI投稿文を生成
- **内部フィードバックの純粋性**: 低評価は加工せず保存

## テスト結果

### 低評価テスト（星2つ）
- ✅ アンケート送信成功
- ✅ AI生成スキップ確認
- ✅ 直接スロットページへ遷移
- ✅ 感謝メッセージ表示
- ✅ データ保存確認

### 高評価テスト（星5つ）
- ✅ アンケート送信成功
- ✅ AI投稿文生成成功
- ✅ 口コミ確認ページ表示
- ✅ Google投稿ボタン表示
- ✅ スロットページへ遷移

## 今後の改善案

1. **段階的なフィードバック収集**
   - 星3の場合は「どちらでもない」として別途分析

2. **A/Bテスト**
   - 低評価時のメッセージ内容による改善率の測定

3. **リアルタイムアラート**
   - 星1-2の場合は管理者へ即座に通知

4. **詳細分析ダッシュボード**
   - 星評価の分布、訪問目的との相関分析

## 関連コミット

- 初回実装: `18c5ad4` - Add survey feature with AI-generated reviews and Google Maps integration
- 最適化: `cde333c` - Optimize: Skip AI review generation for ratings 3 or below

## 参考資料

- OpenAI API料金: https://openai.com/pricing
- Google Maps Place API: https://developers.google.com/maps/documentation/places/web-service/place-id
