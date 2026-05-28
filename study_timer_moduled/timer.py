# 匯入時間模組
from datetime import datetime


# ════════════════════════════════════════════════
# 系統常數設定
# ════════════════════════════════════════════════

DAILY_EXP_CAP = 200              # 每日 EXP 上限
EXP_BONUS_THRESHOLD = 120        # 每日累積讀書超過 120 分鐘後，EXP 變 1.2 倍
AFF_MAX = 100                    # 好感度增加上限


class StudySession:
    """
    StudySession 用來管理一次完整的讀書 session。

    功能包含：
    1. 番茄鐘模式 / 自訂時間模式
    2. 開始、暫停、繼續、中止、結束
    3. 記錄開始時間、結束時間、預定時長、實際讀書時間
    4. 記錄干擾原因、干擾次數、干擾總時間
    5. 判斷是否完成目標
    6. 判斷是否低專注
    7. 產生讀書結束提醒、休息提醒、久未讀書提醒
    8. 計算 EXP 與好感度
    """

    def __init__(
        self,
        tag,
        target_minutes=25,
        mode="custom",
        daily_exp_so_far=0,
        break_minutes=5,
        low_focus_threshold=60,
        distraction_warning_minutes=10,
        idle_warning_minutes=1440
    ):
        """
        初始化一次讀書 session。

        Parameters
        ----------
        tag : str
            讀書標籤，例如「英文」、「會計」、「微積分」。

        target_minutes : int or float
            預定讀書分鐘數。

        mode : str
            計時模式：
            "pomodoro" = 番茄鐘模式
            "custom" = 自訂時間模式

        daily_exp_so_far : float
            今日已累積 EXP。

        break_minutes : int or float
            完成讀書後建議休息分鐘數。

        low_focus_threshold : int
            低專注門檻。
            focus_score 低於此數值時，會被判定為低專注。

        distraction_warning_minutes : int or float
            干擾提醒門檻。
            干擾總分鐘數達到此數值時，會觸發警告。

        idle_warning_minutes : int or float
            久未讀書提醒門檻。
            預設 1440 分鐘，也就是 24 小時。
        """

        # 檢查目標時間是否合法
        if target_minutes <= 0:
            raise ValueError("target_minutes 必須大於 0")

        # 檢查模式是否合法
        if mode not in ["pomodoro", "custom"]:
            raise ValueError("mode 只能是 'pomodoro' 或 'custom'")

        # 讀書標籤
        self.tag = tag

        # 計時模式
        self.mode = mode

        # 預定讀書分鐘數
        self.target_minutes = target_minutes

        # 預定讀書秒數
        self.target_seconds = target_minutes * 60

        # 今日已累積 EXP
        self.daily_exp_so_far = daily_exp_so_far

        # 建議休息分鐘數
        self.break_minutes = break_minutes

        # 低專注判斷門檻
        self.low_focus_threshold = low_focus_threshold

        # 干擾警告門檻
        self.distraction_warning_minutes = distraction_warning_minutes

        # 久未讀書提醒門檻
        self.idle_warning_minutes = idle_warning_minutes

        # session 開始時間
        self.start_time = None

        # session 結束時間
        self.end_time = None

        # 暫停開始時間
        self.pause_start = None

        # 暫停原因
        self.pause_reason = None

        # 是否為干擾性暫停
        self.pause_is_distraction = False

        # 干擾專用暫停計時（只計算是干擾的那段時間）
        self.distraction_pause_seconds = 0

        # 累積暫停秒數
        self.total_pause_seconds = 0

        # 實際有效讀書秒數
        self.elapsed_seconds = 0

        # 是否正在計時
        self.is_running = False

        # 是否已結束
        self.is_finished = False

        # 是否中止
        self.is_aborted = False

        # 干擾紀錄清單
        self.distractions = []

        # 提醒訊息清單
        self.reminders = []

    # ════════════════════════════════════════════
    # 開始讀書
    # ════════════════════════════════════════════

    def start(self):
        """
        開始讀書計時。
        """

        # 如果已經在計時，就不要重複開始
        if self.is_running:
            print("計時已經在進行中")
            return

        # 如果 session 已經結束，就不能重新開始
        if self.is_finished:
            print("此 session 已經結束，不能重新開始")
            return

        # 第一次開始時計錄開始時間
        if self.start_time is None:
            self.start_time = datetime.now()

        # 更新狀態為正在計時
        self.is_running = True

        print(f"開始讀書：{self.tag}")
        print(f"模式：{self.mode}")
        print(f"目標時間：{self.target_minutes} 分鐘")

    # ════════════════════════════════════════════
    # 暫停讀書
    # ════════════════════════════════════════════

    def pause(self, reason="未填寫", is_distraction=True):
        """
        暫停讀書。

        Parameters
        ----------
        reason : str
            暫停原因，例如「重要訊息」、「吃飯」、「其他」。
            若使用者選擇「讀完了 / 告一段落」，則 is_distraction=False。

        is_distraction : bool
            是否為干擾性暫停。
            True  = 受到干擾，後台繼續計算干擾持續時間
            False = 正常暫停，不計入干擾時間
        """

        # 如果目前沒有在計時，就不能暫停
        if not self.is_running:
            print("目前沒有正在計時")
            return

        # 記錄暫停開始時間
        self.pause_start = datetime.now()

        # 記錄暫停原因
        self.pause_reason = reason

        # 記錄是否為干擾性暫停
        self.pause_is_distraction = is_distraction

        # 更新狀態為沒有正在計時
        self.is_running = False

        print(f"暫停讀書，原因：{reason}，干擾：{is_distraction}")

    # ════════════════════════════════════════════
    # 繼續讀書
    # ════════════════════════════════════════════

    def resume(self):
        """
        從暫停狀態繼續讀書。

        resume 時會自動：
        1. 計算剛剛暫停多久
        2. 把暫停時間加入總暫停時間
        3. 把本次暫停記錄成一筆干擾資料
        """

        # 如果沒有暫停紀錄，就不能繼續
        if self.pause_start is None:
            print("目前沒有暫停紀錄")
            return

        # 記錄暫停結束時間
        pause_end = datetime.now()

        # 計算本次暫停時長
        pause_duration = pause_end - self.pause_start

        # 轉換為秒數
        pause_seconds = pause_duration.total_seconds()

        # 轉換為分鐘數
        pause_minutes = round(pause_seconds / 60, 2)

        # 累加到總暫停時間
        self.total_pause_seconds += pause_seconds

        # 將本次暫停加入干擾紀錄（含 is_distraction 旗標）
        self.distractions.append({
            "reason": self.pause_reason,
            "is_distraction": self.pause_is_distraction,
            "minutes": pause_minutes,
            "time": self.pause_start.strftime("%Y-%m-%d %H:%M:%S")
        })

        # 若是干擾性暫停，累計干擾秒數
        if self.pause_is_distraction:
            self.distraction_pause_seconds += pause_seconds

        # 清空暫停資料
        self.pause_start = None
        self.pause_reason = None
        self.pause_is_distraction = False

        # 更新狀態為正在計時
        self.is_running = True

        print(f"繼續讀書，本次暫停 {pause_minutes} 分鐘")

    # ════════════════════════════════════════════
    # 手動新增干擾紀錄
    # ════════════════════════════════════════════

    def add_distraction(self, reason, minutes):
        """
        手動新增干擾紀錄。

        Parameters
        ----------
        reason : str
            干擾原因。

        minutes : int or float
            干擾分鐘數。
        """

        # 干擾時間不能小於 0
        if minutes < 0:
            raise ValueError("干擾分鐘數不可小於 0")

        # 加入干擾紀錄
        self.distractions.append({
            "reason": reason,
            "minutes": minutes,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        print(f"已記錄干擾：{reason}，{minutes} 分鐘")

    # ════════════════════════════════════════════
    # 檢查讀書時間是否已達目標
    # ════════════════════════════════════════════

    def check_study_time_up(self):
        """
        檢查目前有效讀書時間是否已經達到目標時間。

        Returns
        -------
        bool
            True：已達目標時間
            False：尚未達目標時間
        """

        # 尚未開始就不需要檢查
        if self.start_time is None:
            return False

        # 已結束就不再檢查
        if self.is_finished:
            return False

        now = datetime.now()

        # 如果目前正在暫停，
        # 需要先計算目前這段暫停已經過多久
        current_pause_seconds = 0

        if self.pause_start is not None:
            current_pause_seconds = (
                now - self.pause_start
            ).total_seconds()

        # 從開始到現在的總經過時間
        total_passed_seconds = (
            now - self.start_time
        ).total_seconds()

        # 有效讀書時間
        # = 總經過時間 - 已累積暫停時間 - 目前正在暫停的時間
        current_effective_seconds = (
            total_passed_seconds
            - self.total_pause_seconds
            - current_pause_seconds
        )

        # 判斷是否達成目標時間
        return current_effective_seconds >= self.target_seconds

    # ════════════════════════════════════════════
    # 讀書結束提醒
    # ════════════════════════════════════════════

    def get_study_end_reminder(self):
        """
        若讀書時間已達成目標，產生讀書結束提醒。
        """

        # 檢查是否達成目標時間
        if self.check_study_time_up():

            message = "讀書時間已達成，可以結束本次讀書或進入休息。"

            # 加入提醒清單
            self.reminders.append(message)

            return message

        return None

    # ════════════════════════════════════════════
    # 休息提醒
    # ════════════════════════════════════════════

    def get_break_reminder(self):
        """
        產生休息提醒。
        通常在完成讀書 session 後呼叫。
        """

        message = f"建議休息 {self.break_minutes} 分鐘，讓大腦恢復一下。"

        # 加入提醒清單
        self.reminders.append(message)

        return message

    # ════════════════════════════════════════════
    # 久未讀書提醒
    # ════════════════════════════════════════════

    def check_idle_reminder(self, last_study_time):
        """
        檢查是否長時間未讀書。

        Parameters
        ----------
        last_study_time : datetime or None
            上一次讀書結束時間。

        Returns
        -------
        str or None
            若需要提醒，回傳提醒文字。
            若不需要提醒，回傳 None。
        """

        # 如果完全沒有讀書紀錄
        if last_study_time is None:
            message = "今天還沒有讀書紀錄，可以先從一小段時間開始。"
            self.reminders.append(message)
            return message

        now = datetime.now()

        # 計算距離上次讀書已經過了幾分鐘
        idle_minutes = (
            now - last_study_time
        ).total_seconds() / 60

        # 如果超過久未讀書門檻，就提醒
        if idle_minutes >= self.idle_warning_minutes:
            message = "已經有一段時間沒有讀書了，要不要開一個新的 session？"
            self.reminders.append(message)
            return message

        return None

    # ════════════════════════════════════════════
    # 中止 session
    # ════════════════════════════════════════════

    def abort(self):
        """
        中止讀書 session。

        abort 與 finish 類似，都會結束 session。
        差別是 abort 會把 is_aborted 標記為 True，
        表示這次不是正常完成，而是中途放棄。
        """

        self.is_aborted = True

        return self.finish()

    # ════════════════════════════════════════════
    # 結束 session
    # ════════════════════════════════════════════

    def finish(self):
        """
        結束讀書 session，並回傳完整結果資料。
        """

        # 如果尚未開始，就不能結束
        if self.start_time is None:
            print("尚未開始讀書")
            return None

        # 記錄結束時間
        self.end_time = datetime.now()

        # 如果使用者正在暫停時直接結束，
        # 也要把最後一次暫停加入干擾紀錄
        if self.pause_start is not None:

            # 計算最後一次暫停時間
            pause_duration = self.end_time - self.pause_start
            pause_seconds = pause_duration.total_seconds()
            pause_minutes = round(pause_seconds / 60, 2)

            # 加入總暫停時間
            self.total_pause_seconds += pause_seconds

            # 加入干擾紀錄
            self.distractions.append({
                "reason": self.pause_reason,
                "minutes": pause_minutes,
                "time": self.pause_start.strftime("%Y-%m-%d %H:%M:%S")
            })

            # 清空暫停資料
            self.pause_start = None
            self.pause_reason = None

        # 計算總經過時間
        total_time = self.end_time - self.start_time

        # 實際有效讀書秒數
        # = 總經過時間 - 總暫停時間
        self.elapsed_seconds = max(
            0,
            total_time.total_seconds() - self.total_pause_seconds
        )

        # 更新狀態
        self.is_running = False
        self.is_finished = True

        # 產生結果資料
        result = self.generate_result()

        # 如果完成目標，加入休息提醒
        if result["is_completed"]:
            result["break_reminder"] = self.get_break_reminder()
        else:
            result["break_reminder"] = None

        return result

    # ════════════════════════════════════════════
    # 產生 session 結果資料
    # ════════════════════════════════════════════

    def generate_result(self):
        """
        整理並回傳本次讀書 session 的結果資料。
        """

        # 實際讀書分鐘數
        study_minutes = round(self.elapsed_seconds / 60, 2)

        # 目標讀書分鐘數
        target_minutes = round(self.target_seconds / 60, 2)

        # 干擾總分鐘數
        distraction_minutes = round(
            sum(item["minutes"] for item in self.distractions),
            2
        )

        # 完成率，最高為 1
        completion_rate = min(
            study_minutes / target_minutes,
            1
        )

        # 是否完成目標
        is_completed = study_minutes >= target_minutes

        # 專注分數
        # 每 1 分鐘干擾扣 5 分
        # 最低為 0 分
        focus_score = max(
            0,
            round(100 - distraction_minutes * 5)
        )

        # 低專注判定
        # 如果專注分數低於門檻，就標記為低專注
        is_low_focus = (
            focus_score < self.low_focus_threshold
        )

        # 干擾警告判定
        # 如果干擾總時間達到門檻，就需要提醒
        need_focus_warning = (
            distraction_minutes >= self.distraction_warning_minutes
        )

        # 計算 EXP
        exp_gain = self.calculate_exp(self.elapsed_seconds)

        # 計算好感度
        affection_gain = self.calculate_affection_gain(self.elapsed_seconds)

        # 回傳整理好的結果資料
        return {
            "mode": self.mode,
            "tag": self.tag,

            "start_time":
                self.start_time.strftime("%Y-%m-%d %H:%M:%S"),

            "end_time":
                self.end_time.strftime("%Y-%m-%d %H:%M:%S"),

            "target_minutes": target_minutes,
            "study_minutes": study_minutes,

            "distraction_minutes": distraction_minutes,
            "distraction_count": len(self.distractions),
            "distractions": self.distractions,

            "completion_rate": round(completion_rate, 2),
            "is_completed": is_completed,
            "is_aborted": self.is_aborted,

            "focus_score": focus_score,
            "is_low_focus": is_low_focus,
            "need_focus_warning": need_focus_warning,

            "exp_gain": exp_gain,
            "affection_gain": affection_gain,

            "reminders": self.reminders
        }

    # ════════════════════════════════════════════
    # EXP 計算
    # ════════════════════════════════════════════

    def calculate_exp(self, actual_secs):
        """
        計算本次讀書可獲得的 EXP。

        規則：
        1. 每讀書 1 分鐘獲得 1 EXP
        2. 每日累積超過 120 分鐘後，後續 EXP 變成 1.2 倍
        3. 每日 EXP 不能超過 DAILY_EXP_CAP
        """

        # 將秒數轉成分鐘
        actual_min = actual_secs / 60

        # 如果今天原本就已經超過 120 分鐘
        if self.daily_exp_so_far >= EXP_BONUS_THRESHOLD:
            raw_exp = actual_min * 1.2

        # 如果這次 session 途中剛好跨過 120 分鐘
        elif self.daily_exp_so_far + actual_min > EXP_BONUS_THRESHOLD:

            # 超過 120 分鐘以前的部分，維持 1 倍
            before = EXP_BONUS_THRESHOLD - self.daily_exp_so_far

            # 超過 120 分鐘以後的部分，變成 1.2 倍
            after = actual_min - before

            raw_exp = before + after * 1.2

        # 如果還沒超過 120 分鐘
        else:
            raw_exp = actual_min

        # 計算今天還能獲得多少 EXP
        remaining_cap = max(
            0,
            DAILY_EXP_CAP - self.daily_exp_so_far
        )

        # EXP 不可超過每日上限
        return round(
            min(raw_exp, remaining_cap),
            2
        )

    # ════════════════════════════════════════════
    # 好感度計算
    # ════════════════════════════════════════════

    def calculate_affection_gain(self, actual_secs):
        """
        計算本次讀書可增加的好感度。

        規則：
        1. 每連續讀書 15 分鐘增加 1 點好感度
        2. 單次讀書超過 60 分鐘後，超過部分以 2 倍計算
        3. 好感度增加量不可超過 AFF_MAX
        """

        # 將秒數轉成分鐘
        actual_min = actual_secs / 60

        # 60 分鐘以內：
        # 每 15 分鐘增加 1 點
        if actual_min <= 60:
            affection = actual_min / 15

        # 超過 60 分鐘：
        # 前 60 分鐘正常計算
        # 超過部分 2 倍計算
        else:
            before = 60 / 15
            after = (actual_min - 60) / 15 * 2
            affection = before + after

        # 好感度增加量不可超過上限
        return round(
            min(affection, AFF_MAX),
            2
        )
