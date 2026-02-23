# キャリブレーション曲線（信頼度曲線）を描画するモジュール
# モデルの予測確率が実際の正例率と一致しているか（キャリブレーション）を視覚化する
import matplotlib.pyplot as plt
import numpy.typing as npt
from matplotlib.figure import Figure
from sklearn.calibration import calibration_curve


# 予測確率と実際のラベルからキャリブレーション曲線を描画して Figure オブジェクトを返す関数
# 理想的なキャリブレーションでは対角線（Ideal）にモデルの曲線が重なる
def plot_calibration_curve(y_true: npt.NDArray, y_pred: npt.NDArray, n_bins: int = 50) -> Figure:
    # n_bins 個のビンに分割して各ビンの平均予測確率と実際の正例率を計算する
    prob_true, prob_pred = calibration_curve(y_true, y_pred, n_bins=n_bins)

    fig = plt.figure(figsize=(6, 6))

    # 理想キャリブレーション（完全に一致する場合の対角線）を点線で描画
    plt.plot([0, 0.5], [0, 0.5], "k:", label="Ideal")
    # モデルの実際のキャリブレーション曲線を描画
    plt.plot(prob_pred, prob_true, "s-", label="Model")

    plt.xlabel("Mean predicted probability")
    plt.ylabel("Fraction of positives")
    plt.title("Calibration Curve")
    # クリック率予測は確率が低い範囲に集中するため表示範囲を 0〜0.5 に絞る
    plt.xlim(0, 0.5)
    plt.ylim(0, 0.5)
    plt.legend(loc="best")

    plt.tight_layout()

    return fig
