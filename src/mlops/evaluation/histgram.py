# 予測値の分布ヒストグラムを描画するモジュール
# クリック（正例）と非クリック（負例）ごとに予測確率の分布を可視化し、識別能力を確認する
import matplotlib.pyplot as plt
import numpy.typing as npt
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure


# 正例・負例それぞれの予測値分布をヒストグラムで描画して Figure オブジェクトを返す関数
# 正例の予測値が高い範囲に分布し、負例が低い範囲に分布していれば識別能力が高い
def plot_histgram(y_true: npt.NDArray, y_pred: npt.NDArray) -> Figure:
    fig = plt.figure(figsize=(10, 6))
    # y_pred と y_true を1つの DataFrame にまとめて seaborn に渡す
    df_hist = pd.DataFrame({"y_pred": y_pred, "y_true": y_true})
    # hue="y_true" により正例（1）と負例（0）を色分けしてヒストグラムを重ね描きする
    sns.histplot(data=df_hist, x="y_pred", hue="y_true", bins=100)
    plt.title("Distribution of prediction value")

    return fig
