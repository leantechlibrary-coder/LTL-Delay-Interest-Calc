"""
遅延損害金計算機 - Lean Tech Library
裁判所方式（端数期間暦年閏年説）準拠
"""

import sys
from datetime import date, datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QRadioButton,
    QButtonGroup, QTextEdit, QGroupBox, QFrame, QMessageBox,
    QSizePolicy, QSpacerItem, QComboBox, QSpinBox, QDialog, QMenuBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIntValidator, QDoubleValidator, QClipboard, QAction

from calc_engine import calculate


# 元号定義: (名前, 開始日, 西暦オフセット)
ERAS = [
    ("令和", date(2019, 5, 1), 2018),
    ("平成", date(1989, 1, 8), 1988),
    ("昭和", date(1926, 12, 25), 1925),
]


def wareki_to_seireki(era_name: str, wy: int) -> int:
    """和暦年 → 西暦年"""
    for name, _, offset in ERAS:
        if name == era_name:
            return wy + offset
    return 2025


def seireki_to_wareki(d: date) -> tuple[str, int]:
    """西暦date → (元号名, 和暦年)"""
    for name, start, offset in ERAS:
        if d >= start:
            return name, d.year - offset
    return "昭和", d.year - 1925


class WarekiDateWidget(QWidget):
    """和暦入力ウィジェット: [元号▼][年][月][日] (西暦表示)"""

    dateChanged = pyqtSignal()

    def __init__(self, initial_date: date = None, parent=None):
        super().__init__(parent)
        if initial_date is None:
            initial_date = date.today()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 元号コンボボックス
        self.era_combo = QComboBox()
        self.era_combo.addItems([e[0] for e in ERAS])
        self.era_combo.setFixedWidth(70)
        layout.addWidget(self.era_combo)

        # 年
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1, 99)
        self.year_spin.setSuffix("年")
        self.year_spin.setFixedWidth(65)
        layout.addWidget(self.year_spin)

        # 月
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setSuffix("月")
        self.month_spin.setFixedWidth(58)
        layout.addWidget(self.month_spin)

        # 日
        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setSuffix("日")
        self.day_spin.setFixedWidth(55)
        layout.addWidget(self.day_spin)

        # 西暦確認ラベル
        self.seireki_label = QLabel()
        self.seireki_label.setStyleSheet("color: #666; font-size: 11px; margin-left: 4px;")
        layout.addWidget(self.seireki_label)

        layout.addStretch()

        # 初期値設定
        self.set_date(initial_date)

        # シグナル接続
        self.era_combo.currentIndexChanged.connect(self._on_value_changed)
        self.year_spin.valueChanged.connect(self._on_value_changed)
        self.month_spin.valueChanged.connect(self._on_month_changed)
        self.day_spin.valueChanged.connect(self._on_value_changed)

    def set_date(self, d: date):
        """dateオブジェクトでウィジェットの値を設定"""
        self._block_signals(True)
        era_name, wy = seireki_to_wareki(d)
        idx = next((i for i, e in enumerate(ERAS) if e[0] == era_name), 0)
        self.era_combo.setCurrentIndex(idx)
        self.year_spin.setValue(wy)
        self.month_spin.setValue(d.month)
        self._update_day_range()
        self.day_spin.setValue(d.day)
        self._block_signals(False)
        self._update_seireki_label()
        self.dateChanged.emit()

    def get_date(self) -> date | None:
        """現在の入力値からdateを返す。無効な日付ならNone"""
        try:
            era_name = self.era_combo.currentText()
            wy = self.year_spin.value()
            sy = wareki_to_seireki(era_name, wy)
            return date(sy, self.month_spin.value(), self.day_spin.value())
        except ValueError:
            return None

    def _on_value_changed(self):
        self._update_seireki_label()
        self.dateChanged.emit()

    def _on_month_changed(self):
        self._update_day_range()
        self._update_seireki_label()
        self.dateChanged.emit()

    def _update_day_range(self):
        """月に応じて日のSpinBoxの上限を調整"""
        import calendar
        era_name = self.era_combo.currentText()
        wy = self.year_spin.value()
        sy = wareki_to_seireki(era_name, wy)
        m = self.month_spin.value()
        try:
            max_day = calendar.monthrange(sy, m)[1]
        except ValueError:
            max_day = 31
        self.day_spin.setMaximum(max_day)

    def _update_seireki_label(self):
        d = self.get_date()
        if d:
            self.seireki_label.setText(f"({d.strftime('%Y/%m/%d')})")
        else:
            self.seireki_label.setText("(無効な日付)")

    def _block_signals(self, block: bool):
        self.era_combo.blockSignals(block)
        self.year_spin.blockSignals(block)
        self.month_spin.blockSignals(block)
        self.day_spin.blockSignals(block)


class TextViewerDialog(QDialog):
    """テキスト全文表示用の子ダイアログ"""

    def __init__(self, parent, title: str, content: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(620, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(content)
        text_edit.setFont(QFont("Yu Gothic UI", 9))
        text_edit.moveCursor(text_edit.textCursor().MoveOperation.Start)
        layout.addWidget(text_edit)

        close_btn = QPushButton("閉じる")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class AboutDialog(QDialog):
    """カスタムAboutダイアログ（README・ライセンス情報へのリンク付き）"""

    README_TEXT = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "遅延損害金計算機\n"
        "README\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "この度は遅延損害金計算機をご利用いただき、\n"
        "誠にありがとうございます。\n\n"
        "本ツールは、裁判所方式（端数期間暦年閏年説）に準拠した\n"
        "遅延損害金計算ツールです。\n"
        "判決後の振込額計算に特化しています。\n\n\n"
        "■ 主な機能\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "・元本・年利・起算日・支払日を入力して遅延損害金を自動計算\n"
        "・裁判所方式（端数期間暦年閏年説）と年365日日割特約の\n"
        "  両方に対応\n"
        "・初日算入/不算入の切替\n"
        "・閏年考慮/無視（365日特約）の切替\n"
        "・端数処理: 各区間切り捨て/合算後切り捨て\n"
        "  （東京地裁執行部方式）の選択\n"
        "・法定利率プリセットボタン（3%/5%/6%/14.6%）\n"
        "・和暦入力対応（令和・平成・昭和）\n"
        "・計算過程の詳細明細表示\n"
        "・ワンクリックで計算結果をコピー\n\n\n"
        "■ 動作環境\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "OS：Windows 10 / 11（64bit）\n"
        "インターネット接続：不要（完全オフライン動作）\n\n\n"
        "■ 起動方法\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Microsoft Storeからインストール後、\n"
        "スタートメニューから起動してください。\n\n\n"
        "■ 使い方\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. 元本（円）を入力\n"
        "2. 年利（%）を入力、またはプリセットボタンをクリック\n"
        "3. 起算日を和暦で入力（元号・年・月・日）\n"
        "4. 支払日を和暦で入力（「今日」ボタンで当日に設定可能）\n"
        "5. 必要に応じて設定を変更\n"
        "   ・初日算入/不算入\n"
        "   ・閏年考慮/無視\n"
        "   ・端数処理方法\n"
        "6. 「計算」ボタンをクリック\n"
        "7. 遅延損害金・合計振込額・計算明細が表示されます\n"
        "8. 「計算結果・明細をコピー」で結果をクリップボードにコピー\n\n\n"
        "■ 計算方式\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "【特約なし（端数期間暦年閏年説）— デフォルト】\n"
        "遅延損害金 = 元本 × 年利 × (年数 + 平年日÷365 + 閏年日÷366)\n\n"
        "・起算日から年に満つる期間は年利計算\n"
        "・端数期間は暦年（1/1〜12/31）ごとに平年/閏年を判定\n"
        "・閏年に属する日数は÷366、平年は÷365で計算\n\n"
        "【年365日日割特約（閏年無視）】\n"
        "遅延損害金 = 元本 × 年利 × 総日数÷365\n\n\n"
        "■ 参照資料\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "・東京地方裁判所民事執行センター資料\n"
        "  （閏年処理・端数処理）\n\n\n"
        "■ 法定利率の変遷\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "〜令和2年3月31日: 年5%（旧民法）\n"
        "令和2年4月1日〜 : 年3%\n"
        "※旧商事法定利率（年6%）は令和2年4月1日施行の\n"
        "  改正で廃止\n\n\n"
        "■ ソースコード\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "本ソフトウェアはAGPL-3.0ライセンスの下で配布されています。\n"
        "ソースコードはGitHubで公開しています。\n"
        "https://github.com/leantechlibrary-coder/LTL-Delay-Interest-Calc\n\n"
        "再配布の際はライセンス条件に従ってください。\n\n\n"
        "■ 免責事項\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "本ソフトウェアの計算結果の正確性について、\n"
        "著作者は保証するものではありません。\n"
        "計算結果の利用は自己責任でお願いいたします。\n"
        "実務でのご利用に際しては、\n"
        "必ずご自身で計算結果をご確認ください。\n\n\n"
        "■ 開発・販売\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Lean Tech Library\n"
        "Simple tools that make you smile\n"
    )

    LICENSE_TEXT = (
        "================================================================================\n"
        "THIRD-PARTY SOFTWARE LICENSES\n"
        "遅延損害金計算機\n"
        "================================================================================\n\n"
        "本ソフトウェアは、以下のオープンソースソフトウェアを使用しています。\n"
        "各ソフトウェアのライセンス条項に従い、ライセンス情報を記載します。\n\n\n"
        "================================================================================\n"
        "1. PyQt6\n"
        "================================================================================\n\n"
        "License: GNU General Public License v3.0 (GPL-3.0)\n"
        "Copyright: Riverbank Computing Limited\n"
        "Website: https://www.riverbankcomputing.com/software/pyqt/\n\n"
        "ライセンス全文：https://www.gnu.org/licenses/gpl-3.0.txt\n\n\n"
        "================================================================================\n"
        "2. python-dateutil\n"
        "================================================================================\n\n"
        "License: Apache License 2.0 / BSD 3-Clause\n"
        "Copyright: Gustavo Niemeyer, Paul Ganssle\n"
        "Website: https://github.com/dateutil/dateutil\n\n"
        "Licensed under the Apache License, Version 2.0 and BSD 3-Clause License.\n"
        "You may obtain a copy of the License at:\n"
        "https://www.apache.org/licenses/LICENSE-2.0\n\n\n"
        "================================================================================\n"
        "本ソフトウェアのライセンス\n"
        "================================================================================\n\n"
        "遅延損害金計算機\n"
        "Copyright (c) 2026 Lean Tech Library\n\n"
        "本ソフトウェアはAGPL-3.0ライセンスの下で配布されています。\n"
        "ソースコードはGitHubで公開しています。\n"
        "https://github.com/leantechlibrary-coder/LTL-Delay-Interest-Calc\n\n"
        "再配布の際はライセンス条件に従ってください。\n"
        "ライセンス全文：https://www.gnu.org/licenses/agpl-3.0.txt\n"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("遅延損害金計算機について")
        self.setFixedSize(480, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # About本文
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setFont(QFont("Yu Gothic UI", 9))
        about_text.setPlainText(
            "遅延損害金計算機  v1.0.0\n\n"
            "裁判所方式（端数期間暦年閏年説）準拠の\n"
            "遅延損害金計算ツールです。\n"
            "判決後の振込額計算に特化しています。\n\n"
            "【動作環境】\n"
            "Windows 10 / 11（64bit）\n"
            "インターネット接続不要（完全オフライン動作）\n\n"
            "【重要】\n"
            "本ソフトウェアの計算結果の正確性について、\n"
            "開発者は保証するものではありません。\n"
            "実務でのご利用に際しては、\n"
            "必ずご自身で計算結果をご確認ください。\n\n"
            "【開発・販売】\n"
            "Lean Tech Library\n\n"
            "ご使用前にREADMEをご確認ください。"
        )
        about_text.moveCursor(about_text.textCursor().MoveOperation.Start)
        layout.addWidget(about_text)

        # リンクボタン
        link_layout = QHBoxLayout()
        link_layout.setSpacing(8)

        readme_btn = QPushButton("README")
        readme_btn.setToolTip("READMEを表示します")
        readme_btn.clicked.connect(self._show_readme)

        license_btn = QPushButton("ライセンス情報")
        license_btn.setToolTip("サードパーティライセンス情報を表示します")
        license_btn.clicked.connect(self._show_licenses)

        link_layout.addWidget(readme_btn)
        link_layout.addWidget(license_btn)
        layout.addLayout(link_layout)

        # 閉じるボタン
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("閉じる")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        close_layout.addStretch()
        layout.addLayout(close_layout)

    def _show_readme(self):
        dlg = TextViewerDialog(self, "README", self.README_TEXT)
        dlg.exec()

    def _show_licenses(self):
        dlg = TextViewerDialog(self, "ライセンス情報", self.LICENSE_TEXT)
        dlg.exec()


def show_about_dialog(parent=None):
    """Aboutダイアログを表示"""
    dlg = AboutDialog(parent)
    dlg.exec()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("遅延損害金計算機 - Lean Tech Library")
        self.setMinimumWidth(700)
        self.setMinimumHeight(750)

        # --- メニューバー ---
        menubar = self.menuBar()
        help_menu = menubar.addMenu("ヘルプ(&H)")
        about_action = QAction("このツールについて(&A)", self)
        about_action.triggered.connect(lambda: show_about_dialog(self))
        help_menu.addAction(about_action)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # --- タイトル ---
        title = QLabel("遅延損害金計算機")
        title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        subtitle = QLabel("判決後の振込額計算に")
        subtitle.setFont(QFont("Yu Gothic UI", 9))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        main_layout.addWidget(subtitle)

        # --- 入力エリア ---
        input_group = QGroupBox("入力")
        input_layout = QGridLayout(input_group)
        input_layout.setSpacing(8)

        # 元本
        input_layout.addWidget(QLabel("元本（円）:"), 0, 0)
        self.principal_edit = QLineEdit()
        self.principal_edit.setPlaceholderText("例: 1000000")
        self.principal_edit.setValidator(QIntValidator(0, 2147483647))
        input_layout.addWidget(self.principal_edit, 0, 1, 1, 2)

        # 利率
        input_layout.addWidget(QLabel("年利（%）:"), 1, 0)
        self.rate_edit = QLineEdit()
        self.rate_edit.setPlaceholderText("例: 3")
        self.rate_edit.setValidator(QDoubleValidator(0.0, 100.0, 4))
        input_layout.addWidget(self.rate_edit, 1, 1)

        # プリセットボタン
        preset_layout = QHBoxLayout()
        for label, value in [("3%", "3"), ("5%", "5"), ("6%", "6"), ("14.6%", "14.6")]:
            btn = QPushButton(label)
            btn.setFixedWidth(50)
            btn.setStyleSheet("font-size: 11px; padding: 2px;")
            btn.clicked.connect(lambda checked, v=value: self.rate_edit.setText(v))
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        input_layout.addLayout(preset_layout, 1, 2)

        # 起算日
        input_layout.addWidget(QLabel("起算日:"), 2, 0)
        today = date.today()
        one_year_ago = date(today.year - 1, today.month, today.day)
        self.start_date_widget = WarekiDateWidget(one_year_ago)
        input_layout.addWidget(self.start_date_widget, 2, 1, 1, 2)

        # 支払日
        input_layout.addWidget(QLabel("支払日:"), 3, 0)
        self.end_date_widget = WarekiDateWidget(today)
        input_layout.addWidget(self.end_date_widget, 3, 1)

        today_btn = QPushButton("今日")
        today_btn.setFixedWidth(50)
        today_btn.clicked.connect(lambda: self.end_date_widget.set_date(date.today()))
        input_layout.addWidget(today_btn, 3, 2)

        main_layout.addWidget(input_group)

        # --- 設定エリア ---
        settings_group = QGroupBox("設定")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setSpacing(6)

        # 初日算入/不算入
        settings_layout.addWidget(QLabel("初日:"), 0, 0)
        self.first_day_group = QButtonGroup()
        self.rb_exclude = QRadioButton("不算入（デフォルト）")
        self.rb_include = QRadioButton("算入")
        self.rb_exclude.setChecked(True)
        self.first_day_group.addButton(self.rb_exclude, 0)
        self.first_day_group.addButton(self.rb_include, 1)
        fd_layout = QHBoxLayout()
        fd_layout.addWidget(self.rb_exclude)
        fd_layout.addWidget(self.rb_include)
        fd_layout.addStretch()
        settings_layout.addLayout(fd_layout, 0, 1)

        # 閏年考慮
        settings_layout.addWidget(QLabel("閏年:"), 1, 0)
        self.leap_group = QButtonGroup()
        self.rb_leap_yes = QRadioButton("考慮する（デフォルト）")
        self.rb_leap_no = QRadioButton("無視する（365日特約）")
        self.rb_leap_yes.setChecked(True)
        self.leap_group.addButton(self.rb_leap_yes, 0)
        self.leap_group.addButton(self.rb_leap_no, 1)
        lp_layout = QHBoxLayout()
        lp_layout.addWidget(self.rb_leap_yes)
        lp_layout.addWidget(self.rb_leap_no)
        lp_layout.addStretch()
        settings_layout.addLayout(lp_layout, 1, 1)

        # 端数処理
        settings_layout.addWidget(QLabel("端数処理:"), 2, 0)
        self.trunc_group = QButtonGroup()
        self.rb_trunc_each = QRadioButton("各区間ごとに切り捨て（デフォルト）")
        self.rb_trunc_total = QRadioButton("合算後に切り捨て（裁判所方式）")
        self.rb_trunc_each.setChecked(True)
        self.trunc_group.addButton(self.rb_trunc_each, 0)
        self.trunc_group.addButton(self.rb_trunc_total, 1)
        tr_layout = QHBoxLayout()
        tr_layout.addWidget(self.rb_trunc_each)
        tr_layout.addWidget(self.rb_trunc_total)
        tr_layout.addStretch()
        settings_layout.addLayout(tr_layout, 2, 1)

        main_layout.addWidget(settings_group)

        # --- 計算ボタン ---
        btn_layout = QHBoxLayout()
        calc_btn = QPushButton("計算")
        calc_btn.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        calc_btn.setFixedHeight(40)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        calc_btn.clicked.connect(self.on_calculate)
        btn_layout.addWidget(calc_btn)

        clear_btn = QPushButton("クリア")
        clear_btn.setFixedHeight(40)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        clear_btn.clicked.connect(self.on_clear)
        btn_layout.addWidget(clear_btn)
        main_layout.addLayout(btn_layout)

        # --- 結果表示 ---
        result_group = QGroupBox("計算結果")
        result_layout = QVBoxLayout(result_group)

        # 金額表示
        amount_layout = QGridLayout()
        amount_layout.setSpacing(4)

        self.lbl_delay = QLabel("―")
        self.lbl_delay.setFont(QFont("Yu Gothic UI", 18, QFont.Weight.Bold))
        self.lbl_delay.setStyleSheet("color: #dc2626;")
        amount_layout.addWidget(QLabel("遅延損害金:"), 0, 0)
        amount_layout.addWidget(self.lbl_delay, 0, 1)

        self.lbl_total = QLabel("―")
        self.lbl_total.setFont(QFont("Yu Gothic UI", 18, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet("color: #059669;")
        amount_layout.addWidget(QLabel("合計振込額:"), 1, 0)
        amount_layout.addWidget(self.lbl_total, 1, 1)

        result_layout.addLayout(amount_layout)

        # コピーボタン
        copy_btn = QPushButton("計算結果・明細をコピー")
        copy_btn.clicked.connect(self.copy_all)
        result_layout.addWidget(copy_btn)

        # 計算過程
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Consolas, Yu Gothic UI", 10))
        self.detail_text.setMinimumHeight(150)
        self.detail_text.setPlaceholderText("計算結果がここに表示されます")
        result_layout.addWidget(self.detail_text)

        main_layout.addWidget(result_group)

        # 計算結果の保持
        self.last_result = None

        # フッター
        footer = QLabel("Lean Tech Library | Simple tools that make you smile")
        footer.setFont(QFont("Yu Gothic UI", 8))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #999;")
        main_layout.addWidget(footer)

    def on_calculate(self):
        # 入力値の取得とバリデーション
        principal_text = self.principal_edit.text().strip()
        rate_text = self.rate_edit.text().strip()

        if not principal_text:
            QMessageBox.warning(self, "入力エラー", "元本を入力してください。")
            self.principal_edit.setFocus()
            return

        if not rate_text:
            QMessageBox.warning(self, "入力エラー", "年利を入力してください。")
            self.rate_edit.setFocus()
            return

        try:
            principal = int(principal_text.replace(",", ""))
        except ValueError:
            QMessageBox.warning(self, "入力エラー", "元本は整数で入力してください。")
            return

        try:
            rate_percent = float(rate_text.replace(",", ""))
            rate = rate_percent / 100.0
        except ValueError:
            QMessageBox.warning(self, "入力エラー", "年利は数値で入力してください。")
            return

        if principal <= 0:
            QMessageBox.warning(self, "入力エラー", "元本は正の値を入力してください。")
            return

        if rate <= 0:
            QMessageBox.warning(self, "入力エラー", "年利は正の値を入力してください。")
            return

        start_date = self.start_date_widget.get_date()
        end_date = self.end_date_widget.get_date()

        if start_date is None:
            QMessageBox.warning(self, "入力エラー", "起算日が無効です。日付を確認してください。")
            return

        if end_date is None:
            QMessageBox.warning(self, "入力エラー", "支払日が無効です。日付を確認してください。")
            return

        if start_date >= end_date:
            QMessageBox.warning(self, "入力エラー", "支払日は起算日より後の日付にしてください。")
            return

        include_first_day = self.rb_include.isChecked()
        consider_leap = self.rb_leap_yes.isChecked()
        truncate_each = self.rb_trunc_each.isChecked()

        # 計算実行
        result = calculate(
            principal=principal,
            rate=rate,
            start_date=start_date,
            end_date=end_date,
            include_first_day=include_first_day,
            consider_leap=consider_leap,
            truncate_each=truncate_each,
        )

        self.last_result = result

        # 結果表示
        self.lbl_delay.setText(f"{result.delay_interest:,} 円")
        self.lbl_total.setText(f"{result.total_payment:,} 円")

        # 計算明細の冒頭に遅延損害金・合計振込額を追加
        header = (
            f"遅延損害金: {result.delay_interest:,}円\n"
            f"合計振込額: {result.total_payment:,}円\n"
            f"{'─' * 30}\n"
        )
        self.detail_text.setPlainText(header + result.detail_text)

    def on_clear(self):
        self.principal_edit.clear()
        self.rate_edit.clear()
        today = date.today()
        self.start_date_widget.set_date(date(today.year - 1, today.month, today.day))
        self.end_date_widget.set_date(today)
        self.rb_exclude.setChecked(True)
        self.rb_leap_yes.setChecked(True)
        self.rb_trunc_each.setChecked(True)
        self.lbl_delay.setText("―")
        self.lbl_total.setText("―")
        self.detail_text.clear()
        self.last_result = None
        self.principal_edit.setFocus()

    def copy_all(self):
        if not self.last_result:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(self.detail_text.toPlainText())


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
