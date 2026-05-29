"""日本語フォント設定ヘルパー（クロスプラットフォーム）。

japanize_matplotlib は Python 3.12+ で distutils 依存により動かないため、
matplotlib の rcParams を直接設定する方式を採る。
OS 別に利用可能な日本語フォントを順に探して設定する。
"""

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# OS をまたいでよく入っている日本語フォントの候補（優先順）
_CANDIDATES = [
    "Hiragino Sans",          # macOS
    "Hiragino Maru Gothic Pro",
    "YuGothic",               # macOS / Windows
    "Yu Gothic",              # Windows
    "Meiryo",                 # Windows
    "MS Gothic",              # Windows
    "Noto Sans CJK JP",       # Linux (Noto)
    "IPAexGothic",            # Linux (IPA)
    "TakaoGothic",            # Linux
    "Arial Unicode MS",       # フォールバック
]


def set_japanese_font():
    """利用可能な日本語フォントを matplotlib に設定して名前を返す。"""
    available = {f.name for f in fm.fontManager.ttflist}
    for name in _CANDIDATES:
        if name in available:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False  # マイナス記号の豆腐防止
            return name
    # 見つからなければ警告だけ出して既定フォントのまま
    print("警告: 日本語フォントが見つかりませんでした。グラフが文字化けする可能性があります。")
    return None


# import 時に自動設定（japanize_matplotlib と同じ使い勝手）
_USED_FONT = set_japanese_font()
