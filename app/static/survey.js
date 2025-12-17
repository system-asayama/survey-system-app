/* アンケートページのJavaScript */

document.addEventListener('DOMContentLoaded', () => {
  // 星評価の処理（複数の星評価に対応）
  const starRatings = document.querySelectorAll('.star-rating');
  
  starRatings.forEach(ratingContainer => {
    const stars = ratingContainer.querySelectorAll('.star');
    const questionId = ratingContainer.dataset.questionId;
    const hiddenInput = document.querySelector(`input[name="q${questionId}"]`);
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
        if (hiddenInput) {
          hiddenInput.value = selectedRating;
        }
        
        stars.forEach((s, i) => {
          if (i < selectedRating) {
            s.classList.add('active');
          } else {
            s.classList.remove('active');
          }
        });

        // エラーメッセージをクリア
        const errorMsg = document.getElementById(`q${questionId}-error`);
        if (errorMsg) {
          errorMsg.textContent = '';
        }
      });
    });
  });

  // フォーム送信処理
  const form = document.getElementById('survey-form');
  const submitBtn = document.getElementById('submit-btn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // バリデーション
    let isValid = true;
    const formData = new FormData(form);
    const surveyData = {};

    // すべての必須フィールドをチェック
    const requiredInputs = form.querySelectorAll('[required]');
    requiredInputs.forEach(input => {
      const name = input.name;
      const errorElement = document.getElementById(`${name}-error`);
      
      if (input.type === 'radio') {
        const checked = form.querySelector(`input[name="${name}"]:checked`);
        if (!checked) {
          if (errorElement) {
            errorElement.textContent = 'この項目は必須です';
          }
          isValid = false;
        } else {
          if (errorElement) {
            errorElement.textContent = '';
          }
        }
      } else if (input.type === 'hidden') {
        // 星評価の場合
        if (!input.value) {
          if (errorElement) {
            errorElement.textContent = 'この項目は必須です';
          }
          isValid = false;
        } else {
          if (errorElement) {
            errorElement.textContent = '';
          }
        }
      } else if (input.tagName === 'TEXTAREA') {
        if (!input.value.trim()) {
          if (errorElement) {
            errorElement.textContent = 'この項目は必須です';
          }
          isValid = false;
        } else {
          if (errorElement) {
            errorElement.textContent = '';
          }
        }
      }
    });

    if (!isValid) {
      return;
    }

    // フォームデータの収集
    for (let [key, value] of formData.entries()) {
      if (surveyData[key]) {
        // 既に存在する場合は配列にする（チェックボックス対応）
        if (!Array.isArray(surveyData[key])) {
          surveyData[key] = [surveyData[key]];
        }
        surveyData[key].push(value);
      } else {
        surveyData[key] = value;
      }
    }

    // チェックボックスの値を配列として収集
    const checkboxGroups = {};
    form.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
      const name = cb.name;
      if (!checkboxGroups[name]) {
        checkboxGroups[name] = [];
      }
      checkboxGroups[name].push(cb.value);
    });
    
    // チェックボックスの値を上書き
    Object.keys(checkboxGroups).forEach(key => {
      surveyData[key] = checkboxGroups[key];
    });

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
        console.log('DEBUG: Server response:', result);
        // メッセージを表示
        alert(result.message);
        
        // 口コミ投稿文がある場合は追加で表示
        if (result.generated_review) {
          alert('以下の口コミ投稿文を生成しました：\n\n' + result.generated_review);
        }
        
        // リダイレクトURLがある場合は遷移
        if (result.redirect_url) {
          console.log('DEBUG: Redirecting to:', result.redirect_url);
          window.location.href = result.redirect_url;
        } else {
          // フォームをリセット
          form.reset();
          submitBtn.disabled = false;
          submitBtn.textContent = 'アンケートを送信してスロットへ';
        }
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
