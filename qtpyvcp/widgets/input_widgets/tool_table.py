from qtpy.QtCore import Qt, Slot, Property, QModelIndex, QSortFilterProxyModel
from qtpy.QtGui import QStandardItemModel
from qtpy.QtWidgets import QTableView, QStyledItemDelegate, QDoubleSpinBox, \
     QSpinBox, QLineEdit, QMessageBox

from qtpyvcp.utilities.logger import getLogger
from qtpyvcp.plugins import getPlugin

LOG = getLogger(__name__)


class ItemDelegate(QStyledItemDelegate):

    def __init__(self, columns):
        super(ItemDelegate, self).__init__()

        self._columns = columns
        self._padding = ' ' * 2

    def displayText(self, value, locale):

        if type(value) == float:
            return "{0:.4f}".format(value)

        return "{}{}".format(self._padding, value)

    def createEditor(self, parent, option, index):
        col = self._columns[index.column()]

        if col == 'R':
            editor = QLineEdit(parent)
            editor.setFrame(False)
            margins = editor.textMargins()
            padding = editor.fontMetrics().width(self._padding) + 1
            margins.setLeft(margins.left() + padding)
            editor.setTextMargins(margins)
            return editor

        elif col in 'TPQ':
            editor = QSpinBox(parent)
            editor.setFrame(False)
            editor.setAlignment(Qt.AlignCenter)
            editor.setMinimum(0)
            editor.setMaximum(100)
            return editor

        elif col in 'XYZABCUVWD':
            editor = QDoubleSpinBox(parent)
            editor.setFrame(False)
            editor.setAlignment(Qt.AlignCenter)
            editor.setDecimals(4)
            # editor.setStepType(QSpinBox.AdaptiveDecimalStepType)
            editor.setProperty('stepType', 1)  # stepType was added in 5.12
            editor.setMinimum(0)
            return editor

        elif col in 'IJ':
            editor = QDoubleSpinBox(parent)
            editor.setFrame(False)
            editor.setAlignment(Qt.AlignCenter)
            editor.setDecimals(2)
            # editor.setStepType(QSpinBox.AdaptiveDecimalStepType)
            editor.setProperty('stepType', 1)  # stepType was added in 5.12
            editor.setMinimum(0)
            return editor

        return None


class ToolModel(QStandardItemModel):
    def __init__(self, parent=None):
        super(ToolModel, self).__init__(parent)

        self.tt = getPlugin('tooltable')

        self._columns = self.tt.columns
        self._column_labels = self.tt.COLUMN_LABELS

        self._tool_table = self.tt.loadToolTable()

        self.setColumnCount(self.columnCount())
        self.setRowCount(100)  # (self.rowCount())

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._column_labels[self._columns[section]]

        return QStandardItemModel.headerData(self, section, orientation, role)

    def columnCount(self, parent=None):
        return len(self._columns)

    def rowCount(self, parent=None):
        return len(self._tool_table) - 1

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            key = self.tt.columns[index.column()]
            tnum = sorted(self._tool_table)[index.row() + 1]
            return self._tool_table[tnum][key]

        elif role == Qt.TextAlignmentRole:
            col = self._columns[index.column()]
            if col == 'R':      # Remark
                return Qt.AlignVCenter | Qt.AlignLeft
            elif col in 'TPQ':  # Integers (Tool, Pocket, Orient)
                return Qt.AlignVCenter | Qt.AlignCenter
            else:               # All the other floats
                return Qt.AlignVCenter | Qt.AlignRight


        return QStandardItemModel.data(self, index, role)

    def setData(self, index, value, role):
        key = self.tt.columns[index.column()]
        tnum = sorted(self._tool_table)[index.row() + 1]
        self._tool_table[tnum][key] = value
        return True

    def removeTool(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        tnum = sorted(self._tool_table)[row + 1]
        del self._tool_table[tnum]
        self.endRemoveRows()
        return True

    def addTool(self):
        try:
            tnum = sorted(self._tool_table)[-1] + 1
        except IndexError:
            tnum = 1

        if tnum > 100:
            # max 100 tools
            return False

        row = len(self._tool_table) - 1

        self.beginInsertRows(QModelIndex(), row, row)
        self._tool_table[tnum] = self.tt.newTool(tnum=tnum)
        self.endInsertRows()
        return True

    def toolDataFromRow(self, row):
        tnum = sorted(self._tool_table)[row]
        return self._tool_table[tnum]

    def saveToolTable(self):
        self.tt.saveToolTable(self._tool_table)
        return True

    def clearToolTable(self):
        self.beginRemoveRows(QModelIndex(), 0, 100)
        # delete all but the spindle, which can't be deleted
        self._tool_table = {0: self._tool_table[0]}
        self.endRemoveRows()
        return True

    def loadToolTable(self):
        self.beginResetModel()
        self._tool_table = self.tt.loadToolTable()
        self.endResetModel()
        return True


class ToolTable(QTableView):
    def __init__(self, parent=None):
        super(ToolTable, self).__init__(parent)

        self.tool_model = ToolModel(self)

        delegate = ItemDelegate(columns=self.tool_model._columns)
        self.setItemDelegate(delegate)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setSourceModel(self.tool_model)

        self.setModel(self.proxy_model)

        # Properties
        self._confirm_actions = False

        # Appearance/Behaviour settings
        self.setSortingEnabled(True)
        self.verticalHeader().hide()
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSortIndicator(0, Qt.AscendingOrder)

    @Slot()
    def saveToolTable(self):
        if not self.confirmAction("Do you want to save changes and\n"
                                  "load tool table into LinuxCNC?"):
            return
        self.tool_model.saveToolTable()

    @Slot()
    def loadToolTable(self):
        if not self.confirmAction("Do you want to re-load the tool table?\n"
                                  "All unsaved changes will be lost."):
            return
        self.tool_model.loadToolTable()

    @Slot()
    def deleteSelectedTool(self):
        current_row = self.selectedRow()
        if current_row == -1:
            # no row selected
            return

        tdata = self.tool_model.toolDataFromRow(current_row)
        if not self.confirmAction("Are you sure you want to delete T{tdata[T]}?\n"
                                  "{tdata[R]}".format(tdata=tdata)):
            return

        self.tool_model.removeTool(current_row)

    @Slot()
    def clearToolTable(self, confirm=True):
        if confirm:
            if not self.confirmAction("Do you want to delete the whole tool table?"):
                return

        self.tool_model.clearToolTable()

    @Slot()
    def addTool(self):
        self.tool_model.addTool()

    def selectedRow(self):
        return self.selectionModel().currentIndex().row()

    def confirmAction(self, message):
        if not self._confirm_actions:
            return True

        box = QMessageBox.question(self,
                                   'Confirm Action',
                                   message,
                                   QMessageBox.Yes,
                                   QMessageBox.No)
        if box == QMessageBox.Yes:
            return True
        else:
            return False

    @Property(bool)
    def confirmActions(self):
        return self._confirm_actions

    @confirmActions.setter
    def confirmActions(self, confirm):
        self._confirm_actions = confirm

    def insertToolAbove(self):
        # it does not make sense to insert tools, since the numbering
        # of all the other tools would have to change.
        self.addTool()
        raise DeprecationWarning("insertToolAbove() will be removed in "
                                 "the future, use addTool() instead")

    def insertToolBelow(self):
        self.addTool()
        raise DeprecationWarning("insertToolBelow() will be removed in "
                                 "the future, use addTool() instead")
