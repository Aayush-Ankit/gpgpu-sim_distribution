# Extraction script to obtain metrics (P/fsynq, fsnyq, area) for ADC from Boris Murman survey (ISSCC and VLSI papers)

import os
import argparse

import xlrd
import re
import csv

# Setup parser - excel file and user defined search constraints
parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="The file with raw ADC data", default="ADCsurvey_rev20190802.xls")
parser.add_argument("-o", "--output", help="The file with dumped ADC stats", default="adc_stats.csv")
parser.add_argument("-e", "--energyMax", help="The max energy in pJ per sampling value", default=20) #20 pJ sampling energy is pretty high for PIM applications
parser.add_argument("-a", "--areaMax", help="The max area in mm2", default=0.0100) # 1000 um2 is a large area compared to SRAM banks
parser.add_argument("-f", "--freqMin", help="The min sampling frequency in Hz", default=10**8) # 10 mega-samples per second is a very high latency per conversion
parser.add_argument("-n", "--normalizeTech", help="Sets if technology normalization based scaling will be done", action='store_true')
parser.add_argument("-v", "--verbose", help="Print every stats collected", action='store_true')

# Obtain constraints
args = parser.parse_args()
adc_input_file = args.path
output_file = args.output
e_max = args.energyMax
a_max = args.areaMax
f_min = args.freqMin
t_norm = args.normalizeTech

if (t_norm):
    print ("Technology normalization actiivated")
    
# Setup the excel sheets and relevant column ids
wb = xlrd.open_workbook (adc_input_file)
isscc_sheet = wb.sheet_by_index(1)
vlsi_sheet = wb.sheet_by_index(2)
adc_sheet_l = [isscc_sheet, vlsi_sheet]
col_id_d = {'tech':4, 'title':5, 'area':10, 'freq':22, 'energy':23} # based on location of data in boris murman survey

# Traverse the sheets
base_tech = 0.045 # 45 nm
valid_types = [int, float]
stat_l = []
dummy_entry = {'bits':0, 'area':0.0, 'energy':0.0, 'freq':0.0, 'shId':0, 'rowId':0}

# Function to search bits in the title
def get_bits_from_title (title):
    # Pattern: Integer followed by a character (space or dash) followed by bits/bit/b" "
    pattern = re.compile("([0-9]+(\.\d*)*)( ||-)(bit|bits|b )", re.IGNORECASE)
    result = re.search(pattern, title)
    if result:
        res_groups = result.groups()
        bits = int(round(float(res_groups[0]))) #some entries have float values for bits
        return bits
    return 0
                          
# Function to get scaling factors for area, freq and energy
def get_scale_afe (tech):
    if (not t_norm): 
        return [1,1,1]
    a_scale = (base_tech/tech)**2
    f_scale = (base_tech/tech)**-1
    e_scale = (base_tech/tech)**2 # assumed quadratic instead of cubic (conservative)
    return [a_scale, f_scale, e_scale]

for shId in range(len(adc_sheet_l)):
    s = adc_sheet_l[shId]
    for i in range(1, s.nrows):
        # check if bit resolution can be found in title
        b_temp = get_bits_from_title (s.cell_value(i, col_id_d['title']))
        if (b_temp < 1):
            continue
        #print ("regex match, row: " + str(i) + "bits: " + str(b_temp))
        
        # check if all necessary entries are valid and add data to list
        t_temp = s.cell_value(i, col_id_d['tech']) #t_temp can have non float entries (eg: 1.00 bicmos)
        if(type(t_temp) == str):
            try:
                t_temp = float(t_temp.split(" ")[0])
            except ValueError:
                print ("Technology: string found, hence skipped")

        a_temp = s.cell_value(i, col_id_d['area'])
        f_temp = s.cell_value(i, col_id_d['freq'])
        e_temp = s.cell_value(i, col_id_d['energy'])
        
        if ((type(t_temp) in valid_types) and (type(a_temp) in valid_types) and
            (type(f_temp) in valid_types) and (type(e_temp) in valid_types)):
            entry_temp = dummy_entry.copy()
            scale_l = get_scale_afe(t_temp)
            entry_temp['bits']      = b_temp
            entry_temp['area']      = a_temp * scale_l[0]
            entry_temp['freq']      = f_temp * scale_l[1]
            entry_temp['energy']    = e_temp * scale_l[2]
            entry_temp['shId'] = shId
            entry_temp['rowId'] = i
            stat_l.append(entry_temp)
            
            # debug support
            if (args.verbose):
                print(entry_temp)

print("No. of entries extracted ", len(stat_l))

# Write to csv file from dictionary
with open(output_file, mode='w') as csv_f:
    fields = dummy_entry.keys()
    writer = csv.DictWriter(csv_f, fieldnames=fields)

    writer.writeheader()
    for entry in stat_l:
        writer.writerow(entry)
