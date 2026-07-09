import cv2
import numpy as np
from collections import deque


class VideoStabilizer:
    def __init__(
        self,
        max_corners=200,
        quality_level=0.01,
        min_distance=30,
        zoom_scale=1.08,
        border_mode="zoom",
    ):
        """
        手ブレ補正クラス

        Parameters
        ----------
        max_corners : int
            検出する特徴点の最大数
        quality_level : float
            特徴点検出の品質
        min_distance : int
            特徴点同士の最小距離
        zoom_scale : float
            黒枠を隠すための拡大率
        border_mode : str
            黒枠対策
            "zoom"      : 少し拡大して黒枠を隠す
            "replicate" : 端の画素を引き伸ばす
            "black"     : 黒枠のまま
        """
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance
        self.zoom_scale = zoom_scale
        self.border_mode = border_mode

        self.prev_gray = None
        self.initialized = False

    def reset(self):
        """
        内部状態をリセットする
        """
        self.prev_gray = None
        self.initialized = False

    def initialize(self, frame):
        """
        最初のフレームで初期化する
        """
        self.prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.initialized = True

    def stabilize(self, frame):
        """
        1フレーム分の手ブレ補正を行う

        Parameters
        ----------
        frame : np.ndarray
            入力フレーム BGR画像

        Returns
        -------
        stabilized_frame : np.ndarray
            補正後フレーム
        """
        if frame is None:
            return None

        if not self.initialized:
            self.initialize(frame)
            return frame.copy()

        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        prev_pts = cv2.goodFeaturesToTrack(
            self.prev_gray,
            maxCorners=self.max_corners,
            qualityLevel=self.quality_level,
            minDistance=self.min_distance
        )

        stabilized_frame = frame.copy()

        if prev_pts is not None:
            curr_pts, status, err = cv2.calcOpticalFlowPyrLK(
                self.prev_gray,
                curr_gray,
                prev_pts,
                None
            )

            if curr_pts is not None and status is not None:
                valid_prev = prev_pts[status.flatten() == 1]
                valid_curr = curr_pts[status.flatten() == 1]

                if len(valid_prev) > 4:
                    transform_matrix, _ = cv2.estimateAffinePartial2D(
                        valid_prev,
                        valid_curr
                    )

                    if transform_matrix is not None:
                        stabilized_frame = self._apply_inverse_transform(
                            frame,
                            transform_matrix
                        )

        self.prev_gray = curr_gray.copy()

        return stabilized_frame

    def _apply_inverse_transform(self, frame, transform_matrix):
        """
        推定された動きを打ち消す変換を適用する
        """
        dx = -transform_matrix[0, 2]
        dy = -transform_matrix[1, 2]
        da = -np.arctan2(transform_matrix[1, 0], transform_matrix[0, 0])

        correction_matrix = np.zeros_like(transform_matrix)

        correction_matrix[0, 0] = np.cos(da)
        correction_matrix[0, 1] = -np.sin(da)
        correction_matrix[1, 0] = np.sin(da)
        correction_matrix[1, 1] = np.cos(da)
        correction_matrix[0, 2] = dx
        correction_matrix[1, 2] = dy

        h, w = frame.shape[:2]

        if self.border_mode == "replicate":
            stabilized = cv2.warpAffine(
                frame,
                correction_matrix,
                (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE
            )

        else:
            stabilized = cv2.warpAffine(
                frame,
                correction_matrix,
                (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )

        if self.border_mode == "zoom":
            stabilized = self._fix_border_by_zoom(stabilized)

        return stabilized

    def _fix_border_by_zoom(self, frame):
        """
        黒枠を隠すため、中心基準で少し拡大する
        """
        h, w = frame.shape[:2]

        zoom_matrix = cv2.getRotationMatrix2D(
            (w / 2, h / 2),
            0,
            self.zoom_scale
        )

        fixed = cv2.warpAffine(
            frame,
            zoom_matrix,
            (w, h),
            flags=cv2.INTER_LINEAR
        )

        return fixed
    













class SmoothVideoStabilizer:
    def __init__(
        self,
        buffer_size=21,
        smoothing_window=None,
        max_corners=200,
        quality_level=0.01,
        min_distance=30,
        zoom_scale=1.10,
        border_mode="zoom",
        smoothing_type="gaussian",
        output_position="center",
    ):
        """
        Webカメラ/画像列向けの滑らか手ブレ補正クラス

        Parameters
        ----------
        buffer_size : int
            内部に保持するフレーム数。
            大きいほど滑らかになるが、遅延も増える。

        smoothing_window : int or None
            平滑化に使うフレーム数。
            Noneならbuffer_sizeと同じ。

        output_position : str
            "center" : バッファ中央のフレームを出力。滑らかだが遅延あり。
            "latest" : 最新寄りのフレームを出力。遅延少なめだが滑らかさは少し落ちる。
        """
        self.buffer_size = buffer_size
        self.smoothing_window = smoothing_window or buffer_size

        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance

        self.zoom_scale = zoom_scale
        self.border_mode = border_mode
        self.smoothing_type = smoothing_type
        self.output_position = output_position

        self.frame_buffer = deque(maxlen=buffer_size)

    def update(self, frame):
        """
        Webカメラなどから1フレームずつ渡して使う。

        Parameters
        ----------
        frame : np.ndarray
            入力フレーム

        Returns
        -------
        output_frame : np.ndarray
            補正後フレーム。
            バッファが溜まるまでは元フレームを返す。
        """
        if frame is None:
            return None

        self.frame_buffer.append(frame.copy())

        # バッファが溜まるまでは元の映像を返す
        if len(self.frame_buffer) < self.buffer_size:
            return frame.copy()

        frames = list(self.frame_buffer)
        stabilized_frames = self.stabilize_frames(frames)

        if self.output_position == "latest":
            output_index = len(stabilized_frames) - 1
        else:
            output_index = len(stabilized_frames) // 2

        return stabilized_frames[output_index]

    def reset(self):
        """
        内部バッファをリセットする
        """
        self.frame_buffer.clear()

    def stabilize_frames(self, frames):
        """
        複数フレームをまとめて滑らかに補正する
        """
        if frames is None or len(frames) <= 1:
            return frames

        transforms = self._estimate_transforms(frames)

        trajectory = np.cumsum(transforms, axis=0)

        smoothed_trajectory = self._smooth_trajectory(trajectory)

        difference = smoothed_trajectory - trajectory
        corrected_transforms = transforms + difference

        stabilized_frames = [frames[0].copy()]

        for i in range(1, len(frames)):
            dx, dy, da = corrected_transforms[i - 1]
            stabilized = self._apply_transform(frames[i], dx, dy, da)
            stabilized_frames.append(stabilized)

        return stabilized_frames

    def _to_gray(self, frame):
        """
        BGR / BGRA / グレースケールを安全にグレースケールへ変換
        """
        if frame is None:
            return None

        if len(frame.shape) == 2:
            return frame.copy()

        if len(frame.shape) == 3:
            channels = frame.shape[2]

            if channels == 1:
                return frame[:, :, 0].copy()

            if channels == 3:
                return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if channels == 4:
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

        raise ValueError(f"対応していない画像形式です: shape={frame.shape}")

    def _estimate_transforms(self, frames):
        """
        各フレーム間の移動量 dx, dy と回転 da を推定する
        """
        transforms = []

        prev_gray = self._to_gray(frames[0])

        for i in range(1, len(frames)):
            curr_gray = self._to_gray(frames[i])

            dx, dy, da = 0.0, 0.0, 0.0

            prev_pts = cv2.goodFeaturesToTrack(
                prev_gray,
                maxCorners=self.max_corners,
                qualityLevel=self.quality_level,
                minDistance=self.min_distance
            )

            if prev_pts is not None:
                curr_pts, status, err = cv2.calcOpticalFlowPyrLK(
                    prev_gray,
                    curr_gray,
                    prev_pts,
                    None
                )

                if curr_pts is not None and status is not None:
                    valid_prev = prev_pts[status.flatten() == 1]
                    valid_curr = curr_pts[status.flatten() == 1]

                    if len(valid_prev) > 4:
                        matrix, _ = cv2.estimateAffinePartial2D(
                            valid_prev,
                            valid_curr
                        )

                        if matrix is not None:
                            dx = matrix[0, 2]
                            dy = matrix[1, 2]
                            da = np.arctan2(matrix[1, 0], matrix[0, 0])

            transforms.append([dx, dy, da])
            prev_gray = curr_gray.copy()

        return np.array(transforms, dtype=np.float32)

    def _smooth_trajectory(self, trajectory):
        """
        カメラ軌跡を平滑化する
        """
        if self.smoothing_window <= 1:
            return trajectory.copy()

        if self.smoothing_type == "gaussian":
            return self._gaussian_smooth(trajectory, self.smoothing_window)

        return self._moving_average_smooth(trajectory, self.smoothing_window)

    def _moving_average_smooth(self, trajectory, window):
        """
        移動平均による平滑化
        """
        smoothed = np.zeros_like(trajectory)
        radius = window // 2

        for i in range(len(trajectory)):
            start = max(0, i - radius)
            end = min(len(trajectory), i + radius + 1)
            smoothed[i] = np.mean(trajectory[start:end], axis=0)

        return smoothed

    def _gaussian_smooth(self, trajectory, window):
        """
        ガウシアン平滑化
        """
        smoothed = np.zeros_like(trajectory)

        radius = window // 2
        sigma = max(window / 6.0, 1.0)

        x = np.arange(-radius, radius + 1)
        weights = np.exp(-(x ** 2) / (2 * sigma ** 2))
        weights = weights / np.sum(weights)

        for i in range(len(trajectory)):
            weighted_sum = np.zeros(3, dtype=np.float32)
            weight_sum = 0.0

            for j, weight in enumerate(weights):
                index = i + j - radius

                if 0 <= index < len(trajectory):
                    weighted_sum += trajectory[index] * weight
                    weight_sum += weight

            smoothed[i] = weighted_sum / weight_sum

        return smoothed

    def _apply_transform(self, frame, dx, dy, da):
        """
        補正変換をフレームへ適用
        """
        h, w = frame.shape[:2]

        matrix = np.array([
            [np.cos(da), -np.sin(da), dx],
            [np.sin(da),  np.cos(da), dy]
        ], dtype=np.float32)

        if self.border_mode == "replicate":
            stabilized = cv2.warpAffine(
                frame,
                matrix,
                (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE
            )
        else:
            border_value = 0 if len(frame.shape) == 2 else (0, 0, 0)

            stabilized = cv2.warpAffine(
                frame,
                matrix,
                (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=border_value
            )

        if self.border_mode == "zoom":
            stabilized = self._fix_border_by_zoom(stabilized)

        return stabilized

    def _fix_border_by_zoom(self, frame):
        """
        黒枠を隠すために中心基準で拡大
        """
        h, w = frame.shape[:2]

        zoom_matrix = cv2.getRotationMatrix2D(
            (w / 2, h / 2),
            0,
            self.zoom_scale
        )

        fixed = cv2.warpAffine(
            frame,
            zoom_matrix,
            (w, h),
            flags=cv2.INTER_LINEAR
        )

        return fixed