from artiq.experiment import *
from artiq.coredevice.ad9910 import RAM_MODE_RAMPUP, RAM_DEST_ASF
from artiq.coredevice.ad9910 import PHASE_MODE_TRACKING, PHASE_MODE_ABSOLUTE
import numpy as np


class IsingSimulation:
    amp_blue="MolmerSorensen.amp_blue"
    att_blue="MolmerSorensen.att_blue"
    amp_red="MolmerSorensen.amp_red"
    att_red="MolmerSorensen.att_red"
    amp="MolmerSorensen.amplitude"
    att="MolmerSorensen.att"
    phase="MolmerSorensen.phase"
    line_selection="MolmerSorensen.line_selection"
    selection_sideband="MolmerSorensen.selection_sideband"
    detuning="MolmerSorensen.detuning"
    detuning_carrier_1="MolmerSorensen.detuning_carrier_1"
    detuning_carrier_2="MolmerSorensen.detuning_carrier_2"

    ac_stark_detuning = "Benchmarking.ac_stark_detuning"

    default_sp_amp_729="Excitation_729.single_pass_amplitude"
    default_sp_att_729="Excitation_729.single_pass_att"

    duration="Benchmarking.simulation_time"
    fast_noise_fraction="Benchmarking.fast_noise_fraction"
    slow_noise_fraction="Benchmarking.slow_noise_fraction"
    parameter_miscalibration_fraction="Benchmarking.parameter_miscalibration_fraction"
    crosstalk_fraction="Benchmarking.crosstalk_fraction"
    control_leakage_fraction="Benchmarking.control_leakage_fraction"

    phase_ref_time=np.int64(-1)
    use_ramping=False
    reverse=False
    alternate_basis=False
    disable_coupling_term=False
    disable_transverse_term=False

    def add_child_subsequences(pulse_sequence):
        s = IsingSimulation

    def setup_noisy_single_pass(pulse_sequence):
        s = IsingSimulation
        # TODO_RYAN: Generate the correct type of noisy waveform here
        pulse_sequence.generate_single_pass_noise_waveform(
            mean=s.amp_blue,
            std=s.fast_noise_fraction * s.amp_blue,
            freq_noise=False)

    @kernel
    def setup_ramping(pulse_sequence):
        s = IsingSimulation
        s.use_ramping = True
        self.get_729_dds("729G")
        pulse_sequence.prepare_pulse_with_amplitude_ramp(
            pulse_duration=s.duration,
            ramp_duration=1*us,
            dds1_amp=s.amp)
        pulse_sequence.prepare_noisy_single_pass(freq_noise=False)

    def subsequence(self):
        s = IsingSimulation

        if not s.use_ramping:
            raise AssertionError("Must call setup_ramping before running subsequence")

        # TODO_RYAN: Implement s.slow_noise_fraction
        # TODO_RYAN: Implement s.parameter_miscalibration_fraction
        # TODO_RYAN: Implement s.crosstalk_fraction
        # TODO_RYAN: Implement s.control_leakage_fraction

        ac_stark_detuning = s.ac_stark_detuning
        if alternate_basis:
            # TODO_RYAN: global z-rotation by pi/2 via AC stark shift

        ms_detuning = s.detuning
        ac_stark_detuning = s.ac_stark_detuning
        if s.reverse:
            ms_detuning = -ms_detuning
            ac_stark_detuning = -ac_stark_detuning

        if s.disable_transverse_term:
            ac_stark_detuning = 0.

        phase_blue = 0.
        if s.alternate_basis:
            phase_blue = 180.

        if not s.disable_coupling_term:
            trap_frequency = self.get_trap_frequency(s.selection_sideband)
            freq_red = 80*MHz - trap_frequency - ms_detuning
            freq_blue = 80*MHz + trap_frequency + ms_detuning + ac_stark_detuning # TODO_RYAN: Is adding ac_stark_detuning here correct?

            self.get_729_dds("729G")
            offset = self.get_offset_frequency("729G")
            freq_blue += offset
            freq_red += offset

            # Set double-pass to correct frequency and phase,
            # and set amplitude to zero for now.
            dp_freq = self.calc_frequency(
                s.line_selection,
                detuning=s.detuning_carrier_1,
                dds="729G"
            )
            self.dds_729.set(dp_freq, amplitude=0., phase=s.phase / 360, ref_time_mu=s.phase_ref_time)

            self.dds_729_SP.set(freq_blue, amplitude=0., ref_time_mu=s.phase_ref_time)
            self.dds_729_SP.set_att(s.att_blue)
            self.dds_729_SP_bichro.set(freq_red, amplitude=0., ref_time_mu=s.phase_ref_time)
            self.dds_729_SP_bichro.set_att(s.att_red)

            self.start_noisy_single_pass(s.phase_ref_time,
                freq_sp=freq_blue, amp_sp=s.amp_blue, att_sp=s.att_blue, phase_sp=phase_blue / 360,
                use_bichro=True,
                freq_sp_bichro=freq_red, amp_sp_bichro=s.amp_red, att_sp_bichro=s.att_red)

            self.execute_pulse_with_amplitude_ramp(dds1_att=s.att, dds1_freq=dp_freq)

            self.stop_noisy_single_pass(use_bichro=True)

        else if not s.disable_transverse_term:
            # Implement only the ac stark shift here
            self.dds_729.set(dp_freq + ac_stark_detuning, amplitude=s.amp, phase=s.phase / 360, ref_time_mu=s.phase_ref_time)
            self.dds_729.set_att(s.att)

            sp_freq_729 = 80*MHz + self.get_offset_frequency("729G")
            self.start_noisy_single_pass(s.phase_ref_time,
                freq_sp=sp_freq_729, amp_sp=s.default_sp_amp_729, att_sp=s.default_sp_att_729)

            self.dds_729.sw.on()
            delay(s.duration)
            self.dds_729.sw.off()

            self.stop_noisy_single_pass()

        if alternate_basis:
            # TODO_RYAN: global rotation by -pi/2 via AC stark shift
            pass
