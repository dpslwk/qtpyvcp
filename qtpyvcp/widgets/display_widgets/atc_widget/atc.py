import hal
import os

# Workarround for nvidia propietary drivers

import ctypes
import ctypes.util
from pprint import pprint

from qtpyvcp.utilities.obj_status import HALStatus

ctypes.CDLL(ctypes.util.find_library("GL"), mode=ctypes.RTLD_GLOBAL)

# end of Workarround


import linuxcnc
from qtpy.QtCore import Signal, Slot, QUrl, QTimer
from qtpy.QtQuickWidgets import QQuickWidget

from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger

LOG = logger.getLogger(__name__)
STATUS = getPlugin('status')
TOOLTABLE = getPlugin('tooltable')
IN_DESIGNER = os.getenv('DESIGNER', False)
WIDGET_PATH = os.path.dirname(os.path.abspath(__file__))


class DynATC(QQuickWidget):
    moveToPocketSig = Signal(int, int, arguments=['previous_pocket', 'pocket_num'])

    # toolInSpindleSig = Signal(int, arguments=['tool_num'])

    rotateFwdSig = Signal(int, arguments=['position'])
    rotateRevSig = Signal(int, arguments=['position'])
    
    rotateSig = Signal(int, arguments=['position'])

    showToolSig = Signal(int, int, arguments=['pocket', 'tool_num'])
    hideToolSig = Signal(int, arguments=['tool_num'])

    def __init__(self, parent=None):
        super(DynATC, self).__init__(parent)

        if IN_DESIGNER:
            return

        self.atc_position = 0
        self.prevous_car_position = None
        self.direction = 0

        self.hal_stat = HALStatus()

        self.car_pos = self.hal_stat.getHALPin('carpos.out')

        self.car_pos.setLogChange(True)
        self.car_pos.connect(self.rotate)

        # self.hal_cw_pin.setLogChange(True)
        # self.hal_cw_pin.connect(self.rotate_forward)
        #
        # self.hal_ccw_pin.setLogChange(True)
        # self.hal_ccw_pin.connect(self.rotate_reverse)

        inifile = os.getenv("INI_FILE_NAME")
        self.inifile = linuxcnc.ini(inifile)

        self.parameter_file = self.inifile.find("RS274NGC", "PARAMETER_FILE")

        self.engine().rootContext().setContextProperty("atc_spiner", self)
        qml_path = os.path.join(WIDGET_PATH, "atc.qml")
        url = QUrl.fromLocalFile(qml_path)

        self.setSource(url)  # Fixme fails on qtdesigner

        self.parameter = dict()


        self.tool_table = None
        self.status_tool_table = None
        self.pockets = dict()
        self.tools = None

        self.offsets = [
            5190,
            5191,
            5192,
            5193,
            5194,
            5195,
            5196,
            5197,
            5198,
            5199,
            5200,
            5201
        ]

        self.load_tools()
        self.draw_tools()

        # STATUS.tool_table.notify(self.load_tools)
        # STATUS.pocket_prepped.notify(self.on_pocket_prepped)

    def hideEvent(self, *args, **kwargs):
        pass  # hack to prevent animation glitch

    def load_tools(self):

        with open(self.parameter_file) as param:
            for line in param.read().splitlines():
                offset = int(line[0:4])
                val = float(line[5:])
                self.parameter[offset] = val

        self.tool_table = TOOLTABLE.getToolTable()
        self.status_tool_table = STATUS.tool_table

        self.pockets = dict()
        self.tools = dict()

        # for index, tool in self.tool_table.items():
        #   self.pockets[tool['P']] = tool['T']
        #   self.tools[tool['T']] = tool['P']

        for index, offset in enumerate(self.offsets):
            self.pockets[index + 1] = self.parameter[offset]

    def draw_tools(self):
        for i in range(1, 13):
            self.hideToolSig.emit(i)

        for pocket, tool in self.pockets.items():
            if 0 < pocket < 13:
                if tool != 0:
                    self.showToolSig.emit(pocket, tool)

    # def on_pocket_prepped(self, pocket_num):
    #
    #     if pocket_num > 0:
    #         self.draw_tools()
    #
    #         tool = self.status_tool_table[pocket_num][0]
    #         next_pocket = self.tool_table[tool]['P']
    #
    #         self.moveToPocketSig.emit(self.atc_position - 1, next_pocket - 1)
    #         self.atc_position = next_pocket
    #
    #     if pocket_num == -1:
    #         tool = self.status_tool_table[self.atc_position][0]
    #         self.hideToolSig.emit(tool)

    @Slot()
    def rotate_forward(self):

        print("rotate FW", self.atc_position)
        self.rotateFwdSig.emit(self.atc_position)
        self.atc_position += 1

    @Slot()
    def rotate_reverse(self):

        print("rotate BW", self.atc_position)
        self.rotateRevSig.emit(self.atc_position)
        self.atc_position -= 1

    def rotate(self, car_pos):
        direction = 0

        if car_pos > self.direction:
            direction = 1
        elif car_pos < self.direction:
            direction = -1

        self.direction = car_pos

        car_pos = int(car_pos)

        if car_pos != self.prevous_car_position:

            if direction < 0:
                self.rotate_forward()
            elif direction > 0:
                self.rotate_reverse()

            if self.prevous_car_position is None:
                self.prevous_car_position = -9999
            else:
                self.prevous_car_position = car_pos

