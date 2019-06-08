from artiq.experiment import *


class RampTest(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.dds = self.get_device("SP_729L1")
        self.cpld = self.get_device("urukul2_cpld")

    @kernel
    def run(self):
        self.core.reset()
        self.cpld.init()
        self.dds.init()
        self.core.break_realtime()

        self.dds.set(80*MHz, amplitude=1)
        self.dds.set_att(5*dB)

        self.dds.sw.on()
        delay(1*ms)
        self.dds.sw.off()
