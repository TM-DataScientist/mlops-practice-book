# モデル評価指標の計算モジュール
# LogLoss・AUC・キャリブレーションスコアの3指標を計算して返す
import logging

import numpy.typing as npt
from sklearn.metrics import log_loss, roc_auc_score

logger = logging.getLogger(__name__)


# 3種類の評価指標（LogLoss・ROC-AUC・キャリブレーション）を計算して辞書形式で返す関数
def calculate_metrics(y_true: npt.NDArray, y_pred: npt.NDArray) -> dict[str, float]:
    logloss = log_loss(y_true=y_true, y_pred=y_pred)  # 予測確率の対数損失（小さいほど良い）
    roc_auc = roc_auc_score(y_true=y_true, y_score=y_pred)  # ROC 曲線下面積（大きいほど良い、最大1.0）
    calibration = calibration_score(y_true=y_true, y_pred=y_pred)  # キャリブレーションスコア（1.0 が理想）
    logger.info(f"logloss: {logloss}, AUC: {roc_auc}, calibration: {calibration}")
    return {
        "logloss": logloss,
        "AUC": roc_auc,
        "calibration": calibration,
    }


# キャリブレーションスコアを計算する関数
# 予測確率の総和を実際の正例数で割った値で、1.0 に近いほど予測確率の総量が実態に近い
# > 1.0: 予測確率が過大（過信）、< 1.0: 予測確率が過小（過小評価）
def calibration_score(y_true: npt.NDArray, y_pred: npt.NDArray) -> float:
    return sum(y_pred) / sum(y_true)
