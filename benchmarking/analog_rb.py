from pulse_sequence import PulseSequence
from subsequences.state_preparation import StatePreparation
from subsequences.rabi_excitation import RabiExcitation
from subsequences.ising_simulation import IsingSimulation
import numpy as np
import pickle
import os
from artiq.experiment import *

# This sequence implements analog randomized benchmarking protocol for
# an analog simulation involving a Molmer-Sorensen interaction and a single-ion
# AC stark shift.
# It also implements amplitude noise on the two parameters, such that when
# increasing the noise, the result should be a decrease in the population that
# ends up in the initial state.

class AnalogRB(PulseSequence):
    PulseSequence.accessed_params = {
        "AnalogBenchmarking.sequence_number",
        "AnalogBenchmarking.fast_noise_fraction",
        "AnalogBenchmarking.slow_noise_fraction",
        "AnalogBenchmarking.parameter_miscalibration_fraction",
        "AnalogBenchmarking.crosstalk_fraction",
        "AnalogBenchmarking.control_leakage_fraction",
        "AnalogBenchmarking.global_pi_time",
        "AnalogBenchmarking.global_amp",
        "AnalogBenchmarking.global_att",
        "AnalogBenchmarking.global_line_selection",
        "AnalogBenchmarking.local_pi_time",
        "AnalogBenchmarking.local_amp",
        "AnalogBenchmarking.local_att",
        "AnalogBenchmarking.local_line_selection",
    }

    PulseSequence.scan_params.update(
        AnalogRB=[
            ("Benchmarking", ("AnalogBenchmarking.sequence_number", 1, 200, 200)),
            ("Benchmarking", ("AnalogBenchmarking.fast_noise_fraction", 0., 0.5, 11)),
            ("Benchmarking", ("AnalogBenchmarking.slow_noise_fraction", 0., 0.5, 11)),
            ("Benchmarking", ("AnalogBenchmarking.parameter_miscalibration_fraction", 0., 0.5, 11)),
            ("Benchmarking", ("AnalogBenchmarking.crosstalk_fraction", 0., 0.5, 11)),
            ("Benchmarking", ("AnalogBenchmarking.control_leakage_fraction", 0., 0.5, 11)),
        ]
    )

    def run_initially(self):
        self.stateprep = self.add_subsequence(StatePreparation)
        self.rabi = self.add_subsequence(RabiExcitation)
        self.simulation = self.add_subsequence(IsingSimulation)
        self.simulation.setup_noisy_single_pass(self)
        self.phase_ref_time = np.int64(0)
        self.sequence_number = 1
        self.set_subsequence["AnalogRB"] = self.set_subsequence_benchmarking

        # load pickle files with analog RB sequences, initial states, and final states
        benchmarking_dir = os.path.join(os.path.expanduser("~"), "artiq-work", "benchmarking")
        self.sequences_enable_0 = pickle.load(open(os.path.join(benchmarking_dir, "analog_rb_sequences_enable_0.pickle"), "rb"))
        self.sequences_enable_1 = pickle.load(open(os.path.join(benchmarking_dir, "analog_rb_sequences_enable_1.pickle"), "rb"))
        self.sequences_t_step = pickle.load(open(os.path.join(benchmarking_dir, "analog_rb_sequences_t_step.pickle"), "rb"))
        self.sequences_reverse_step = pickle.load(open(os.path.join(benchmarking_dir, "analog_rb_sequences_reverse_step.pickle"), "rb"))
        self.initial_states = pickle.load(open(os.path.join(benchmarking_dir, "analog_rb_initial_states.pickle"), "rb"))
        self.final_states = pickle.load(open(os.path.join(benchmarking_dir, "analog_rb_final_states.pickle"), "rb"))

    @kernel
    def set_subsequence_benchmarking(self):
        self.sequence_number = int(self.get_variable_parameter("AnalogBenchmarking_sequence_number") - 1)
        self.simulation.duration = self.sequences_t_step[self.sequence_number][0]
        self.simulation.fast_noise_fraction = self.get_variable_parameter("AnalogBenchmarking_fast_noise_fraction")
        self.simulation.slow_noise_fraction = self.get_variable_parameter("AnalogBenchmarking_slow_noise_fraction")
        self.simulation.parameter_miscalibration_fraction = self.get_variable_parameter("AnalogBenchmarking_parameter_miscalibration_fraction")
        self.simulation.crosstalk_fraction = self.get_variable_parameter("AnalogBenchmarking_crosstalk_fraction")
        self.simulation.control_leakage_fraction = self.get_variable_parameter("AnalogBenchmarking_control_leakage_fraction")
        self.simulation.setup_ramping(self)

    @kernel
    def global_pi_pulse(self, phase=0.):
        self.rabi.channel_729 = "729G"
        self.rabi.duration = self.AnalogBenchmarking_global_pi_time
        self.rabi.amp_729 = self.AnalogBenchmarking_global_amp
        self.rabi.att_729 = self.AnalogBenchmarking_global_att
        self.rabi.freq_729 = self.calc_frequency(
            self.AnalogBenchmarking_global_line_selection,
            dds=self.rabi.channel_729
        )
        self.rabi.phase_729 = phase
        self.rabi.run(self)

    @kernel
    def local_pi_pulse(self, phase=0.):
        self.rabi.channel_729 = "729L1"
        self.rabi.duration = self.AnalogBenchmarking_local_pi_time
        self.rabi.amp_729 = self.AnalogBenchmarking_local_amp
        self.rabi.att_729 = self.AnalogBenchmarking_local_att
        self.rabi.freq_729 = self.calc_frequency(
            self.AnalogBenchmarking_local_line_selection,
            dds=self.rabi.channel_729
        )
        self.rabi.phase_729 = phase
        self.rabi.run(self)

    @kernel
    def AnalogRB(self):
        self.phase_ref_time = now_mu()
        self.simulation.phase_ref_time = self.phase_ref_time

        trace_name = "AnalogRB"
        with self.core_dma.record(trace_name):
            self.stateprep.run(self)

            # initial_state will be a string: "SS", "SD", "DS", or "DD"
            initial_state = self.initial_states[self.sequence_number]
            if initial_state == "SD" or initial_state == "DD":
                self.global_pi_pulse()
            if initial_state == "SD" or initial_state == "DS":
                self.local_pi_pulse()

            # Run the simulation for each item in the sequence
            sequence_length = len(self.sequences_reverse_step[self.sequence_number])
            for i in range(sequence_length):
                # TODO_RYAN: Optimize or move this delay so it doesn't interrupt the pulse sequence
                delay(5*us)
                self.simulation.reverse = self.sequences_reverse_step[self.sequence_number][i]
                self.simulation.disable_coupling_term = not self.sequences_enable_0[self.sequence_number][i]
                self.simulation.disable_transverse_term = not self.sequences_enable_1[self.sequence_number][i]
                self.simulation.run(self)

            # adjust for the final_state so that we ideally end up back in SS
            final_state = self.final_states[self.sequence_number]
            if initial_state == "SD" or initial_state == "DS":
                self.local_pi_pulse(phase=180.)
            if initial_state == "SD" or initial_state == "DD":
                self.global_pi_pulse(phase=180.)
        
        handle = self.core_dma.get_handle(trace_name)
        self.core.break_realtime()
        self.core_dma.playback_handle(handle)
