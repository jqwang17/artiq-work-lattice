from pulse_sequence import PulseSequence
from subsequences.repump_D import RepumpD
from subsequences.doppler_cooling import DopplerCooling
from subsequences.optical_pumping_pulsed import OpticalPumpingPulsed
from subsequences.rabi_excitation import RabiExcitation
from subsequences.sideband_cooling import SidebandCooling
from artiq.experiment import *


class Ramsey(PulseSequence):
    PulseSequence.accessed_params.update(
        {"Ramsey.wait_time",
         "Ramsey.phase",
         "Ramsey.selection_sideband",
         "Ramsey.order",
         "Ramsey.channel_729",
         "Ramsey.detuning",
         "Rotation729L1.pi_time",
         "Rotation729L1.line_selection",
         "Rotation729L1.amplitude",
         "Rotation729L1.att",
         "Rotation729L2.pi_time",
         "Rotation729L2.line_selection",
         "Rotation729L2.amplitude",
         "Rotation729L2.att",
         "Rotation729G.pi_time",
         "Rotation729G.line_selection",
         "Rotation729G.amplitude",
         "Rotation729G.att",
         }
    )

    PulseSequence.scan_params["Ramsey"] = ("Ramsey",
        [("Ramsey.wait_time", 0*ms, 5*ms, 100, "ms"),
         ("Ramsey.phase", 0., 360., 20, "deg")]
    )

    def run_initially(self):
        self.repump854 = self.add_subsequence(RepumpD)
        self.dopplerCooling = self.add_subsequence(DopplerCooling)
        self.opc = self.add_subsequence(OpticalPumpingPulsed)
        self.sbc = self.add_subsequence(SidebandCooling)
        self.rabi = self.add_subsequence(RabiExcitation)
        self.set_subsequence["Ramsey"] = self.set_subsequence_ramsey
        if self.p.Ramsey.channel_729 == "729L1":
            self.pi_time = self.Rotation729L1.pi_time
            self.line_selection = self.Rotation729L1.line_selection
            self.amplitude = self.Rotation729L1.amplitude
            self.att = self.Rotation729L1.att
        elif self.p.Ramsey.channel_729 == "729L2":
            self.pi_time = self.Rotation729L2.pi_time
            self.line_selection = self.Rotation729L2.line_selection
            self.amplitude = self.Rotation729L2.amplitude
            self.att = self.Rotation729L2.att
        elif self.p.Ramsey.channel_729 == "729G":
            self.pi_time = self.Rotation729G.pi_time
            self.line_selection = self.Rotation729G.line_selection
            self.amplitude = self.Rotation729G.amplitude
            self.att = self.Rotation729G.att

    @kernel
    def set_subsequence_ramsey(self):
        self.rabi.duration = self.pi_time
        self.rabi.amp_729 = self.amplitude
        self.rabi.att_729 = self.att
        self.rabi.freq_729 = self.calc_frequency(
            self.line_selection, 
            detuning=self.Ramsey_detuning,
            sideband=self.Ramsey_selection_sideband,
            order=self.Ramsey_order, 
            dds=self.Ramsey_channel_729
        )

    @kernel
    def Ramsey(self):
        delay(1*ms)
        self.repump854.run(self)
        self.dopplerCooling.run(self)
        self.opc.run(self)
        if self.StatePreparation_sideband_cooling_enable:
            self.sbc.run(self)
        self.rabi.run(self)
        delay(self.Ramsey_wait_time)
        self.rabi.phase_729 = self.Ramsey_phase * 0.01745329251
        self.rabi.run(self)