############
# Standard #
############
from collections import OrderedDict, ChainMap
###############
# Third Party #
###############
import numpy as np
from bluesky.examples import Mover, Reader
from ophyd.ophydobj import OphydObject

##########
# Module #
##########


class OneMirrorSystem(object):
    """
    System of a source, mirror and an imager.
    """
    def __init__(self, **kwargs):
        self._x0 = kwargs.get("x0", 0)
        self._xp0 = kwargs.get("xp0", 0)
        self._x1 = kwargs.get("x1", 0)
        self._d1 = kwargs.get("d1", 90.510)
        self._a1 = kwargs.get("a1", 0.0014)
        self._x2 = kwargs.get("x2", 0.0317324)
        self._d2 = kwargs.get("d2", 101.843)
        self._noise_x0 = kwargs.get("noise_x0", 0)
        self._noise_xp0 = kwargs.get("noise_xp0", 0)
        self._noise_x1 = kwargs.get("noise_x1", 0)
        self._noise_d1 = kwargs.get("noise_d1", 0)
        self._noise_a1 = kwargs.get("noise_a1", 0)
        self._noise_x2 = kwargs.get("noise_x2", 0)
        self._noise_d2 = kwargs.get("noise_d2", 0)
        self._fake_sleep_s_x = kwargs.get("fake_sleep_s_x", 0)
        self._fake_sleep_s_xp = kwargs.get("fake_sleep_s_xp", 0)
        self._fake_sleep_m1_x = kwargs.get("fake_sleep_m1_x", 0)
        self._fake_sleep_m1_z = kwargs.get("fake_sleep_m1_z", 0)
        self._fake_sleep_m1_alpha = kwargs.get("fake_sleep_m1_alpha", 0)
        self._fake_sleep_y1_x = kwargs.get("fake_sleep_y1_x", 0)
        self._fake_sleep_y1_z = kwargs.get("fake_sleep_y1_z", 0)
        self._name_s = kwargs.get("name_s", "Source")
        self._name_m1 = kwargs.get("name_m1", "Mirror 1")
        self._name_y1 = kwargs.get("name_y1", "YAG 1")
        self._pix_y1 = kwargs.get("pix_y1", (1392, 1040))
        self._size_y1 = kwargs.get("size_y1", (0.0076, 0.0062))
        self._invert_y1 = kwargs.get("invert_y1", False)

        self.source = Source(self._name_s, self._x0, self._xp0,
                             noise_x=self._noise_x0, noise_xp=self._noise_xp0,
                             fake_sleep_x=self._fake_sleep_s_x,
                             fake_sleep_xp=self._fake_sleep_s_xp)

        self.mirror_1 = Mirror(self._name_m1, self._x1, self._d1, self._a1,
                               noise_x=self._noise_x1,
                               noise_alpha=self._noise_a1,
                               fake_sleep_x=self._fake_sleep_m1_x,
                               fake_sleep_z=self._fake_sleep_m1_z,
                               fake_sleep_alpha=self._fake_sleep_m1_alpha)

        self.yag_1 = YAG(self._name_y1, self._x2, self._d2, self._noise_x2,
                         self._noise_d2, pix=self._pix_y1, size=self._size_y1,
                         fake_sleep_x=self._fake_sleep_y1_x,
                         fake_sleep_z=self._fake_sleep_y1_z)

        def calc_cent_x():
            x = OneBounce(self.mirror_1.read()['alpha']['value'],
                          self.source.read()['x']['value'],
                          self.source.read()['xp']['value'],
                          self.mirror_1.read()['x']['value'],
                          self.mirror_1.read()['z']['value'],
                          self.yag_1.read()['z']['value'])
            return np.floor(self.yag_1.pix[0]/2) + (1 - 2*self._invert_y1) * \
                (x - self.x2)*self.yag_1.pix[0]/self.yag_1.size[0]

        self.yag_1.cent_x = calc_cent_x


def OneBounce(a1, x0, xp0, x1, d1, d2):
    return -2*a1*d1 + 2*a1*d2 - d2*xp0 + 2*x1 - x0


def TwoBounce(alphas, x0, xp0, x1, d1, x2, d2, d3):
    return 2*alphas[0]*d1 - 2*alphas[0]*d3 - 2*alphas[1]*d2 \
        + 2*alphas[1]*d3 + d3*xp0 - 2*x1 + 2*x2 + x0


class Source(object):
    """
    Simulation of the photon source (simplified undulator).
    """
    def __init__(self, name, x, xp, noise_x, noise_xp, fake_sleep_x=0,
                 fake_sleep_xp=0):
        self.name = name
        self.noise_x = noise_x
        self.noise_xp = noise_xp
        self.fake_sleep_x = fake_sleep_x
        self.fake_sleep_xp = fake_sleep_xp
        self.x = Mover('X Motor', OrderedDict(
                [('x', lambda x: x + np.random.uniform(-1, 1)
                  * self.noise_x),
                 ('x_setpoint', lambda x: x)]), {'x': x})
        self.xp = Mover('XP Motor', OrderedDict(
                [('xp', lambda xp: xp + np.random.uniform(-1, 1)
                  * self.noise_xp),
                 ('xp_setpoint', lambda xp: xp)]), {'xp': xp})
        self.motors = [self.x, self.xp]

    def read(self):
        return dict(ChainMap(*[motor.read() for motor in self.motors]))

    def set(self, **kwargs):
        for key in kwargs.keys():
            for motor in self.motors:
                if key in motor.read():
                    motor.set(kwargs[key])


class Mirror(object):
    """
    Simulation of the Flat Mirror Pitch

    Parameters
    ----------
    name : string
        Name of motor

    x: float
        Initial x position of the motor in meters from nominal

    z: float
        Distance of the mirror from the source in meters

    alpha: float
        Initial pitch of motor in microradians

    noise_x: float, optional
        Scaler to multiply uniform noise on x

    noise_z: float, optional
        Scaler to multiply uniform noise on z

    noise_alpha: float, optional
        Scaler to multiply uniform noise on alpha

    fake_sleep_x: float, optional
        Simulate moving time in x

    fake_sleep_z: float, optional
        Simulate moving time in z

    fake_sleep_alpha: float, optional
        Simulate moving time in alpha
    """
    def __init__(self, name, x, z, alpha, noise_x=0, noise_z=0,
                 noise_alpha=0, fake_sleep_x=0, fake_sleep_z=0,
                 fake_sleep_alpha=0):
        self.name = name
        self.noise_x = noise_x
        self.noise_z = noise_z
        self.noise_alpha = noise_alpha
        self.fake_sleep_x = fake_sleep_x
        self.fake_sleep_z = fake_sleep_z
        self.fake_sleep_alpha = fake_sleep_alpha

        self.x = Mover('X Motor', OrderedDict(
                [('x', lambda x: x + np.random.uniform(-1, 1)*self.noise_x),
                 ('x_setpoint', lambda x: x)]), {'x': x},
                       fake_sleep=self.fake_sleep_x)
        self.z = Mover('Z Motor', OrderedDict(
                [('z', lambda z: z + np.random.uniform(-1, 1)*self.noise_z),
                 ('z_setpoint', lambda z: z)]), {'z': z},
                       fake_sleep=self.fake_sleep_z)
        self.alpha = Mover('Alpha Motor', OrderedDict(
                [('alpha', lambda alpha: alpha +
                  np.random.uniform(-1, 1)*self.noise_alpha),
                 ('alpha_setpoint', lambda alpha: alpha)]), {'alpha': alpha},
                           fake_sleep=self.fake_sleep_alpha)
        self.motors = [self.x, self.z, self.alpha]

    def read(self):
        return dict(ChainMap(*[motor.read() for motor in self.motors]))

    def set(self, cmd=None, **kwargs):
        if cmd in ("IN", "OUT"):
            pass  # If these were removable we'd implement it here
        for key in kwargs.keys():
            for motor in self.motors:
                if key in motor.read():
                    motor.set(kwargs[key])

    @property
    def blocking(self):
        return False

    def subscribe(self, *args, **kwargs):
        pass


class YAG(Reader, OphydObject):
    """
    Simulation of a YAG

    Parameters
    ----------
    name : str
        Alias of YAG

    x: float
        Initial x position of the motor in meters from nominal

    z: float
        Distance of the mirror from the source in meters

    noise_x: float, optional
        Scaler to multiply uniform noise on x

    noise_z: float, optional
        Scaler to multiply uniform noise on z

    fake_sleep_x: float, optional
        Simulate moving time in x

    fake_sleep_y: float, optional
        Simulate moving time in y

    fake_sleep_z: float, optional
        Simulate moving time in z

    **kwargs:
        pix: (int, int)
            Size of the image in pixels
        size: (float, float)
            Size of the image in meters
    """
    SUB_VALUE = "value"
    _default_sub = SUB_VALUE

    def __init__(self, name, x, z, noise_x=0, noise_z=0, fake_sleep_x=0,
                 fake_sleep_y=0, fake_sleep_z=0, **kwargs):

        self.name = name
        self.noise_x = noise_x
        self.noise_z = noise_z

        self.fake_sleep_x = fake_sleep_x
        self.fake_sleep_z = fake_sleep_z

        self.x = Mover('X Motor', OrderedDict(
                [('x', lambda x: x + np.random.uniform(-1, 1)*self.noise_x),
                 ('x_setpoint', lambda x: x)]), {'x': x},
                       fake_sleep=self.fake_sleep_x)
        self.z = Mover('Z Motor', OrderedDict(
                [('z', lambda z: z + np.random.uniform(-1, 1)*self.noise_z),
                 ('z_setpoint', lambda z: z)]), {'z': z},
                       fake_sleep=self.fake_sleep_z)
        self.motors = [self.x, self.z]

        self.pix = kwargs.get("pix", (1392, 1040))
        self.size = kwargs.get("size", (0.0076, 0.0062))

        self.y_state = "OUT"

        def cent_x():
            return np.floor(self.pix[0]/2)

        def cent_y():
            return np.floor(self.pix[1]/2)

        def cent():
            return (cent_x(), cent_y())

        super().__init__(self.name, {'centroid_x': cent_x,
                                     'centroid_y': cent_y,
                                     'centroid': cent})
        OphydObject.__init__(self)  # Reader doesn't call super().__init__

    def read(self):
        # TODO: Roll the centroid data into this large dict, rather than it
        # just containing motor information
        return dict(ChainMap(*[motor.read() for motor in self.motors]))

    def set(self, cmd=None, **kwargs):
        if cmd == "OUT":
            self.y_state = "OUT"
        elif cmd == "IN":
            self.y_state = "IN"
        if cmd is not None:
            self._run_subs(self.y_state, sub_type=self.SUB_VALUE)

        for key in kwargs.keys():
            for motor in self.motors:
                if key in motor.read():
                    motor.set(kwargs[key])

    @property
    def blocking(self):
        return self.y_state == "IN"


if __name__ == "__main__":
    sys = OneMirrorSystem()
    m = sys.mirror_1
    print("x: ", m.read()['x']['value'])
    m.set(x=10)
    print("x: ", m.read()['x']['value'])
    import IPython
    IPython.embed()
    # print("Centroid:", system.yag_1.read()['centroid_x']['value'])
