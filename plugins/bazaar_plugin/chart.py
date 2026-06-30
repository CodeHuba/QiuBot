"""
生成玩家分数/排名折线图。
横轴: 时间  左轴: 分数(rating)  右轴: 排名(position, 越小越好→反转)
"""
from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

# ── 图片输出目录 ──
_CHART_DIR = Path(__file__).resolve().parents[2] / "data" / "charts"


def _ensure_dir():
    _CHART_DIR.mkdir(parents=True, exist_ok=True)


def _downsample(rh: list[dict], max_points: int = 300) -> list[dict]:
    """每 n 条取一个点，保留首尾。"""
    n = len(rh)
    if n <= max_points:
        return rh
    step = math.ceil(n / max_points)
    sampled = rh[::step]
    if sampled[-1] is not rh[-1]:
        sampled.append(rh[-1])
    return sampled


def _parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def _wsl_to_win(path: Path) -> str:
    """把 /mnt/d/... 转成 D:\\... 供 NapCat 使用。"""
    p = str(path.resolve())
    if p.startswith("/mnt/"):
        parts = p[5:].split("/", 1)
        drive = parts[0].upper()
        rest  = parts[1].replace("/", "\\") if len(parts) > 1 else ""
        return f"{drive}:\\{rest}"
    return p


def generate_stat_chart(username: str, rh: list[dict]) -> str:
    """
    画分数/排名折线图，返回图片的 Windows 绝对路径字符串。
    rh: ratingHistory 列表，每项 {timestamp, rating, position}
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.ticker as ticker

    # ── 字体 ──
    plt.rcParams["font.family"] = "Noto Sans CJK SC"
    plt.rcParams["axes.unicode_minus"] = False

    # ── 降采样 ──
    pts     = _downsample(rh, 300)
    times   = [_parse_ts(p["timestamp"]) for p in pts]
    ratings = [p["rating"]   for p in pts]
    ranks   = [p["position"] for p in pts]

    # ── 统计信息（全量数据）──
    cur_r    = rh[-1]["rating"]
    cur_pos  = rh[-1]["position"]
    peak_r   = max(p["rating"]   for p in rh)
    best_pos = min(p["position"] for p in rh)
    start_r  = rh[0]["rating"]
    delta    = cur_r - start_r
    start_str = rh[0]["timestamp"][:10]
    end_str   = rh[-1]["timestamp"][:10]

    # ── 配色 ──
    BG       = "#1a1d23"
    PANEL    = "#22262f"
    RATING_C = "#4fc3f7"   # 蓝
    RANK_C   = "#ff8a65"   # 橙
    GRID_C   = "#252a35"   # 更暗的网格，不抢眼
    TEXT_C   = "#c9d1d9"
    MUTED_C  = "#6e7681"

    # 左右各留出足够空间，避免轴标签被截断
    fig, ax1 = plt.subplots(figsize=(12, 5.5))
    fig.patch.set_facecolor(BG)
    ax1.set_facecolor(PANEL)
    fig.subplots_adjust(left=0.09, right=0.91, top=0.82, bottom=0.14)

    # ── 左轴：分数 ──
    ax1.plot(times, ratings, color=RATING_C, linewidth=1.8,
             label="分数", zorder=3)
    ax1.fill_between(times, ratings, min(ratings),
                     alpha=0.10, color=RATING_C, zorder=2)
    ax1.set_ylabel("排位分数", color=RATING_C, fontsize=11, labelpad=8)
    ax1.tick_params(axis="y", colors=RATING_C, labelsize=9)
    ax1.tick_params(axis="x", colors=MUTED_C,  labelsize=8.5)
    ax1.spines["left"].set_color(RATING_C)
    ax1.spines["right"].set_visible(False)
    ax1.spines["top"].set_visible(False)
    ax1.spines["bottom"].set_color(GRID_C)

    r_min, r_max = min(ratings), max(ratings)
    r_pad = max((r_max - r_min) * 0.10, 20)
    ax1.set_ylim(r_min - r_pad, r_max + r_pad)

    # ── 右轴：排名（越小越好，轴反转）──
    ax2 = ax1.twinx()
    ax2.plot(times, ranks, color=RANK_C, linewidth=1.8,
             linestyle="--", label="排名", zorder=3, alpha=0.85)
    ax2.set_ylabel("排名（越小越好）", color=RANK_C, fontsize=11, labelpad=10)
    ax2.tick_params(axis="y", colors=RANK_C, labelsize=9)
    ax2.spines["right"].set_color(RANK_C)
    ax2.spines["left"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)

    pos_min, pos_max = min(ranks), max(ranks)
    p_pad = max((pos_max - pos_min) * 0.10, 2)
    ax2.set_ylim(pos_max + p_pad, pos_min - p_pad)  # 反转：小排名在上
    ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=6))

    # ── 网格（仅 ax1，颜色更淡）──
    ax1.grid(True, color=GRID_C, linewidth=0.5, zorder=1)
    ax1.set_axisbelow(True)

    # ── 横轴格式 ──
    days_span = (times[-1] - times[0]).days
    if days_span <= 3:
        fmt = mdates.DateFormatter("%m/%d %H:%M")
        loc = mdates.HourLocator(interval=6)
    elif days_span <= 14:
        fmt = mdates.DateFormatter("%m/%d")
        loc = mdates.DayLocator(interval=1)
    else:
        fmt = mdates.DateFormatter("%m/%d")
        loc = mdates.DayLocator(interval=2)
    ax1.xaxis.set_major_formatter(fmt)
    ax1.xaxis.set_major_locator(loc)
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right",
             color=MUTED_C)

    # ── 当前值标注（最后一个点）──
    ax1.annotate(
        f" {cur_r}",
        xy=(times[-1], ratings[-1]),
        xytext=(5, 0), textcoords="offset points",
        color=RATING_C, fontsize=10, fontweight="bold", va="center",
    )
    ax2.annotate(
        f" #{cur_pos}",
        xy=(times[-1], ranks[-1]),
        xytext=(5, 0), textcoords="offset points",
        color=RANK_C, fontsize=10, fontweight="bold", va="center",
    )

    # ── 标题区域 ──
    delta_str = f"{delta:+d}"
    fig.text(
        0.50, 0.965,
        f"{username}  赛季走势",
        ha="center", va="top",
        color=TEXT_C, fontsize=14, fontweight="bold",
        transform=fig.transFigure,
    )
    fig.text(
        0.50, 0.925,
        f"当前 {cur_r}分  #{cur_pos}   ·   峰值 {peak_r}分   ·   "
        f"最佳排名 #{best_pos}   ·   赛季 {delta_str}分",
        ha="center", va="top",
        color=MUTED_C, fontsize=9,
        transform=fig.transFigure,
    )
    fig.text(
        0.50, 0.895,
        f"{start_str}  ~  {end_str}",
        ha="center", va="top",
        color=MUTED_C, fontsize=8.5,
        transform=fig.transFigure,
    )

    # ── 图例（右上角，不遮数据）──
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(
        lines1 + lines2, labels1 + labels2,
        loc="upper right", fontsize=9,
        facecolor=PANEL, edgecolor=GRID_C,
        labelcolor=TEXT_C,
    )

    # ── 保存 ──
    _ensure_dir()
    out_path = _CHART_DIR / f"stat_{username.lower()}.png"
    fig.savefig(str(out_path), dpi=130, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    return _wsl_to_win(out_path)
