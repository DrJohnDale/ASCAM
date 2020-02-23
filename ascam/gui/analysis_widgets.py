import logging

# pylint: disable=no-name-in-module
from PySide2.QtCore import QAbstractTableModel, Qt
from PySide2 import QtWidgets
from PySide2.QtWidgets import (
    QComboBox,
    QDialog,
    QTableView,
    QSpacerItem,
    QGridLayout,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QLineEdit,
    QToolButton,
    QTabBar,
    QPushButton,
    QLabel,
)

from ascam.utils import string_to_array, array_to_string
from ascam.constants import TIME_UNIT_FACTORS, CURRENT_UNIT_FACTORS


debug_logger = logging.getLogger("ascam.debug")


class IdealizationFrame(QWidget):
    def __init__(self, main):
        super().__init__()

        self.main = main
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.create_widgets()

    @property
    def current_tab(self):
        return self.tab_frame.currentWidget()

    def create_widgets(self):
        self.tab_frame = IdealizationTabFrame(self)
        self.layout.addWidget(self.tab_frame)

        self.calc_button = QPushButton("Calculate idealization")
        self.calc_button.clicked.connect(self.idealize_episode)
        self.layout.addWidget(self.calc_button)
        self.events_button = QPushButton("Create Table of Events")
        self.events_button.clicked.connect(self.create_event_frame)
        self.layout.addWidget(self.events_button)

        # self.apply_button = QPushButton("Apply")
        # self.apply_button.clicked.connect(self.apply)
        # self.layout.addWidget(self.apply_button)

        self.close_button = QPushButton("Close Tab")
        self.close_button.clicked.connect(self.close_tab)
        self.layout.addWidget(self.close_button)

        self.layout.addItem(
            QSpacerItem(
                20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
            )
        )

    def plot_params(self):
        amps, thresh, resolution, intrp_factor = self.get_params()
        if self.current_tab.show_amp_check.isChecked():
            self.main.plot_frame.plot_amp_lines(amps)
        else:
            self.main.plot_frame.clear_amp_lines()
        if self.current_tab.show_threshold_check.isChecked():
            self.main.plot_frame.plot_theta_lines(thresh)
        else:
            self.main.plot_frame.clear_theta_lines()

    def close_tab(self):
        if self.tab_frame.count() > 1:
            self.tab_frame.removeTab(self.tab_frame.currentIndex())

    def create_event_frame(self):
        self.current_tab.event_table = self.create_table()
        self.event_table_frame = EventTableFrame(self, self.current_tab.event_table)

    def create_table(self):
        self.idealize_series()
        events = self.main.data.get_events()
        return EventTableModel(
            events, self.main.data.trace_unit, self.main.data.time_unit
        )

    def get_params(self):
        amps = string_to_array(self.current_tab.amp_entry.text())
        thresholds = string_to_array(self.current_tab.threshold_entry.text())
        res_string = self.current_tab.res_entry.text()
        intrp_string = self.current_tab.intrp_entry.text()

        if self.current_tab.auto_thresholds.isChecked() or (
            thresholds is None or thresholds.size != amps.size - 1
        ):
            thresholds = (amps[1:] + amps[:-1]) / 2
            self.current_tab.threshold_entry.setText(array_to_string(thresholds))
            self.current_tab.auto_thresholds.setChecked(True)
            self.current_tab.threshold_entry.setEnabled(False)

        if self.current_tab.neg_check.isChecked():
            amps *= -1
            thresholds *= -1

        trace_factor = CURRENT_UNIT_FACTORS[
            self.current_tab.amp_unit_choice.currentText()
        ]
        amps /= trace_factor
        thresholds /= trace_factor
        time_factor = TIME_UNIT_FACTORS[self.current_tab.time_unit_choice.currentText()]

        if res_string.strip() and self.current_tab.use_res.isChecked():
            resolution = float(res_string)
            resolution /= time_factor
        else:
            resolution = None

        if intrp_string.strip() and self.current_tab.interpolate.isChecked():
            intrp_factor = int(intrp_string)
        else:
            intrp_factor = 1

        return amps, thresholds, resolution, intrp_factor

    def idealize_episode(self):
        amps, thresh, resolution, intrp_factor = self.get_params()
        self.main.data.idealize_episode(amps, thresh, resolution, intrp_factor)
        self.main.plot_frame.plot_episode()
        self.plot_params()

    def idealize_series(self):
        amps, thresh, resolution, intrp_factor = self.get_params()
        self.main.data.idealize_series(amps, thresh, resolution, intrp_factor)

    def apply(self):
        pass


class IdealizationTabFrame(QTabWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.tabs = [IdealizationTab(self)]
        self.addTab(self.tabs[0], "1")

        self.insertTab(1, QWidget(), "")
        self.new_button = QToolButton()
        self.new_button.setText("+")
        self.new_button.clicked.connect(self.add_tab)
        self.tabBar().setTabButton(1, QTabBar.RightSide, self.new_button)

        self.setTabsClosable(True)
        self.tabBar().tabCloseRequested.connect(self.removeTab)

        self.currentChanged.connect(self.switch_tab)

    def add_tab(self):
        title = str(self.count())
        debug_logger.debug(f"adding new tab with number {title}")
        tab = IdealizationTab(self)
        self.tabs.append(tab)
        ind = self.insertTab(self.count() - 1, tab, title)
        self.setCurrentIndex(ind)

    def switch_tab(self):
        self.parent.idealize_episode()


class IdealizationTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.create_widgets()

    def create_widgets(self):
        row_one = QHBoxLayout()
        amp_label = QLabel("Amplitudes")
        row_one.addWidget(amp_label)
        self.amp_unit_choice = QComboBox()
        self.amp_unit_choice.addItems(CURRENT_UNIT_FACTORS.keys())
        self.amp_unit_choice.setCurrentIndex(1)
        row_one.addWidget(self.amp_unit_choice)
        self.show_amp_check = QCheckBox("Show")
        row_one.addWidget(self.show_amp_check)
        self.neg_check = QCheckBox("Negative Values")
        row_one.addWidget(self.neg_check)
        self.layout.addLayout(row_one)

        self.amp_entry = QLineEdit()
        self.layout.addWidget(self.amp_entry)

        row_three = QHBoxLayout()
        threshold_label = QLabel("Thresholds")
        row_three.addWidget(threshold_label)
        self.show_threshold_check = QCheckBox("Show")
        row_three.addWidget(self.show_threshold_check)
        self.auto_thresholds = QCheckBox("Automatic")
        self.auto_thresholds.stateChanged.connect(self.toggle_auto_theta)
        row_three.addWidget(self.auto_thresholds)
        self.layout.addLayout(row_three)

        self.threshold_entry = QLineEdit()
        self.layout.addWidget(self.threshold_entry)

        row_four = QHBoxLayout()
        res_label = QLabel("Resolution")
        row_four.addWidget(res_label)
        self.time_unit_choice = QComboBox()
        self.time_unit_choice.addItems(TIME_UNIT_FACTORS.keys())
        self.time_unit_choice.setCurrentIndex(1)
        row_four.addWidget(self.time_unit_choice)
        self.use_res = QCheckBox("Apply")
        self.use_res.stateChanged.connect(self.toggle_resolution)
        row_four.addWidget(self.use_res)
        self.layout.addLayout(row_four)

        self.res_entry = QLineEdit()
        self.layout.addWidget(self.res_entry)

        row_six = QHBoxLayout()
        intrp_label = QLabel("Interpolation")
        row_six.addWidget(intrp_label)
        self.interpolate = QCheckBox("Apply")
        self.interpolate.stateChanged.connect(self.toggle_interpolation)
        row_six.addWidget(self.interpolate)
        self.layout.addLayout(row_six)

        self.intrp_entry = QLineEdit()
        self.layout.addWidget(self.intrp_entry)

    def toggle_interpolation(self, state):
        if not state:
            self.intrp_entry.setEnabled(False)
        else:
            self.intrp_entry.setEnabled(True)

    def toggle_resolution(self, state):
        if not state:
            self.res_entry.setEnabled(False)
        else:
            self.res_entry.setEnabled(True)

    def toggle_auto_theta(self, state):
        # apparently state==2 if the box is checked and 0
        # if it is not
        if state:
            self.threshold_entry.setEnabled(False)
        else:
            self.threshold_entry.setEnabled(True)


class EventTableFrame(QDialog):
    def __init__(self, parent, table_view):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("Events")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.event_table = QTableView()
        self.event_table.setModel(table_view)

        self.layout.addWidget(self.event_table)
        self.setModal(False)
        self.show()

    def create_table(self):
        events = self.parent.main.data.get_events()
        self.q_event_table = EventTableModel(
            events, self.parent.main.data.trace_unit, self.parent.main.data.time_unit
        )
        self.event_table = QTableView()
        self.event_table.setModel(self.q_event_table)


class EventTableModel(QAbstractTableModel):
    def __init__(self, data, current_unit, time_unit):
        super().__init__()
        # super(TableModel, self).__init__()
        self._data = data
        self._data[:, 0] *= CURRENT_UNIT_FACTORS[current_unit]
        self._data[:, 1:] *= TIME_UNIT_FACTORS[time_unit]

        self._header = [
            f"Amplitude [{current_unit}]",
            f"Duration [{time_unit}]",
            f"t_start",
            "t_stop",
            "Episode #",
        ]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # See below for the nested-list data structure.
            # .row() indexes into the outer list,
            # .column() indexes into the sub-list
            if index.row() == 0:
                return self._header[index.column()]
            return self._data[index.row() - 1][index.column()]

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return len(self._data[0])


class FirstActivationFrame(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.create_widgets()

    def create_widgets(self):
        threshold_button = QPushButton("Set threshold")
        threshold_entry = QLineEdit()
        self.layout.addWidget(threshold_button, 1, 1)
        self.layout.addWidget(threshold_entry, 1, 2)

        mark_button = QPushButton("Mark events manually")
        jump_checkbox = QCheckBox("Click jumps to next episode:")
        self.layout.addWidget(mark_button, 2, 1)
        self.layout.addWidget(jump_checkbox, 2, 2)

        finish_button = QPushButton("Finish")
        cancel_button = QPushButton("Cancel")
        self.layout.addWidget(finish_button, 3, 1)
        self.layout.addWidget(cancel_button, 3, 2)