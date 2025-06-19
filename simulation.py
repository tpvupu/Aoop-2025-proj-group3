# simulation.py
import numpy as np
from character import Bubu, Yier, Mitao, Huihui
import setting  # 用來取得資源路徑
import os
import random, statistics, math
import matplotlib.pyplot as plt
from collections import Counter
from pathlib import Path
from bisect import bisect_left  # ★ 用來算 percentile
import csv

class Simulation:
    """
    角色行為模擬與成績分佈分析
    ---------------------------------
    n_players : 進行模擬的人次
    n_actions : 每位學生在一次模擬中執行的動作次數
    out_dir   : 圖檔輸出資料夾
    """
    def __init__(self, n_players: int = 300, n_actions: int = 16,
                 actions=None, characters=None, out_dir: str = setting.SIMULATION_PLOTS_DIR) -> None:
        self.n_players = n_players
        self.n_actions = n_actions
        self.actions = actions or ["study", "rest", "play_game", "socialize"]
        self.characters = characters or [Bubu, Yier, Mitao, Huihui]

        # 迴圈結束後才會填進來的屬性
        self.midterm, self.final = [], []
        self.knowledge, self.gpa = [], []
        self.total_scores = []
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # 核心流程
    # --------------------------------------------------
    def run(self) -> None:
        """執行整體模擬，產生所有 raw data。"""
        self.midterm.clear(); self.final.clear()
        self.knowledge.clear(); self.gpa.clear()

        for _ in range(self.n_players):
            player = random.choice(self.characters)()
            for _ in range(7):
                getattr(player, random.choice(self.actions))(1)
                player.week_number += 1

            player.get_midterm()

            for _ in range(7):
                getattr(player, random.choice(self.actions))(1)
                player.week_number += 1

            player.get_final()
            player.calculate_GPA()

            self.midterm.append(player.midterm)
            self.final.append(player.final)
            self.knowledge.append(player.knowledge)
            self.gpa.append(player.GPA)
            self.total_scores.append(player.total_score)

    
    # --------------------------------------------------
    # 資料處理
    # --------------------------------------------------
    def _smooth_curve(self, y: list[int], window: int = 3) -> list[float]:
        smoothed = []
        for i in range(len(y)):
            start, end = max(0, i - window), min(len(y), i + window + 1)
            smoothed.append(sum(y[start:end]) / (end - start))
        return smoothed


    # --------------------------------------------------
    # 圖表繪製
    # --------------------------------------------------
    def plot_midterm_final(self, highlight_mid: float | None = None, highlight_final: float | None = None) -> Path:
        mid_cnt = Counter(self.midterm)
        fin_cnt = Counter(self.final)

        mid_x = sorted(mid_cnt); mid_y = [mid_cnt[s] for s in mid_x]
        fin_x = sorted(fin_cnt); fin_y = [fin_cnt[s] for s in fin_x]

        smooth_mid_y = self._smooth_curve(mid_y)
        smooth_fin_y = self._smooth_curve(fin_y)

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(mid_x, smooth_mid_y, label=f"Midterm (Avg {statistics.mean(self.midterm):.2f})", linewidth=2)
        ax.plot(fin_x, smooth_fin_y, label=f"Final (Avg {statistics.mean(self.final):.2f})", linewidth=2)

        def plot_highlight(score, x_vals, y_vals, color, label, data):
            if score < x_vals[0] or score > x_vals[-1]:
                return  # 分數超出範圍時不畫

            # 用線性內插找到該分數在平滑曲線上的 y 值
            idx = bisect_left(x_vals, score)
            if idx == 0:
                y_interp = y_vals[0]
            elif idx >= len(x_vals):
                y_interp = y_vals[-1]
            else:
                x0, x1 = x_vals[idx - 1], x_vals[idx]
                y0, y1 = y_vals[idx - 1], y_vals[idx]
                ratio = (score - x0) / (x1 - x0)
                y_interp = y0 + ratio * (y1 - y0)

            # 算出排名百分比
            higher = sum(1 for x in data if x > score)
            pct = higher / len(data) * 100

            ax.plot(score, y_interp, marker='o', color=color, markersize=8)
            ax.text(score, y_interp + max(y_vals) * 0.05,
                    f"{label} {score:.1f}\nTop {pct:.1f}%",
                    ha="center", va="bottom", fontsize=12, color=color)

        if highlight_mid is not None:
            plot_highlight(highlight_mid, mid_x, smooth_mid_y, "blue", "Your Midterm", self.midterm)

        if highlight_final is not None:
            plot_highlight(highlight_final, fin_x, smooth_fin_y, "red", "Your Final", self.final)

        # 設定圖表標題置左
        ax.set_title("Midterm & Final Distribution", loc='left')
        ax.set_xlabel("Score (0 ~ 100)")
        ax.set_ylabel("People")
        ax.set_xlim(0, 100)  # <--- 固定橫軸範圍
        ax.legend()
        ax.grid(True)
        fig.tight_layout()

        out_file = os.path.join(self.out_dir, "midterm_final_highlight.png" if highlight_mid or highlight_final else "midterm_final.png")
        fig.savefig(out_file)
        plt.close(fig)
        return out_file

    def plot_total(self, highlight: float | None = None) -> Path:
        fig, ax = plt.subplots(figsize=(12, 6))
        counts, edges, _ = ax.hist(
            self.total_scores, bins=14, alpha=0.7, edgecolor='black', color="#C89AEB",
            label=f"Total Avg {statistics.mean(self.total_scores):.2f}"
        )

        if highlight is not None:
            pct = sum(1 for x in self.total_scores if x > highlight) / len(self.total_scores) * 100
            bin_idx = np.searchsorted(edges, highlight, side="right") - 1
            bin_idx = np.clip(bin_idx, 0, len(counts) - 1)
            y_point = counts[bin_idx]

            ax.plot(highlight, y_point, marker="o", markersize=8)
            ax.text(highlight, y_point + counts.max() * 0.02,
                    f"Your Total {highlight:.1f}\nTop {pct:.1f}%", 
                    ha="center", va="bottom", fontsize=12)

        ax.set_title("Total Score Distribution", loc='left')
        ax.set_xlabel("Total Score"); ax.set_ylabel("People")
        ax.legend(); ax.grid(True); fig.tight_layout()

        out_file = os.path.join(self.out_dir, "total_highlight.png" if highlight else "total.png")
        fig.savefig(out_file); plt.close(fig)
        return out_file

     # --------------------------------------------------
    # ❶ 重新寫：累積人數表（同分只列一次）
    # --------------------------------------------------
    def cumulative_gpa_counts(self):
        """
        回傳兩個 list：
          gpa_unique   : 由小到大、不重複的 GPA
          cum_counts   : 人數累計——'≥ 該 GPA' 的人數
        """
        counts = Counter(self.gpa)                 # 各 GPA 出現次數
        gpa_unique = sorted(counts)               # 升冪、不重複
        total = len(self.gpa)
        cum_counts = []
        running = total
        for gpa in gpa_unique:
            cum_counts.append(running)
            running -= counts[gpa]                # 下一檔少掉「這一檔」人數
        return gpa_unique, cum_counts

    # --------------------------------------------------
    # ❷ Top-x% 計算—同分共享同一名次
    # --------------------------------------------------
    def percentile_from_top(self, gpa_value: float) -> float:
        """
        回傳『前 x%』；同分者算在同一檔次（≤ 你的全都算落後）。
        """
        higher = sum(1 for g in self.gpa if g > gpa_value)   # 嚴格大於你的
        pct = higher / len(self.gpa) * 100
        return pct 

    # --------------------------------------------
    # ❹ GPA 直方圖（可標註個人成績）
    # --------------------------------------------
    def plot_gpa(self, highlight: float | None = None, bins: int = 12) -> Path:
        """
        畫 GPA 直方圖  
        - highlight: 你的 GPA (0–4.3)，圖上標一點並顯示 Top-x%
        - bins:      直方圖分箱數
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        counts, edges, _ = ax.hist(
            self.gpa, bins=bins, alpha=0.7, edgecolor="black",color ="#A1FAFF",
            label=f"GPA Avg {statistics.mean(self.gpa):.2f}"
        )

        if highlight is not None:
            pct = self.percentile_from_top(highlight)

            # ── 找出 highlight 落在哪個 bin ───────────────────────────
            bin_idx = np.searchsorted(edges, highlight, side="right") - 1
            bin_idx = np.clip(bin_idx, 0, len(counts) - 1)  # 防呆
            y_point = counts[bin_idx]

            # ── 畫標記點與文字 ────────────────────────────────────────
            ax.plot(highlight, y_point, marker="o", markersize=8)
            ax.text(
                highlight, y_point + counts.max() * 0.02,   # 往上 2% 畫標註
                f"Your GPA {highlight:.2f}\nTop {pct:.1f}%",
                va="bottom", ha="center", fontsize=12
            )

        ax.set_title("GPA Distribution", loc='left')
        ax.set_xlabel("GPA (0 ~ 4.3)")
        ax.set_ylabel("People")
        ax.set_xlim(0, 4.3) 
        ax.legend()
        ax.grid(True)

        out_file = os.path.join(self.out_dir, "gpa_highlight.png" if highlight else "gpa.png")
    
        fig.tight_layout()
        fig.savefig(out_file)
        plt.close(fig)
        return out_file
    # --------------------------------------------
    # ❺ 一行完成：跑模擬 + 畫全部圖
    # --------------------------------------------
    def run_and_plot_all(self, personal_gpa: float | None = None) -> None:
        self.run()
        self.plot_midterm_final()
        self.plot_total()
        self.plot_gpa(highlight=personal_gpa)
        #print(f"完成！所有圖檔位於 {self.out_dir.resolve()}")

    def run_and_plot_all_with_player(self, player) -> None:
        self.run()
        self.plot_midterm_final(highlight_mid=player.midterm, highlight_final=player.final)
        self.plot_total(highlight=player.total_score)
        self.plot_gpa(highlight=player.GPA)
        

    def export_gpa_csv(
        self,
        filename: str | Path = "gpa_rank.csv",
        include_percentile: bool = True,
    ) -> Path:
        """
        依 GPA 由高到低輸出 CSV（同分共用名次，但 Rank 會跳號）
        欄位：Rank, GPA, People[, Top%]
        - Rank：名次，＝(前面已累計人數) + 1
        - GPA   ：該分數
        - People ：該分數的人數
        - Top%  ：你若擁有此分數，位於全班前幾 %
                    = (前面已累計人數 / 總人數) × 100
        """
        path = Path(self.out_dir, filename)
        counts   = Counter(self.gpa)            # GPA → 人數
        gpa_desc = sorted(counts, reverse=True) # 由高到低
        total    = len(self.gpa)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["Rank", "GPA", "People"]
            if include_percentile:
                header.append("Top%")
            writer.writerow(header)

            processed = 0                       # 已經累計過多少人
            for g in gpa_desc:
                rank = processed + 1            # 下一名次＝已累計人數 + 1
                row  = [rank, f"{g:.2f}", counts[g]]

                if include_percentile:
                    top_pct = processed / total * 100
                    row.append(f"{top_pct:.1f}%")

                writer.writerow(row)
                processed += counts[g]          # 把這一批人計入累計

        return path
    

    def plot_all_characters(self):
        """
        針對每個角色分別模擬、畫圖，圖檔存到 simulation_plots/{character_name}_run/
        """
        for char_cls in self.characters:
            char_name = char_cls.__name__
            out_dir = self.out_dir / f"{char_name}_run"
            out_dir.mkdir(parents=True, exist_ok=True)

            # 建立一個新的 Simulation 實例，指定 out_dir
            sim = Simulation(
                n_players=self.n_players,
                n_actions=self.n_actions,
                actions=self.actions,
                characters=[char_cls],
                out_dir=out_dir
            )
            sim.run()
            sim.plot_midterm_final()
            sim.plot_total()
            sim.plot_gpa()
            # 也可以輸出 csv
            sim.export_gpa_csv()

    def plot_all_chosen(self):
        """
        針對所有角色，分別模擬「全部都只做 study」、「全部都只做 rest」...，
        圖檔存到 simulation_plots/only_{action}/
        """
        for action in self.actions:
            out_dir = self.out_dir / f"only_{action}"
            out_dir.mkdir(parents=True, exist_ok=True)

            # 建立一個新的 Simulation 實例，指定 actions 只包含一種
            sim = Simulation(
                n_players=self.n_players,
                n_actions=self.n_actions,
                actions=[action],
                characters=self.characters,
                out_dir=out_dir
            )
            sim.run()
            sim.plot_midterm_final()
            sim.plot_total()
            sim.plot_gpa()
            sim.export_gpa_csv()



# -------------------------------
# 範例呼叫
# -------------------------------
if __name__ == "__main__":
    sim = Simulation()
    sim.plot_all_characters()
    sim.plot_all_chosen()

