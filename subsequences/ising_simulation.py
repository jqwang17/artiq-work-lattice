from artiq.experiment import *
from artiq.coredevice.ad9910 import RAM_MODE_RAMPUP, RAM_DEST_ASF
from artiq.coredevice.ad9910 import PHASE_MODE_TRACKING, PHASE_MODE_ABSOLUTE
from subsequences.rabi_excitation import RabiExcitation
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

    ac_stark_detuning="IsingSimulation.ac_stark_detuning"
    ac_stark_pi_time="IsingSimulation.ac_stark_pi_time"
    ac_stark_amp="IsingSimulation.ac_stark_amp"
    ac_stark_att="IsingSimulation.ac_stark_att"
    ac_stark_line_selection="IsingSimulation.ac_stark_line_selection"

    transverse_field_sp_amp_729="IsingSimulation.transverse_field_sp_amp"
    transverse_field_sp_att_729="IsingSimulation.transverse_field_sp_att"

    default_sp_amp_729="Excitation_729.single_pass_amplitude"
    default_sp_att_729="Excitation_729.single_pass_att"

    duration="IsingSimulation.simulation_time"
    fast_noise_fraction="IsingSimulation.fast_noise_fraction"
    slow_noise_fraction="IsingSimulation.slow_noise_fraction"
    parameter_miscalibration_fraction="IsingSimulation.parameter_miscalibration_fraction"
    active_crosstalk_fraction="IsingSimulation.active_crosstalk_fraction"
    idle_crosstalk_fraction="IsingSimulation.idle_crosstalk_fraction"

    disable_coupling_term="IsingSimulation.disable_coupling_term"
    disable_transverse_term="IsingSimulation.disable_transverse_term"

    phase_ref_time=np.int64(-1)
    use_ramping=False
    reverse=False
    alternate_basis=False

    def add_child_subsequences(pulse_sequence):
        s = IsingSimulation
        s.rabi = pulse_sequence.add_subsequence(RabiExcitation)

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
        pulse_sequence.get_729_dds("729G")
        pulse_sequence.prepare_pulse_with_amplitude_ramp(
            pulse_duration=s.duration,
            ramp_duration=1*us,
            dds1_amp=s.amp)
        pulse_sequence.prepare_noisy_single_pass(freq_noise=False)

    @kernel
    def rz_pi_2_pulse(self, phase=0.):
        s = IsingSimulation
        s.rabi.channel_729 = "729G"
        s.rabi.duration = s.ac_stark_pi_time / 2.
        s.rabi.amp_729 = s.ac_stark_amp
        s.rabi.att_729 = s.ac_stark_att
        s.rabi.freq_729 = self.calc_frequency(
            s.ac_stark_line_selection,
            detuning=s.ac_stark_detuning,
            dds=s.rabi.channel_729
        )
        s.rabi.phase_729 = phase
        s.rabi.phase_ref_time = s.phase_ref_time
        s.rabi.run(self)

    def subsequence(self):
        s = IsingSimulation

        if not s.use_ramping:
            raise Exception("Must call setup_ramping before running subsequence")

        # TODO_RYAN: Implement s.slow_noise_fraction
        # TODO_RYAN: Implement s.parameter_miscalibration_fraction
        # TODO_RYAN: Implement s.active_crosstalk_fraction
        # TODO_RYAN: Implement s.idle_crosstalk_fraction

        if s.alternate_basis:
            # global z-rotation by pi/2 via AC stark shift
            s.rz_pi_2_pulse(self)

        ms_detuning = s.detuning
        if s.reverse:
            ms_detuning = -ms_detuning

        phase_blue = 0.
        phase_transverse = 0.
        if s.alternate_basis:
            # MS term: implement sigma_y sigma_y instead of sigma_x sigma_x
            phase_blue = 180.
            # transverse field term: implement sigma_x instead of sigma_y
            phase_transverse = 90.

        dp_freq = self.calc_frequency(
            s.line_selection,
            detuning=s.detuning_carrier_1,
            dds="729G"
        )

        trap_frequency = self.get_trap_frequency(s.selection_sideband)
        freq_red = 80*MHz - trap_frequency - ms_detuning
        freq_blue = 80*MHz + trap_frequency + ms_detuning

        self.get_729_dds("729G")
        offset = self.get_offset_frequency("729G")
        freq_blue += offset
        freq_red += offset

        # Set double-pass to correct frequency and phase,
        # and set amplitude to zero for now.
        self.dds_729.set(dp_freq, amplitude=0., phase=s.phase / 360, ref_time_mu=s.phase_ref_time)

        self.dds_729_SP.set(freq_blue, amplitude=0., ref_time_mu=s.phase_ref_time)
        self.dds_729_SP.set_att(s.att_blue)
        self.dds_729_SP_bichro.set(freq_red, amplitude=0., ref_time_mu=s.phase_ref_time)
        self.dds_729_SP_bichro.set_att(s.att_red)

        if not s.disable_coupling_term:
            # Enable the blue and red DDS for the MS term
            self.start_noisy_single_pass(s.phase_ref_time,
                freq_sp=freq_blue, amp_sp=s.amp_blue, att_sp=s.att_blue, phase_sp=phase_blue / 360,
                use_bichro=True,
                freq_sp_bichro=freq_red, amp_sp_bichro=s.amp_red, att_sp_bichro=s.att_red)

        if not s.disable_transverse_term:
            # Enable the carrier DDS for the transverse field term
            # NOTE: This requires the SP_729L2 channel to be mixed with the SP_729G and SP_729G_bichro channels
            #       with all three channels going to the single-pass AOM for the global 729 beam.
            sp_freq_729_carrier = 80*MHz + self.get_offset_frequency("729G")
            self.dds_SP_729L2.set(sp_freq_729_carrier, amplitude=s.transverse_field_sp_amp_729,
                phase=phase_transverse / 360, ref_time_mu=s.phase_ref_time)
            self.dds_SP_729L2.set_att(s.transverse_field_sp_att_729)
            self.dds_SP_729L2.sw.on()

        # Pulse the double-pass DDS for the appropriate duration
        self.execute_pulse_with_amplitude_ramp(dds1_att=s.att, dds1_freq=dp_freq)

        self.stop_noisy_single_pass(use_bichro=True)
        self.dds_SP_729L2.sw.off()

        if s.alternate_basis:
            # global z-rotation by -pi/2 via AC stark shift
            s.rz_pi_2_pulse(self, phase=180.)
