# 新モデルと既存（ベースライン）モデルを比較して、モデルを更新すべきかを判定するモジュール
# LogLoss とキャリブレーションスコアの両方で改善している場合にのみ更新と判定する
import logging

import numpy.typing as npt
from sklearn.metrics import log_loss

from .metrics import calibration_score

logger = logging.getLogger(__name__)


# 新モデルがベースラインモデルより優れているかを判定する関数
# LogLoss とキャリブレーションの両方の条件を満たす場合のみ True を返す（AND 条件）
def is_model_better_than_baseline(
    y_pred: npt.NDArray,
    y_baseline: npt.NDArray,
    y_true: npt.NDArray,
) -> bool:
    return (
        _is_better_logloss(y_pred=y_pred, y_baseline=y_baseline, y_true=y_true)  # noqa
        and _is_better_calibration(y_pred=y_pred, y_baseline=y_baseline, y_true=y_true)
    )


# 新モデルの LogLoss がベースラインよりも小さい（良い）かを判定するプライベート関数
# LogLoss は小さいほど良いため、新モデル <= ベースラインの場合に True を返す
def _is_better_logloss(y_pred: npt.NDArray, y_baseline: npt.NDArray, y_true: npt.NDArray) -> bool:
    logloss = log_loss(y_true=y_true, y_pred=y_pred)
    logloss_baseline = log_loss(y_true=y_true, y_pred=y_baseline)
    logger.info(f"logloss: {logloss}, baseline: {logloss_baseline}")
    return logloss <= logloss_baseline


# 新モデルのキャリブレーションスコアがベースラインより1に近い（良い）かを判定するプライベート関数
# キャリブレーションスコアは 1.0 が理想（予測確率の総和 = 実際の正例数）なので、1との差が小さいほど良い
def _is_better_calibration(y_pred: npt.NDArray, y_baseline: npt.NDArray, y_true: npt.NDArray) -> bool:
    calibration = calibration_score(y_true=y_true, y_pred=y_pred)
    calibration_baseline = calibration_score(y_true=y_true, y_pred=y_baseline)
    logger.info(f"calibration: {calibration}, baseline: {calibration_baseline}")
    # |スコア - 1| が小さいほどキャリブレーションが良い
    return abs(calibration - 1) <= abs(calibration_baseline - 1)
