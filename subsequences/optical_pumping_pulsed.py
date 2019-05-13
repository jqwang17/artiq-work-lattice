from artiq.experiment import *


class OpticalPumpingPulsed():
    freq_729=220*MHz
    number_of_cycles="StatePreparation.number_of_cycles"
    duration_854="StatePreparation.pulsed_854_duration"
    pi_time="StatePreparation.pi_time"
    channel_729="StatePreparation.channel_729"
    amplitude_729="StatePreparation.pulsed_amplitude"
    att_729="StatePreparation.pulsed_att"
    frequency_866="DopplerCooling.doppler_cooling_frequency_866"
    amplitude_866="DopplerCooling.doppler_cooling_amplitude_866"
    att_866="DopplerCooling.doppler_cooling_att_866"
    frequency_854="OpticalPumping.optical_pumping_frequency_854"
    amplitude_854="OpticalPumping.optical_pumping_amplitude_854"
    att_854="OpticalPumping.optical_pumping_att_854"
    line_selection="OpticalPumping.line_selection"

    def subsequence(self):
        if OpticalPumpingPulsed.channel_729 == "729L1":
            dds_729 = self.dds_729L1
        elif OpticalPumpingPulsed.channel_729 == "729L2":
            dds_729 = self.dds_729L2
        elif OpticalPumpingPulsed.channel_729 == "729G":
            dds_729 = self.dds_729G
        else:
            dds_729 = self.dds_729G
        
        self.dds_866.set(OpticalPumpingPulsed.frequency_866, amplitude=OpticalPumpingPulsed.amplitude_866)
        self.dds_866.set_att(OpticalPumpingPulsed.att_866)
        dds_729.set(OpticalPumpingPulsed.freq_729, amplitude=OpticalPumpingPulsed.amplitude_729)
        dds_729.set_att(OpticalPumpingPulsed.att_729)
        self.dds_854.set(OpticalPumpingPulsed.frequency_854, amplitude=OpticalPumpingPulsed.amplitude_854)
        self.dds_854.set_att(OpticalPumpingPulsed.att_854)
        self.dds_866.sw.on()
        for _ in range(int(OpticalPumpingPulsed.number_of_cycles)):
            with parallel:
                dds_729.sw.on()
            delay(OpticalPumpingPulsed.pi_time)
            with parallel:
                dds_729.sw.off()
                self.dds_854.sw.on()
            delay(OpticalPumpingPulsed.duration_854)
            self.dds_854.sw.off()
        self.dds_866.sw.off()