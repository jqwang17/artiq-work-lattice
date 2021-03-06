import numpy as np
from datetime import datetime
from pulse_sequence import PulseSequence, FitError
from scipy.optimize import curve_fit
from subsequences.rabi_excitation import RabiExcitation
from subsequences.state_preparation import StatePreparation
from artiq.experiment import *
import traceback

class HeatingRate(PulseSequence):
    PulseSequence.accessed_params = {
        "CalibrationScans.calibration_channel_729",
        "CalibrationScans.sideband_calibration_amp",
        "CalibrationScans.sideband_calibration_att",
        "CalibrationScans.selection_sideband",
        "CalibrationScans.order",
        "Spectrum.manual_excitation_time",
        "CalibrationScans.sideband_calibration_line",
        "Display.relative_frequencies",
        "CalibrationScans.readout_mode",
        "Heating.background_heating_time",
    }
    
    master_scans = [("Heating.background_heating_time", 0., 100e-3, 20, "ms")]

    PulseSequence.scan_params.update(
            CalibRed=[("CalibRed", ("Spectrum.sideband_detuning", -5e3, 5e3, 15, "kHz"))],
            CalibBlue=[("CalibBlue", ("Spectrum.sideband_detuning", -5e3, 5e3, 15, "kHz"))]
    )

    def run_initially(self):
        self.stateprep = self.add_subsequence(StatePreparation)
        self.rabi = self.add_subsequence(RabiExcitation)
        self.rabi.channel_729 = self.p.CalibrationScans.calibration_channel_729
        self.kernel_invariants.update({"sideband"})
        self.sideband = self.p.CalibrationScans.selection_sideband
        self.set_subsequence["CalibRed"] = self.set_subsequence_calibred
        self.set_subsequence["CalibBlue"] = self.set_subsequence_calibblue
        self.wait_time = 0.
        self.red_amps = list()
        self.blue_amps = list()
        self.wait_times = list()
        self.nbars = list()
        self.run_after["CalibRed"] = self.analyze_calibred
        self.run_after["CalibBlue"] = self.analyze_calibblue
        self.plotname = "HeatingRate-" + str(datetime.now().strftime("%H%M_%S"))
        assert int(self.p.CalibrationScans.order) == self.p.CalibrationScans.order, "SB order needs to be int"

    @kernel
    def set_subsequence_calibred(self):
        delta = self.get_variable_parameter("Spectrum_sideband_detuning")
        rabi_line = self.CalibrationScans_sideband_calibration_line
        rabi_dds = self.CalibrationScans_calibration_channel_729
        self.rabi.amp_729 = self.CalibrationScans_sideband_calibration_amp
        self.rabi.att_729 = self.CalibrationScans_sideband_calibration_att
        self.rabi.duration = self.Spectrum_manual_excitation_time
        self.rabi.freq_729 = self.calc_frequency(
                rabi_line, delta, sideband=self.sideband, 
                order=-abs(self.CalibrationScans_order), dds=rabi_dds,
                bound_param="Spectrum_sideband_detuning"
            )
    
    @kernel
    def set_subsequence_calibblue(self):
        delta = self.get_variable_parameter("Spectrum_sideband_detuning")
        rabi_line = self.CalibrationScans_sideband_calibration_line
        rabi_dds = self.CalibrationScans_calibration_channel_729
        self.rabi.amp_729 = self.CalibrationScans_sideband_calibration_amp
        self.rabi.att_729 = self.CalibrationScans_sideband_calibration_att
        self.rabi.duration = self.Spectrum_manual_excitation_time
        self.rabi.freq_729 = self.calc_frequency(
                rabi_line, delta, sideband=self.sideband, 
                order=abs(self.CalibrationScans_order), dds=rabi_dds,
                bound_param="Spectrum_sideband_detuning"
            )

    @kernel
    def CalibRed(self):
        self.stateprep.run(self)
        delay(self.Heating_background_heating_time)
        self.rabi.run(self)

    def analyze_calibred(self):
        y = self.data.CalibRed.y[-1]
        x = self.data.CalibRed.x
        global_max = x[np.argmax(y)]
        try:
            popt, pcov = curve_fit(gaussian, x, y, p0=[0.5, global_max, 500.0])
            self.red_amps.append(popt[0])
            print("red_amp:", popt[0])
        except:
            self.red_amps.append(np.nan)
            raise FitError
        if len(self.red_amps) == len(self.blue_amps):
            try:
                R = self.red_amps[-1] / self.blue_amps[-1]
                nbar = R / (1 - R) if R < 1 else -1
                self.nbars.append(nbar)
                self.wait_times.append(self.p.Heating.background_heating_time)
                self.rcg.plot(self.wait_times, self.nbars, tab_name="CalibSidebands",
                        plot_name="nbar", append=True,
                        plot_title=self.plotname)
                self.manual_save(self.wait_times, self.nbars, name=self.plotname,
                        plot_window="nbar", xlabel="heating_time", ylabel="nbar")
            except Exception as e:
                print("\n"*10)
                traceback.print_exc()

    @kernel
    def CalibBlue(self):
        self.stateprep.run(self)
        delay(self.Heating_background_heating_time)
        self.rabi.run(self)

    def analyze_calibblue(self):
        y = self.data.CalibBlue.y[-1]
        x = self.data.CalibBlue.x
        global_max = x[np.argmax(y)]
        if np.max(y) < 0.1:
            raise FitError
        try:
            popt, pcov = curve_fit(gaussian, x, y, p0=[0.5, global_max, 500.0])
            self.blue_amps.append(popt[0])
            print("blue_amp:", popt[0])
        except:
            self.blue_amps.append(np.nan)
            raise FitError
        if len(self.red_amps) == len(self.blue_amps):
            try:
                R = self.red_amps[-1] / self.blue_amps[-1]
                nbar = R / (1 - R) if R < 1 else -1
                self.nbars.append(nbar)
                self.wait_times.append(self.p.Heating.background_heating_time)
                self.rcg.plot(self.wait_times, self.nbars, tab_name="CalibSidebands",
                        plot_name="nbar", append=True,
                        plot_title=self.plotname)
                self.manual_save(self.wait_times, self.nbars, name=self.plotname,
                        plot_window="nbar", xlabel="heating_time", ylabel="nbar")
            except Exception as e:
                print("\n"*10)
                traceback.print_exc()

def gaussian(x, A, x0, sigma):
    return A * np.exp((-(x - x0)**2) / (2*sigma**2))
