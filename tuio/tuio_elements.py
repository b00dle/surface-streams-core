import copy
from typing import List


class TuioSessionId(object):
    """
    Provides a static interface to the generation of session ids, which are unique within one process.
    """

    _current = 0
    _existing = []

    @staticmethod
    def get(keep_current=False):
        """
        Returns the current session id.

        :param keep_current: if True, the current session id will be increased by one, else it stays the same.

        :return: session id (int)
        """
        s_id = TuioSessionId._current
        if not keep_current:
            TuioSessionId._current += 1
            if s_id in TuioSessionId._existing:
                s_id = TuioSessionId.get()
            TuioSessionId._existing.append(s_id)
        return s_id

    @staticmethod
    def get_existing():
        """
        Get a list of session ids already produced by this class, or added externally (see self.add_existing).

        :return: list of session ids (int)
        """
        return copy.deepcopy(TuioSessionId._existing)

    @staticmethod
    def add_existing(s_id):
        """
        Log a session id as existing. This will prevent given number from being returned by self.get(...).

        :param s_id: session id to blacklist.

        :return: None
        """
        if s_id not in TuioSessionId._existing:
            TuioSessionId._existing.append(s_id)


class TuioData(object):
    """
    Describes arbitrary extension data for any TuioElement.
    """

    def __init__(self, mime_type="string", data=""):
        """
        Constructor.

        :param mime_type: mime type identifying the type of data within this instance.

        :param data: actual data contained by this instance.
        """
        self.mime_type = mime_type
        self.data = data

    def __str__(self):
        s = "<TuioData mime_type="+self.mime_type+" data="+str(self.data)+">"
        return s

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return other.mime_type == self.mime_type

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def parse_str_to_rgb(rgb_string: str) -> List[int]:
        """
        Converts string representation of rgb formatted color values to list representation.

        :param rgb_string: color string. Format should be "<r>,<g>,<b>", with <r>, <g> & <b> in range [0,255]

        :return: list representation of color values. Format is [<r>,<g>,<b>]
        """
        rgb = rgb_string.split(",")
        if len(rgb) == 3:
            return [int(c) % 256 for c in rgb]
        return []

    @staticmethod
    def parse_rgb_to_str(rgb: List[int]) -> str:
        """
        Converts string representation of rgb formatted color values to list representation.

        :param rgb: list representation of color values. Format is [<r>,<g>,<b>]

        :return: color string. Format should be "<r>,<g>,<b>", with <r>, <g> & <b> in range [0,255]
        """
        return str(rgb[0]) + "," + str(rgb[1]) + "," + str(rgb[2])


class TuioElement(object):
    """
    Base class for most ordinary tuio elements. Provides an interface to append and read arbitrary data using TuioData.
    """

    def __init__(self):
        """
        Constructor.
        """
        self._data = []

    def append_data(self, data: TuioData, remove_similar=True):
        """
        Add arbitrary data (TuioData) to this instance.

        :param data: TuioData to append to this instance.

        :param remove_similar: If true, all other TuioData appended to this instance with a similar mime type will be
        removed.

        :return: None
        """
        if remove_similar:
            if data in self._data:
                self._data.remove(data)
        self._data.append(data)

    def append_data_list(self, data: List[TuioData], remove_similar=True):
        """
        Add a list of arbitrary data (TuioData) to this instance.

        :param data: list of TuioData to append to this instance.

        :param remove_similar: If true, all other TuioData appended to this instance with a mime type similar to any of
        the ones contained in given data list will be removed.

        :return: None
        """
        if remove_similar:
            for d in data:
                if d in self._data:
                    self._data.remove(d)
        self._data.extend(data)

    def get_data(self):
        """
        Returns a copy of all data (TuioData) added to this instance.

        :return: list of TuioData
        """
        return copy.deepcopy(self._data)

    def get_value_by_mime_type(self, mime_type):
        """
        Returns the value of first TuioData with given mime type attached to this instance.

        :param mime_type: mime type of data to find

        :return: data of given type or None if doesn't exist.
        """
        for d in self._data:
            if d.mime_type == mime_type:
                return d.data
        return None

    def __str__(self):
        s = "<TuioElement data="+str(self._data)+">"
        return s

    def __repr__(self):
        return self.__str__()


class TuioSessionElement(TuioElement):
    """
    Describes a TuioElement with a session id assigned to it.
    """

    def __init__(self, s_id=-1):
        """
        Constructor.

        :param s_id: session id assigned to this instance. If -1 a session id is retrieved from TuioSessionId.
        """
        super().__init__()
        self.s_id = s_id
        if self.s_id == -1:
            self.s_id = TuioSessionId().get()

    def is_empty(self):
        """
        Returns True if session id of this instance is -1. False otherwise.

        :return: bool
        """
        return self.s_id == -1

    def __str__(self):
        s = "<TuioSessionElement s_id="+str(self.s_id)+">"
        return s

    def __repr__(self):
        return self.__str__()


class TuioBounds(TuioElement):
    """
    Describes bnd TuioElement, which is a (rotated) bounding box defined by [x,y]-pos, angle, width & height
    """

    def __init__(self, x_pos=0.0, y_pos=0.0, angle=0.0, width=0.0, height=0.0):
        """
        Constructor.

        :param x_pos: x position

        :param y_pos: y position

        :param angle: rotation angle

        :param width: width of bounds

        :param height: height of bounds
        """
        super().__init__()
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.angle = angle
        self.width = width
        self.height = height

    def is_empty(self):
        """
        Returns True if width and height of bounds are smaller or equal to 0. False otherwise.

        :return: bool
        """
        return self.width <= 0 or self.height <= 0

    def normalized(self, h, w):
        """
        Returns a copy of this instance with x/w, y/h, width/w and height/h.

        :param h: normal height

        :param w: normal width

        :return: TuioBounds
        """
        return TuioBounds(self.x_pos / w, self.y_pos / h, self.angle, self.width / w, self.height / h)

    def scaled(self, h, w):
        """
        Returns a copy of this instance with x*w, y*h, width*w and height*h.

        :param h: scale height

        :param w: scale width

        :return: TuioBounds
        """
        return TuioBounds(self.x_pos * w, self.y_pos * h, self.angle, self.width * w, self.height * h)

    def __str__(self):
        s = "<TuioBounds x_pos="+str(self.x_pos)+" y_pos="+str(self.y_pos)+" "
        s += "angle="+str(self.angle)+" width="+str(self.width)+" "
        s += "height="+str(self.height)+">"
        return s

    def __repr__(self):
        return self.__str__()


class TuioSymbol(TuioElement):
    """
    Describes a sym TuioElement. Value of this symbol is a uuid. It can be identified by type id and component id.
    """

    def __init__(self, uuid=None, tu_id=-1, c_id=-1):
        """
        Constructor.

        :param uuid: universally unique id (string)

        :param tu_id: type id

        :param c_id: component id
        """
        super().__init__()
        self.tu_id = tu_id
        self.c_id = c_id
        self.uuid = uuid

    def is_empty(self):
        """
        Returns True if uuid is None. False otherwise.

        :return: bool
        """
        return self.uuid is None

    def __eq__(self, other):
        return self.uuid == other.uuid and \
               self.tu_id == other.tu_id and \
               self.c_id == other.c_id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        s = "<TuioSymbol uuid="+str(self.uuid)+" "
        s += "tu_id="+str(self.tu_id)+" c_id="+str(self.c_id)+">"
        return s

    def __repr__(self):
        return self.__str__()


class TuioPointer(TuioSessionElement):
    """
    Describes a ptr TuioSessionElement, which is defined by session id, user id, type id, component id, [x,y]-pos,
    rotation angle, shear factor, radius and pressed state.
    """

    tu_id_pointer = 0
    tu_id_pen = 1
    tu_id_eraser = 2

    def __init__(self, s_id=-1, u_id=-1, tu_id=-1, c_id=-1, x_pos=0.0, y_pos=0.0, angle=0.0, shear=0.0, radius=10.0, press=False):
        """
        Constructor.

        :param s_id: session id

        :param u_id: user id

        :param tu_id: type id (see TuioPointer.tu_id_pointer, TuioPointer.tu_id_pen, TuioPointer.tu_id_eraser)

        :param c_id: component id

        :param x_pos: x position

        :param y_pos: y position

        :param angle: rotation angle

        :param shear: shear factor

        :param radius: radius

        :param press: pressed state (bool)
        """
        super().__init__(s_id=s_id)
        self.tu_id = tu_id
        self.c_id = c_id
        self.u_id = u_id
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.angle = angle
        self.shear = shear
        self.radius = radius
        self.press = press

    def refresh_s_id(self):
        """
        Auto assign a new session id.

        :return: None
        """
        self.s_id = TuioSessionId.get()

    def key(self):
        """
        Return a key string for this instance. key is unique within the application.

        :return: str
        """
        return TuioPointer.calc_key(self.s_id, self.u_id, self.c_id)

    @staticmethod
    def calc_key(s_id, u_id, c_id):
        """
        Computes a key string from given values. format is: '<s_id>_<u_id>_<c_id>'

        :param s_id: session id

        :param u_id: user id

        :param c_id: component id

        :return: str
        """
        return str(s_id) + "_" + str(u_id) + "_" + str(c_id)

    def __eq__(self, other):
        return self.key() == other.key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        s = "<TuioPointer s_id="+str(self.s_id)+" "
        s += "u_id="+str(self.u_id)+" tu_id="+str(self.tu_id)+ " "
        s += "c_id="+str(self.c_id)+" x_pos="+str(self.x_pos)+ " "
        s += "y_pos="+str(self.y_pos)+" angle="+str(self.radius)+ " "
        s += "shear="+str(self.shear)+" radius="+str(self.radius)+ " "
        s += "press="+str(self.press)+">"
        return s

    def __repr__(self):
        return self.__str__()


class TuioImagePattern(TuioSessionElement):
    """
    Describes a composite TuioSessionElement, which is comprised of a TuioBounds and a TuioSymbol element. Additionally,
    it is identified by a session id and a user id.
    """

    def __init__(self, s_id=-1, bnd=None, sym=None, u_id=-1):
        """
        Constructor.

        :param s_id: session id

        :param bnd: TuioBounds

        :param sym: TuioSymbol

        :param u_id: user id
        """
        super().__init__(s_id=s_id)
        self._bnd = bnd
        if self._bnd is None:
            self._bnd = TuioBounds()
        self._sym = sym
        if self._sym is None:
            self._sym = TuioSymbol()
        self._u_id = u_id # user_id

    def key(self):
        """
        Calculates a key string from session id and user id which is unique within the application.

        :return: str
        """
        return TuioImagePattern.calc_key(self.s_id, self._u_id)

    @staticmethod
    def calc_key(s_id, u_id):
        """
        Calculates a key string from given session id and user id. Format is: '<s_id>_<u_id>'

        :param s_id: session id

        :param u_id: user id

        :return: str
        """
        return str(s_id) + "_" + str(u_id)

    def __str__(self):
        s = "<TuioPattern s_id="+str(self.s_id)+" "+"u_id="+str(self._u_id)+" "
        s += "bnd="+str(self._bnd)+" sym="+str(self._sym)+">"
        return s

    def __repr__(self):
        return self.__str__()

    def is_valid(self):
        """
        Returns True if sym and bnd of this instance are not empty. False otherwise.

        :return: bool
        """
        return not self._bnd.is_empty() and not self._sym.is_empty()

    def get_s_id(self):
        """
        Getter for session id

        :return: session id
        """
        return self.s_id

    def get_u_id(self):
        """
        Getter for user id

        :return: user id
        """
        return self._u_id

    def get_bnd(self):
        """
        Getter for bounds of this instance.

        :return: TuioBounds
        """
        return self._bnd

    def get_sym(self):
        """
        Getter for symbol identifier of this instance.

        :return: TuioSymbol
        """
        return self._sym

    def set_bnd(self, bnd):
        """
        Setter for bounds of this instance.

        :param bnd: TuioBounds

        :return: None
        """
        self._bnd = bnd

    def set_sym(self, sym):
        """
        Setter for symbol identifier of this instance.

        :param sym: TuioSymbol

        :return: None
        """
        self._sym = sym

    def set_x_pos(self, x_pos):
        """
        Setter for x position of bounds.

        :param x_pos: numeric value

        :return: None
        """
        self._bnd.x_pos = x_pos

    def set_y_pos(self, y_pos):
        """
        Setter for y position of bounds.

        :param y_pos: numeric value

        :return: None
        """
        self._bnd.y_pos = y_pos

    def set_angle(self, angle):
        """
        Set rotation angle of bounds.

        :param angle: numeric value

        :return: None
        """
        self._bnd.angle = angle

    def set_width(self, width):
        """
        Set width of bounds.

        :param width: numeric value

        :return: None
        """
        self._bnd.width = width

    def set_height(self, height):
        """
        Set height of bounds.

        :param height: numeric value

        :return: None
        """
        self._bnd.width = height

    def set_uuid(self, uuid):
        """
        Set uuid of symbol identifier.

        :param uuid: str

        :return: None
        """
        self._sym.uuid = uuid

    def set_tu_id(self, tu_id):
        """
        Set type id of symbol identifier.

        :param tu_id: int

        :return: None
        """
        self._sym.tu_id = tu_id

    def set_u_id(self, u_id):
        """
        Set user id.

        :param u_id: int

        :return: None
        """
        self._u_id = u_id

    def set_c_id(self, c_id):
        """
        Set component id of symbol identifier.

        :param c_id: int

        :return: None
        """
        self._sym.c_id = c_id