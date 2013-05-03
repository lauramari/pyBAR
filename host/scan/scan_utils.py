import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors, cm
import pprint
import time
import struct

import BitVector

from utils.utils import get_all_from_queue

class FEI4ScanUtils(object):
    def __init__(self, register, register_utils):
        self.register = register
        self.register_utils = register_utils
    
    def base_scan(self, command, repeat = 100, mask = 6, steps = None, dcs = None, hardware_repeat = False, same_mask_for_all_dc = False, read_function = None, digital_injection = False):
        if not isinstance(command, BitVector.BitVector):
            raise TypeError
        
        conf_mode_command = self.register.get_commands("confmode")
        run_mode_command = self.register.get_commands("runmode")
        
        if steps == None or steps == []:
            mask_steps = range(mask)
        else:
            mask_steps = steps
            
        if dcs == None or dcs == []:
            dc_steps = range(40)
        else:
            dc_steps = dcs
        
        # preparing for scan
        commands = []
        if digital_injection == True:
            #self.register.set_global_register_value("CalEn", 1) # for GlobalPulse instead Cal-Command
            self.register.set_global_register_value("DIGHITIN_SEL", 1)
            commands.extend(self.register.get_commands("wrregister", name = ["DIGHITIN_SEL"]))
        else:
            dimension = (80,336)
            zero_mask = np.zeros(dimension, dtype = np.uint8)
            self.register.set_pixel_register_value("EnableDigInj", zero_mask)
        self.register_utils.send_commands(commands)
            
        for mask_step in mask_steps:# range(steps):
            commands = []
            commands.extend(conf_mode_command)
            mask_array = self.register_utils.make_pixel_mask(mask = mask, row_offset = mask_step)
            #plt.imshow(np.transpose(mask_array), interpolation='nearest', aspect="auto")
            #plt.pcolor(np.transpose(mask_array))
            #plt.colorbar()
            #plt.savefig('mask_step'+str(mask_step)+'.eps')
            self.register.set_pixel_register_value("Enable", mask_array)
            if digital_injection == True:
                self.register.set_pixel_register_value("EnableDigInj", mask_array)
            commands.extend(self.register.get_commands("wrfrontend", same_mask_for_all_dc = same_mask_for_all_dc, name = ["Enable"]))
            commands.extend(self.register.get_commands("wrfrontend", same_mask_for_all_dc = same_mask_for_all_dc if digital_injection == True else True, name = ["EnableDigInj"]))
            if digital_injection == True:
                self.register.set_global_register_value("DIGHITIN_SEL", 1)
                commands.extend(self.register.get_commands("wrregister", name = ["DIGHITIN_SEL"]))
            self.register_utils.send_commands(commands)
            print repeat, 'injection(s):', 'mask step', mask_step
            
            for dc in dc_steps:
                commands = []
                #commands.extend(conf_mode_command)
                self.register.set_global_register_value("Colpr_Addr", dc)
                # pack all commands into one bit vector, speeding up of inner loop
                #commands.append(conf_mode_command[0]+BitVector.BitVector(size = 10)+self.register.get_commands("wrregister", name = ["Colpr_Addr"])[0]+BitVector.BitVector(size = 10)+run_mode_command[0])
                commands.append(conf_mode_command[0]+self.register.get_commands("wrregister", name = ["Colpr_Addr"])[0]+run_mode_command[0])
                #commands.extend(self.register.get_commands("wrregister", name = ["Colpr_Addr"]))
                #commands.extend(run_mode_command)
                self.register_utils.send_commands(commands)
                
                #print repeat, 'injections:', 'mask step', mask_step, 'dc', dc
                bit_length = self.register_utils.set_command(command)
                if hardware_repeat == True:
                    self.register_utils.send_command(repeat = repeat, wait_for_cmd = True, command_bit_length = bit_length)
                else:
                    for _ in range(repeat):
                        self.register_utils.send_command()
                try:
                    read_function()
                except TypeError:
                    pass

        # setting back to default values
        commands = []
        if digital_injection == True:
            #self.register.set_global_register_value("CalEn", 0) # for GlobalPulse instead Cal-Command
            self.register.set_global_register_value("DIGHITIN_SEL", 0)
            commands.extend(self.register.get_commands("wrregister", name = ["DIGHITIN_SEL"]))
        self.register.set_global_register_value("Colpr_Addr", 0)
        self.register.set_global_register_value("Colpr_Mode", 0)
        commands.extend(self.register.get_commands("wrregister", name = ["Colpr_Addr", "Colpr_Mode"]))
        self.register_utils.send_commands(commands)
