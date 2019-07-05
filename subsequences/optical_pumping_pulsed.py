from artiq.experiment import *


class OpticalPumpingPulsed:
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
        o = OpticalPumpingPulsed
        #self.get_729_dds(o.channel_729, "OpticalPumping")
        self.get_729_dds(self.StatePreparation_channel_729)
        self.dds_866.set(o.frequency_866, 
                         amplitude=o.amplitude_866)
        self.dds_866.set_att(o.att_866)
        freq_729 = self.calc_frequency(
            o.line_selection,
        #    dds=o.channel_729
            dds=self.StatePreparation_channel_729
        )
        self.dds_729_OP.set(freq_729, 
                         amplitude=o.amplitude_729)
        self.dds_729_OP.set_att(o.att_729)
        self.dds_854.set(o.frequency_854, 
                         amplitude=o.amplitude_854)
        self.dds_854.set_att(o.att_854)
        for i in range(int(o.number_of_cycles)):
            with parallel:
                self.dds_729_OP.sw.on()
                self.dds_729_SP_OP.sw.on()
            delay(o.pi_time)
            with parallel:
                self.dds_729_OP.sw.off()
                self.dds_729_SP_OP.sw.off()
                self.dds_854.sw.on()
                self.dds_866.sw.on()
            if i != int(o.number_of_cycles) - 1:
                delay(o.duration_854)
            else:
                delay(10*us)
                self.dds_854.set(80*MHz, amplitude=1.)
                delay(50*us)
            self.dds_854.sw.off()
            self.dds_866.sw.off()
