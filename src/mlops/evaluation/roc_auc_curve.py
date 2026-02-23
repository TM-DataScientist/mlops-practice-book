# ROC-AUC 曲線を描画するモジュール
# 偽陽性率（FPR）と真陽性率（TPR）のトレードオフを可視化し、モデルの識別能力を評価する
import matplotlib.pyplot as plt
import numpy.typing as npt
from matplotlib.figure import Figure
from sklearn.metrics import roc_curve


# ROC 曲線を描画して Figure オブジェクトを返す関数
# ランダム予測（対角線）との比較により、モデルがどれだけ識別能力を持つかを確認する
def plot_roc_auc_curve(y_true: npt.NDArray, y_pred: npt.NDArray) -> Figure:
    # ROC 曲線の各閾値における FPR（偽陽性率）と TPR（真陽性率）を計算する
    [fpr, tpr, _] = roc_curve(y_true, y_pred)

    fig = plt.figure(figsize=(6, 6))
    # モデルの ROC 曲線を描画（左上に近いほど良いモデル）
    plt.plot(fpr, tpr, label="Model")
    # ランダム予測のベースライン（対角線）を破線で描画
    plt.plot([0, 1], [0, 1], "k--", label="Random")
    plt.xlabel("False Positive Rate (specificity)")
    plt.ylabel("True Positive Rate (recall)")
    plt.title("ROC Curve")
    plt.legend()

    return fig
