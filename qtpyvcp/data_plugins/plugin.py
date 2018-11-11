
from qtpy.QtCore import QObject, Signal

class QtPyVCPDataPlugin(QObject):
    """QtPyVCPDataPlugin."""

    protocol = None

    def __init__(self):
        super(QtPyVCPDataPlugin, self).__init__()

    def initialise(self):
        """Initialize the data plugin.

        This method is called after the main event loop has started. Any timers
        or threads used by the plugin should be started here.
        """
        pass

    def terminate(self):
        """Terminate the data plugin.

        This is called right before the main event loop exits. Any cleanup
        of the plugin should be done here, such as saving data to a file.
        """
        pass


class QtPyVCPDataChannel(QObject):
    """QtPyVCPChannel.

    Args:
        address (str) : The address/identifier of the channel.
        value_type (type) : The python type of the item's value. If no type is specified
            the type returned by `type(self.value())` will be used.
        to_str (method) : A method which returns a textual version of the
            item's value. If not specified defaults to the values `__str__` method.
        description (str) : A human readable description of the item.
    """

    valueChanged = Signal([bool], [int], [float], [str], [tuple], [dict])

    def __init__(self, address=None, value_type=None, triggerable=True):
        super(QtPyVCPDataChannel, self).__init__()

        self.address = address
        self.typ = value_type or type(self.value())
        self.triggerable = triggerable

    def handleQuery(self, query):
        item = getattr(self, query)
        if item.iscallable:
            return item()
        else:
            return item

    def handleAssigment(self, attr, value):
        pass

    def value(self):
        """Channel value getter method.

        In a channel implementation the `value` method should return the
        current value of the channel. If getting the value is reasonably
        fast and light (e.g. dict lookup) then that can be done here, but if
        it may take some time (e.g. over a network), then this method should
        return a cashed value that is updated periodically.
        """
        pass

    def text(self):
        """Channel text getter method.

        In a channel implementation this method can be used to return a
        textual representation of the channel's value.
        """
        pass

    def onValueChanged(self, slot):
        """Connect a slot to the value changed signal.

        Args:
            slot : The callback to call when the value changes.
        """
        self.valueChanged[self.typ].connect(slot)

    def onTextChanged(self, slot):
        """Connect a slot to the text changed signal.

        Args:
            slot : The callback to call when the text changes.
        """
        self.valueChanged[str].connect(slot)

    def dataTypes(self):
        if self.to_str == str:
            return [self.typ.__name__]
        else:
            return [self.typ.__name__, 'str']
