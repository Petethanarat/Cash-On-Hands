####### ภาษาอังกฤษไม่แข็งแรง แต่ดันใช้คอมเมนต์เป็นทั้งหมด สู้ๆครับบ ถ้าบางอันมันสื่อความหมายงงๆ ######
import pandas as pd
import os
import numpy as np
from datetime import timedelta,datetime
import tkinter as tk
import time
import re
import shutil
from tkinter import filedialog, messagebox
from util.logger_util import logger, logger_func
from util.config_util import CONFIG
from util.file_util import FileUtil
from util import file_util
#from dateutil.relativedelta import relative
import itertools
import sys
############### CONDITION FOR USER ID (Cut P) #########
def transform(val):
    if isinstance(val, str) and val.startswith('P'):
        if len(val) == 5:
            return '0' + val[1:]    # Replace 'P' with '0'
        elif len(val) > 5:
            return val[1:]          # Remove 'P'
    return val
### Function Calculate accumulate transaction for each user-day ### 
def calculate_daily_accamt(df):
    df['Timestamp'] = pd.to_datetime(df['Timestamp']) # chang 'Timestamp' to datetime
    df = df.sort_values(by=['UserId', 'Timestamp']).reset_index(drop=True) # sort by user timestamp for calaulate
    df['date'] = df['Timestamp'].dt.date # create date for grouping by date
    df['AccAmt'] = df.groupby(['UserId', 'date'])['EAmt'].cumsum().round() # accumulate each user-date and round down
    df = df.drop(columns=['date']) # drop date column because date not nessassory
    return df
### Func calculate time different row by row ### # I #
def cal_time_diff(df, user_col, time_col, time_date, diff_col_name='TimeDifference'):
    if isinstance(df[time_col].dtype, pd.api.extensions.ExtensionDtype) and df[time_col].dtype.kind == 'M':
        pass
    elif 'Date' in df.columns and 'Time' in df.columns and time_col == 'Timestamp':
        df['Timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        time_col = 'Timestamp' # Update time_col to the new combined column
    else:
        df[time_col] = pd.to_datetime(df[time_col])
    df_sorted = df.sort_values(by=[user_col, time_col]).copy() # made .copy() for avoid SettingWithCopyWarning
    df_sorted[diff_col_name] = df_sorted.groupby([user_col, time_date])[time_col].diff() # group for calculate different time_col each user-day
    return df_sorted
### Function convert datetime to time format DD:HH:MM:SS ###
def format_timedelta_to_dhms(td):
    if pd.isna(td):
        return np.nan # check null
    total_seconds = int(td.total_seconds()) # change timedelta to integer
    sign = '-' if total_seconds < 0 else ''
    total_seconds = abs(total_seconds)

    days, remainder_seconds_after_days = divmod(total_seconds, 24 * 3600) # คำนวณวัน
    hours, remainder = divmod(remainder_seconds_after_days, 3600)
    minutes, seconds = divmod(remainder, 60)

    days_str = f"{int(days)}d " if days > 0 else "" # create day, if have
    if hours > 0:
        return f"{sign}{days_str}{int(hours):02}:{int(minutes):02}:{int(seconds):02}" # create HH:MM:SS
    else:
        if days > 0: # if not hour, show MM:SS
            return f"{sign}{days_str}{int(minutes):02}:{int(seconds):02}"
        else:
            return f"{sign}{int(minutes):02}:{int(seconds):02}" # if not both (hour/minute), show 00:SS
def convert_dhms_to_seconds(dhms_str):
    if isinstance(dhms_str, float) and np.isnan(dhms_str):
        return np.nan
    if not isinstance(dhms_str, str):
        # Handle cases where input might not be a string (e.g., if it's already a number)
        try:
            return int(dhms_str)
        except (ValueError, TypeError):
            return np.nan # Or raise an error if preferred

    dhms_str = dhms_str.strip()

    # Check for negative sign and store it
    is_negative = False
    if dhms_str.startswith('-'):
        is_negative = True
        dhms_str = dhms_str[1:] # Remove the sign for parsing

    total_seconds = 0

    try:
        # Check if days are present (e.g., "1d 02:03:04" or "1d 03:04")
        if 'd' in dhms_str:
            parts = dhms_str.split('d')
            days_str = parts[0].strip()
            time_str = parts[1].strip() if len(parts) > 1 else ""
            days = int(days_str)
            total_seconds += days * 24 * 3600
        else:
            time_str = dhms_str

        # Parse the time part (HH:MM:SS or MM:SS)
        time_components = [int(x) for x in time_str.split(':')]

        if len(time_components) == 3:
            # Format HH:MM:SS
            hours, minutes, seconds = time_components
            total_seconds += hours * 3600 + minutes * 60 + seconds
        elif len(time_components) == 2:
            # Format MM:SS (or Dd MM:SS if days were present)
            minutes, seconds = time_components
            total_seconds += minutes * 60 + seconds
        else:
            # Invalid time format
            return np.nan # Or raise ValueError("Invalid time format")

    except ValueError:
        # Catch errors during int conversion or splitting
        return np.nan # Or raise ValueError(f"Could not parse duration string: {dhms_str}")

    return -total_seconds if is_negative else total_seconds
def second_to_time(total_seconds_float):
    # ตรวจสอบว่าอินพุตเป็นตัวเลขและไม่เป็น None
    if not isinstance(total_seconds_float, (int, float)):
        raise TypeError("Input must be an int or float.")

    # จัดการกรณีที่จำนวนวินาทีเป็นค่าติดลบ
    sign = "-" if total_seconds_float < 0 else ""
    total_seconds_abs = abs(total_seconds_float)

    # แปลงเป็นจำนวนเต็มวินาที
    total_seconds_int = int(total_seconds_abs)

    # คำนวณชั่วโมง นาที วินาที
    hours = total_seconds_int // 3600
    remaining_seconds = total_seconds_int % 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60

    # จัดรูปแบบสตริงให้เป็น HH:MM:SS
    # ใช้ {:02d} เพื่อให้แน่ใจว่าตัวเลขมีสองหลักและมี 0 นำหน้าถ้าจำเป็น
    return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
### Function Flag EOD Alert: Value Not Zero ###
def flag_daily(df):
    # duplicate data frame
    df_copy = df.copy()

    # check 'UserId' and 'Timestamp'
    if 'UserId' not in df_copy.columns:
        raise ValueError("DataFrame ต้องมีคอลัมน์ 'UserId'")
    if 'AccAmt' not in df_copy.columns:
        raise ValueError("DataFrame ต้องมีคอลัมน์ 'AccAmt'")

    timestamp_col = None
    if 'Timestamp' in df_copy.columns:
        timestamp_col = 'Timestamp'
    elif 'EjDate' in df_copy.columns: # if hasn't 'Timestamp' will use 'Ejdate' to Timestamp
        timestamp_col = 'EjDate'
    else:
        raise ValueError("DataFrame ต้องมีคอลัมน์ 'Timestamp' หรือ 'EjDate' ที่สามารถแปลงเป็น datetime ได้")

    df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col]) # change timestamp is datetime

    df_copy['daily_date_key'] = df_copy[timestamp_col].dt.date # create 'daily_date_key' for group by date

    df_copy = df_copy.sort_values(by=['UserId', timestamp_col], ascending=True) # sort by 'UserId' and 'Timestamp' for check idxmax()

    idx_last_transaction_per_day = df_copy.groupby(['UserId', 'daily_date_key'])[timestamp_col].idxmax() # group by 'UserId' and 'Date',then select last transaction of day

    df_copy['flag_day'] = np.nan # create flage is nan
    is_last_transaction_mask = df_copy.index.isin(idx_last_transaction_per_day) # condition 1 last transaction of day

    is_accamt_not_zero_mask = (df_copy['AccAmt'] != 0) # condition 2 'AccAmt' don't equal 0

    condition_to_flag = is_last_transaction_mask & is_accamt_not_zero_mask

    df_copy.loc[condition_to_flag, 'flag_day'] = 'F' # true show 'F'

    df_copy = df_copy.drop(columns=['daily_date_key']) # drop column "daily_date_key" unnecessary

    return df_copy
### Funtion flag Alert: Holding more than limit and more than 15 min ###
def create_flag_15min(df):
    required_columns = ['UserId', 'Timestamp', 'AccAmt', 'Limit']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"DataFrame ต้องมีคอลัมน์: {', '.join(required_columns)}") # check nessessory column

    df['Timestamp'] = pd.to_datetime(df['Timestamp']) # change timestame to date
    df = df.sort_values(by=['UserId', 'Timestamp']).reset_index(drop=True) # sort by username and date

    df['flag_15min'] = None # create flag_15min column

    for user_id, user_df in df.groupby('UserId'): # Group by user and then apply the logic
        # keep status time and timer
        in_condition = False
        condition_start_time = None

        for i, row in user_df.iterrows():
            current_accamt = row['AccAmt']
            current_limit = row['Limit']
            current_timestamp = row['Timestamp']

            # check condition accamt not more than limit
            if current_accamt > current_limit:
                if not in_condition:
                    in_condition = True # if in condition, start timer
                    condition_start_time = current_timestamp
                else:
                    # if in condition, timer run
                    time_diff = current_timestamp - condition_start_time
                    if time_diff >= pd.Timedelta(minutes=16):
                        df.loc[row.name, 'flag_15min'] = 'F' # ตั้งค่า flag เป็น F

            else:
                # accumulate not more than limit will reset
                in_condition = False
                condition_start_time = None

    return df
### Set "F" center and hightlight ###
def highlight_center(cell):
    if isinstance(cell, str):
        return 'background-color: red; text-align: center;'
    else:
        return 'text-align: center;'
def extract_str(df, column_name: str, new_column_name: str, n_chars: int = 4, prefix_char: str = 'B'):
    # ตรวจสอบว่าคอลัมน์ที่ระบุมีอยู่ใน DataFrame หรือไม่
    if column_name not in df.columns:
        raise ValueError(f"คอลัมน์ '{column_name}' ไม่มีอยู่ใน DataFrame")
 
    if not pd.api.types.is_string_dtype(df[column_name]):
        print(f"คำเตือน: คอลัมน์ '{column_name}' ไม่ได้มีข้อมูลเป็นประเภทสตริง ฟังก์ชันจะพยายามแปลงเป็นสตริงก่อนประมวลผล")
        df[column_name] = df[column_name].astype(str)

    df[new_column_name] = np.nan


    starts_with_prefix = df[column_name].str.startswith(prefix_char, na=False)

    df.loc[starts_with_prefix, new_column_name] = df.loc[starts_with_prefix, column_name].str[n_chars:]
    
    return df
def calculate_holding_time_accumulated(df: pd.DataFrame) -> pd.DataFrame:
    df_sorted = df.sort_values(by=['UserId', 'Timestamp']).copy()
    df_sorted['CalculatedTimeSeconds'] = 0.0

    # แปลง Timestamp เป็น datetime ถ้ายังไม่ได้แปลง
    df_sorted['Timestamp'] = pd.to_datetime(df_sorted['Timestamp'])
    
    # สร้างคอลัมน์ 'Date' สำหรับการจัดกลุ่มรายวัน
    df_sorted['Date'] = df_sorted['Timestamp'].dt.date

    # Group by UserId and Date
    for (user_id, date), group in df_sorted.groupby(['UserId', 'Date']):
        group_indices = group.index
        
        is_over_limit = group['AccAmt'] > group['Limit']
        
        current_over_limit_start_time = None

        for i in range(len(group)):
            idx = group.index[i]
            current_timestamp = group.loc[idx, 'Timestamp']

            if is_over_limit.loc[idx]:
                # ถ้าเพิ่งเริ่มต้นช่วงเกินลิมิต
                if current_over_limit_start_time is None:
                    current_over_limit_start_time = current_timestamp
                
                # คำนวณเวลาสะสมจากจุดเริ่มต้นของช่วงเกินลิมิตต่อเนื่อง
                accumulated_duration = (current_timestamp - current_over_limit_start_time).total_seconds()
                
                if accumulated_duration > 16 * 60: # ถ้าเวลาสะสมเกิน 16 นาที
                    df_sorted.loc[idx, 'CalculatedTimeSeconds'] = accumulated_duration
                else:
                    # ถ้าเกินลิมิตแต่เวลาสะสมยังไม่ถึง 16 นาที
                    # ให้คำนวณแบบ row by row (จากแถวก่อนหน้า)
                    if i > 0:
                        prev_timestamp = group.loc[group.index[i-1], 'Timestamp']
                        df_sorted.loc[idx, 'CalculatedTimeSeconds'] = (current_timestamp - prev_timestamp).total_seconds()
                    else:
                        df_sorted.loc[idx, 'CalculatedTimeSeconds'] = 0 # แถวแรกของกลุ่ม
            else: # AccAmt <= Limit (ไม่เกินลิมิต)
                # รีเซ็ตจุดเริ่มต้นของช่วงเกินลิมิต
                current_over_limit_start_time = None
                
                # คิดเวลาที่แตกต่างกันแบบ row by row
                if i > 0:
                    prev_timestamp = group.loc[group.index[i-1], 'Timestamp']
                    df_sorted.loc[idx, 'CalculatedTimeSeconds'] = (current_timestamp - prev_timestamp).total_seconds()
                else:
                    df_sorted.loc[idx, 'CalculatedTimeSeconds'] = 0 # แถวแรกของกลุ่ม

    return df_sorted.drop(columns=['Date'])
########## Define Path Transaction #######
def cleanup_old_logs(log_directory, max_log_files=12):
    logger.info(f"Starting log cleanup in directory: {log_directory}")
    logger.info(f"Keeping a maximum of {max_log_files} log files.")
    if not os.path.exists(log_directory):
        logger.warning(f"Log directory '{log_directory}' does not exist. Skipping log cleanup.")
        return

    # Get all files in the log directory
    log_files = []
    for filename in os.listdir(log_directory):
        file_path = os.path.join(log_directory, filename)
        if os.path.isfile(file_path):
            try:
                # Get modification time and store (path, modification_time)
                modified_time = os.path.getmtime(file_path)
                log_files.append((file_path, modified_time))
            except Exception as e:
                logger.error(f"Error getting modification time for '{filename}': {e}", exc_info=True)
        else:
            logger.debug(f"Skipping non-file item in log directory: {filename}")

    # Sort files by modification time (oldest first)
    log_files.sort(key=lambda x: x[1])

    # Check if the number of files exceeds the limit
    if len(log_files) > max_log_files:
        files_to_delete = log_files[:-max_log_files] # Select oldest files to delete
        deleted_count = 0
        logger.info(f"Found {len(log_files)} log files. Deleting {len(files_to_delete)} oldest files.")

        for file_path, _ in files_to_delete:
            try:
                os.remove(file_path)
                deleted_count += 1
                logger.info(f"Deleted old log file: {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f"Error deleting log file '{os.path.basename(file_path)}': {e}", exc_info=True)
        logger.info(f"Log cleanup completed. Total {deleted_count} old log files deleted.")
    else:
        logger.info(f"Number of log files ({len(log_files)}) is within the limit ({max_log_files}). No files deleted.")
@logger_func
def run_process():
    ######### outter loop bc this code unnessessary in loop, it run just once ######
    # Define path const master.xlsx
    logger.info(CONFIG.process_name_shortname)
    print("--------------------------------------------------------------------------------------------------")
    if hasattr(CONFIG, 'Pythonlogs_Path') and CONFIG.Pythonlogs_Path:
        cleanup_old_logs(CONFIG.Pythonlogs_Path, max_log_files=12)
    else:
            logger.warning("CONFIG.Log_Path is not defined or is empty. Skipping log cleanup.")
    input_file_name = f"Master_COH.xlsx"
    file_path = os.path.join(CONFIG.Input_Path, input_file_name)
    ### Read Excel File ###
    try:
        emp_master= pd.read_excel(file_path,sheet_name='Employee_Master',dtype={
            'ID': str
        }) # r Employee and 'ID' covert to str
        lvlum_master= pd.read_excel(file_path,sheet_name='LevelLumpini_Master')     #### r Lv Lumpini
        # print(lvlum_master.head())
        lvnon_master= pd.read_excel(file_path,sheet_name='Levelnormal_Master')  ### r Lv Non Lumpini
        lvnon_master = lvnon_master.loc[:,['Position','Limit']]  # select column ("Level", "Limit")
        # print(lvnon_master.head())
        lvnonS_master = pd.read_excel(file_path,sheet_name='LevelnormalS_Master')
        tran_master = pd.read_excel(file_path,sheet_name='Transaction_Master',dtype={
            'TransactionID': str
        }) # r Transaction for set "positive/negative" and TransactionID convert to str
    except FileNotFoundError as e:
        logger.critical(f"ERROR: Master file not found at {file_path}. Details: {e}")
        raise Exception("Program stopped: Master file not found.") from e
    except Exception as e:
        logger.critical(f"ERROR: Failed to read master Excel files from {file_path}. Details: {e}", exc_info=True)
        raise Exception("Program stopped: Error reading master files.") from e
    if emp_master is None or lvlum_master is None or lvnon_master is None or lvnonS_master is None or tran_master is None:
        logger.critical("One or more master dataframes are None after loading. Aborting process.")
        raise Exception("Master data not loaded correctly.")
    transaction_directory = CONFIG.Input_Path
    target_prefix = "JS_"
    target_extension = ".xlsx"
    try:
        all_files_in_dir = os.listdir(transaction_directory)
        logger.info(f"found file all: {len(all_files_in_dir)} file in {transaction_directory}")
        matching_files = [
            f for f in all_files_in_dir
            if f.startswith(target_prefix) and f.endswith(target_extension)
        ]
        matching_files.sort()
        logger.info(f"found excel file prefix '{target_prefix}' count {len(matching_files)} file: {matching_files}")
        if not matching_files:
            logger.error(f"not found excel file prefix '{target_prefix}' in directory: {transaction_directory}")
            raise FileNotFoundError(f"not found transaction in {transaction_directory}")
    except FileNotFoundError as e:
        logger.critical("program not found necessary file (transaction directory): %s", e)
        raise Exception("program not found transaction directory") from e
    except Exception as e:
        logger.critical("error from impossible (file listing): %s", e, exc_info=True)
        raise Exception("program error during file listing") from e
    processed_dfs = {}
    for selected_file_name in matching_files:
        tran_file_path = os.path.join(transaction_directory, selected_file_name)
        logger.info(f"\n--- Start process: {file_path} ---")
        try:
    # read select transaction_lum&non_lum
            file_name = os.path.splitext(os.path.basename(tran_file_path))[0]
            if "JS_889" in file_name:
                transaction =  pd.read_excel(tran_file_path ,sheet_name='JS_889',dtype={
                'UserId': str,   
                'TranCode' : str
        }) # r transaction cash on hand
            else:
                transaction = pd.read_excel(tran_file_path ,sheet_name='JS_All',dtype={
            'UserId': str,
            'TranCode' : str
        }) # r transaction cash on hand
                transaction = extract_str(transaction,'UserId','Id_B')
            transaction['UserId'] = transaction['UserId'].apply(transform) # apply func for cut "P"
            logger.info(f"Complete read transaction excel file: {selected_file_name}")

################ JOIN DATA #################
            jtransaction = pd.merge(transaction,emp_master,
            how='left', 
            left_on='UserId',    
            right_on='ID'        
        )
        # merge transaction of Lum & nonlum
            if 'JS_889' in file_name:
                jtransaction = pd.merge(jtransaction,lvlum_master,
            how='left', 
            left_on='Position',
            right_on='Position'
        )
            else:
                jtransaction = pd.merge(jtransaction,lvnon_master,
            how='left',
            left_on='Position',
            right_on='Position'
        )
                jtransaction = pd.merge(jtransaction,lvnonS_master,
            how= 'left',
            left_on= 'Id_B',
            right_on= 'Job'
        )
                jtransaction['Limit'] = jtransaction['Limit_x'].fillna(jtransaction['Limit_y'])
                jtransaction = jtransaction.drop(columns= ['Employee Type','Limit_x','Limit_y'])
            jtransaction = pd.merge(jtransaction,tran_master,
            how='left', 
            left_on='TranCode',    
            right_on='TransactionID'        
        ) 
            logger.info(f"complete merge data {selected_file_name}")
################# PROCESS DATA ################

    ### CREATE KEY FOR LOOP ###
            jtransaction['key'] = jtransaction['UserId'] + '_' + jtransaction['EjDate'].dt.strftime('%Y%m%d')
            jtransaction['Timestamp'] = pd.to_datetime(jtransaction['EjDate'].astype(str) + ' ' + jtransaction['EjTime'].astype(str)) # combine date and time
            jtransaction['EAmt'] = jtransaction.apply(lambda row: -row['Amt1'] if row['Result'] == 'Negative' else row['Amt1'], axis=1)
            jtransaction.sort_values(by = ['EjDate','key','EjTime'], ascending = True, inplace = True) ## Sort by 'EjDate' First, 'key' Second, 'Ejtime' Third
            # jtransaction.head(20)
            ############ Call use Function  ###############
            # call func accumulate
            jtransaction = calculate_daily_accamt(jtransaction)
            jtransaction = calculate_holding_time_accumulated(jtransaction)
            jtransaction['Time Diff'] = jtransaction['CalculatedTimeSeconds'].apply(second_to_time)
            # call cal_time_diff function
            Diff_time_per_ID = cal_time_diff(
                jtransaction,
                user_col = 'UserId',
                time_col = 'Timestamp',
                time_date = 'EjDate',
                diff_col_name ='TimeDifference'
            )
            Diff_time_per_ID['TimeElapsed_Minutes'] = Diff_time_per_ID['TimeDifference'].dt.total_seconds() / 60
            # create column 'time_diff_minute' for keep 'TimeDifference' tranform to HH:MM:SS
            jtransaction['time_different'] = Diff_time_per_ID['TimeDifference'].apply(format_timedelta_to_dhms)
            jtransaction['time_sec'] = jtransaction['time_different'].apply(convert_dhms_to_seconds)
            # over all accumulate
            # call funtion flag alert: when accamt not equal 0 EOD
            jtransaction = flag_daily(jtransaction)
            # call func for alert: flag when in condition
            jtransaction = create_flag_15min(jtransaction)
            jtransaction['Time Flag'] = jtransaction.apply(lambda row: row['time_different'] if row['flag_15min'] == 'F' else 0, axis=1)
            jtransaction['Time Flag_sec'] = jtransaction.apply(lambda row: row['time_sec'] if row['flag_15min'] == 'F' else 0, axis=1)
            if "JS_889" in file_name:
                jtransaction = jtransaction.drop(columns= ['Order', 'ID', 'Rank', 'TransactionID', 'Result', 'key', 'Timestamp'])
            else:
                jtransaction = jtransaction.drop(columns= ['Order','Id_B', 'ID', 'Rank', 'TransactionID', 'Result', 'key', 'Timestamp'])
                # call func hightlight & center
            column_for_highlight = ['flag_day', 'flag_15min']
            jtransaction = jtransaction.style.applymap(highlight_center, subset=column_for_highlight)
            logger.info("complete process call function")
            # tranform to excel
            if "JS_889" in file_name:
                match = re.search(r'(\d+)(?:\.xlsx)?$', file_name)
                extracted_number = ""
                if match:
                    extracted_number = match.group(1)
                    output_file_name = f"cash_on_hand_Lum_{extracted_number}.xlsx"
                else:
                    print("not found name file")
            else:
                match = re.search(r'(\d+)(?:\.xlsx)?$', file_name)
                extracted_number = ""
                if match:
                    extracted_number = match.group(1)
                    output_file_name = f"cash_on_hand_nonLum_{extracted_number}.xlsx"
                else:
                    print("not found name file")
            full_output_path = os.path.join(CONFIG.Output_Path, output_file_name)
            jtransaction.to_excel(full_output_path, sheet_name = "cash on hand",index= False)
            backup_directory = CONFIG.BackupInput_Path
            if not os.path.exists(backup_directory):
                try:
                    os.makedirs(backup_directory)
                    logger.info(f"Created backup directory: {backup_directory}")
                except Exception as e:
                    logger.critical(f"ERROR: Could not create backup directory {backup_directory}. Details: {e}", exc_info=True)
                    raise Exception("Program stopped: Cannot create backup directory.") from e
            destination_backup_path = os.path.join(backup_directory, selected_file_name)
            try:
                shutil.move(tran_file_path, destination_backup_path)
                logger.info(f"Moved '{selected_file_name}' to backup: {destination_backup_path}")
            except FileNotFoundError:
                logger.warning(f"File '{selected_file_name}' not found for moving to backup. It might have been moved or deleted already.")
            except Exception as e:
                logger.error(f"Error moving file '{selected_file_name}' to backup: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error processing file '{selected_file_name}': {e}", exc_info=True)
    return jtransaction

if __name__ == "__main__":
    # print("xxxxx")
    run_process()

    # run_process()