## Modelling script to filter out MVMU energy and latency data from raw stats
# Components considered - SRAM array, ADC (#TODO Add DAC, Shift-and-Add)

# Methodology: excel sheet computes energy/row and latency/row for 16-bit ops based on a specific ADC bits (dot-product width)

import argparse
import xlrd
import csv

# Setup parser - excel file and user defined search constraints
parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="The file with raw ADC data", default="analog-sram-modelling.xlsx")
parser.add_argument("-o", "--output", help="The file with dumped ADC stats", default="mvmu-stats.csv")
parser.add_argument("-t", "--topK", help="The number of top-k ADC candidates to look into for best edp/row", type=int, default=1) # wave latency is dot-product width*row-latency
args = parser.parse_args()

# Setup the excel sheets and relevant column ids
wb = xlrd.open_workbook (args.path)
s = wb.sheet_by_index(2)
col_id_d = {'bits':2, 'energy-row':14, 'latency-row':18, 'mvm-adc-ratio':20} # based on location of data in analog-mvmu-design-exploration sheet

#Emin = {} # dict to keep track of min energy versus bits
#Dmin = {} # dict to keep track of min energy versus bits
EDP = {} # dict to keep track of min EDP versus bits
Config = {} # dict to keep track of best EDP configs versus bits

e_key = 'row-energy'
d_key = 'row-delay'
edp_key = 'row-edp'
ratio_key = 'mvm-adc-ratio'
dummy_entry = {'rowId':0, 'bits':0, e_key:0, d_key:0, edp_key:0, ratio_key:0}

# some helper functions
def create_entry (r_temp, b_temp, e_temp, d_temp, edp_temp, ratio_temp):
    entry_temp = dummy_entry.copy()
    entry_temp['rowId'] = r_temp
    entry_temp['bits'] = b_temp
    entry_temp[e_key] = e_temp
    entry_temp[d_key] = d_temp
    entry_temp[edp_key] = edp_temp
    entry_temp[ratio_key] = ratio_temp
    return entry_temp

def get_single_dict_from_list (dict_l):
    e_temp = d_temp = edp_temp = ratio_temp = 0.0
    entry_combined = dict_l[0].copy()
    n = len(dict_l)
    for entry in dict_l:
        e_temp += entry[e_key]
        d_temp += entry[d_key]
        edp_temp += entry[edp_key]
        ratio_temp += entry[ratio_key]
    entry_combined[e_key] = e_temp / n
    entry_combined[d_key] = d_temp / n
    entry_combined[edp_key] = edp_temp / n
    entry_combined[ratio_key] = ratio_temp / n
    return entry_combined


# Traverse the sheet and extract the MVMU-configs with best energy, delay and EDP
for i in range(2, s.nrows):
    r_temp = i
    b_temp = s.cell_value(i, col_id_d['bits'])
    e_temp = s.cell_value(i, col_id_d['energy-row'])
    d_temp = s.cell_value(i, col_id_d['latency-row'])
    ratio_temp = s.cell_value(i, col_id_d['mvm-adc-ratio'])
    edp_temp = e_temp*d_temp
    
    # Add configs to the Emin, Dmin, EDPmin - if applicable
    # record the edp and config details
    if (not (b_temp in EDP.keys())): # initlialize the list if not present
        entry_temp = create_entry (r_temp, b_temp, e_temp, d_temp, edp_temp, ratio_temp)
        EDP[b_temp] = [edp_temp]
        Config[b_temp] = [entry_temp]

    elif (len(EDP[b_temp]) < args.topK): # append to list
        entry_temp = create_entry (r_temp, b_temp, e_temp, d_temp, edp_temp, ratio_temp)
        EDP[b_temp].append(edp_temp)
        Config[b_temp].append(entry_temp)
    
    else: # replace the max edp config -  if applicable
        max_edp = max(EDP[b_temp])
        if (max_edp > edp_temp): 
            entry_temp = create_entry (r_temp, b_temp, e_temp, d_temp, edp_temp, ratio_temp)
            EDP[b_temp].append(edp_temp)
            Config[b_temp].append(entry_temp)

            # delete the max entry
            i = EDP[b_temp].index(max_edp)  
            del(EDP[b_temp][i])
            del(Config[b_temp][i])


# Write to csv file from dictionary
with open(args.output, mode='w') as csv_f:
    fields = dummy_entry.keys()
    writer = csv.DictWriter(csv_f, fieldnames=fields)

    writer.writeheader()
    for key in Config.keys():
        # construct a dictionary of average of entries (energy, delay and EDP)
        entry = get_single_dict_from_list(Config[key])
        writer.writerow(entry) # writer expects a dictionary
            
