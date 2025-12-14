/* アンケートページのJavaScript */

document.addEventListener('DOMContentLoaded', () => {
  // 星評価の処理
  const stars = document.querySelectorAll('.star');
  const ratingInput = document.getElementById('rating');
  let selectedRating = 0;

  stars.forEach((star, index) => {
    // マウスホバー時
    star.addEventListener('mouseenter', () => {
      stars.forEach((s, i) => {
        if (i <= index) {
          s.classList.add('hover');
        } else {
          s.classList.remove('hover');
        }
      });
    });

    // マウスが離れた時
    star.addEventListener('mouseleave', () => {
      stars.forEach(s => s.classList.remove('hover'));
    });

    // クリック時
    star.addEventListener('click', () => {
      selectedRating = parseInt(star.dataset.value);
      ratingInput.value = selectedRating;
      
      stars.forEach((s, i) => {
        if (i < selectedRating) {
          s.classList.add('active');
        } else {
          s.classList.remove('active');
        }
      });

      // エラーメッセージをクリア
      document.getElementById('rating-error').textContent = '';
    });
  });

  // フォーム送信処理
  const form = document.getElementById('survey-form');
  const submitBtn = document.getElementById('submit-btn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // バリデーション
    let isValid = true;

    // 星評価のチェック
    if (!ratingInput.value) {
      document.getElementById('rating-error').textContent = '総合評価を選択してください';
      isValid = false;
    } else {
      document.getElementById('rating-error').textContent = '';
    }

    // 訪問目的のチェック
    const visitPurpose = document.querySelector('input[name="visit_purpose"]:checked');
    if (!visitPurpose) {
      document.getElementById('visit_purpose-error').textContent = '訪問目的を選択してください';
      isValid = false;
    } else {
      document.getElementById('visit_purpose-error').textContent = '';
    }

    // 雰囲気のチェック（少なくとも1つ選択）
    const atmosphereChecked = document.querySelectorAll('input[name="atmosphere"]:checked');
    if (atmosphereChecked.length === 0) {
      document.getElementById('atmosphere-error').textContent = 'お店の雰囲気を少なくとも1つ選択してください';
      isValid = false;
    } else {
      document.getElementById('atmosphere-error').textContent = '';
    }

    // おすすめ度のチェック
    const recommend = document.querySelector('input[name="recommend"]:checked');
    if (!recommend) {
      document.getElementById('recommend-error').textContent = 'おすすめ度を選択してください';
      isValid = false;
    } else {
      document.getElementById('recommend-error').textContent = '';
    }

    if (!isValid) {
      return;
    }

    // フォームデータの収集
    const atmosphereValues = Array.from(atmosphereChecked).map(cb => cb.value);
    
    const surveyData = {
      rating: parseInt(ratingInput.value),
      visit_purpose: visitPurpose.value,
      atmosphere: atmosphereValues,
      recommend: recommend.value,
      comment: document.getElementById('comment').value.trim()
    };

    // 送信ボタンを無効化
    submitBtn.disabled = true;
    submitBtn.textContent = '送信中...';

    try {
      const response = await fetch(window.location.pathname.replace('/survey', '/submit_survey'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(surveyData)
      });

      const result = await response.json();

      if (result.ok) {
        // 星3以下の場合はメッセージを表示してからリダイレクト
        if (result.rating <= 3) {
          alert(result.message);
        }
        // 成功したら指定されたページへリダイレクト
        window.location.href = result.redirect_url || '/slot';
      } else {
        alert('エラーが発生しました: ' + (result.error || '不明なエラー'));
        submitBtn.disabled = false;
        submitBtn.textContent = 'アンケートを送信してスロットへ';
      }
    } catch (error) {
      alert('送信エラー: ' + error.message);
      submitBtn.disabled = false;
      submitBtn.textContent = 'アンケートを送信してスロットへ';
    }
  });
});
