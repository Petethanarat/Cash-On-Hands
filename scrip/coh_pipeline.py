import os
import re
import shutil

import numpy as np
import pandas as pd

from util.logger_util import logger, logger_func
from util.config_util import CONFIG


# ===========================================================================
# ส่วนที่ 1: ฟังก์ชันแปลง/จัดรูปแบบข้อมูลเล็กๆ (helper)
# ===========================================================================

def transform(val):
    """ตัดตัวอักษร 'P' นำหน้า UserId ให้เป็นรหัสตัวเลขล้วน
    - 'Pxxxx' (ยาว 5)  -> เติม 0 แทน P  => '0xxxx'
    - 'Pxxxxx' (ยาว>5) -> ตัด P ทิ้ง
    """
    if isinstance(val, str) and val.startswith('P'):
        if len(val) == 5:
            return '0' + val[1:]
        elif len(val) > 5:
            return val[1:]
    return val


def extract_str(df, column_name, new_column_name, n_chars=4, prefix_char='B'):
    """ดึงสตริงส่วนท้ายของค่าในคอลัมน์ (เฉพาะแถวที่ขึ้นต้นด้วย prefix_char)
    ใช้กับกลุ่ม non-Lumpini เพื่อสร้าง 'Id_B' = ตัดอักษร n_chars ตัวแรกของ UserId ที่ขึ้นต้นด้วย 'B'
    แถวที่ไม่เข้าเงื่อนไขจะเป็น NaN
    """
    if column_name not in df.columns:
        raise ValueError(f"คอลัมน์ '{column_name}' ไม่มีอยู่ใน DataFrame")

    # กันไว้: ถ้าคอลัมน์ไม่ใช่สตริง ให้แปลงเป็นสตริงก่อน
    if not pd.api.types.is_string_dtype(df[column_name]):
        df[column_name] = df[column_name].astype(str)

    # สร้างคอลัมน์ใหม่เป็น dtype=object (กัน FutureWarning ตอนใส่สตริงลงคอลัมน์ float)
    df[new_column_name] = pd.Series(np.nan, index=df.index, dtype=object)
    mask = df[column_name].str.startswith(prefix_char, na=False)
    df.loc[mask, new_column_name] = df.loc[mask, column_name].str[n_chars:]
    return df


def format_timedelta_to_dhms(td):
    """แปลง timedelta -> สตริงอ่านง่าย เช่น '1d 02:03:04' / '05:06' / '-00:30'"""
    if pd.isna(td):
        return np.nan
    total = int(td.total_seconds())
    sign = '-' if total < 0 else ''
    total = abs(total)

    days, rem = divmod(total, 24 * 3600)      # แยกวัน
    hours, rem = divmod(rem, 3600)            # แยกชั่วโมง
    minutes, seconds = divmod(rem, 60)        # แยกนาที/วินาที

    day_str = f"{days}d " if days > 0 else ""
    if hours > 0:                             # มีชั่วโมง -> HH:MM:SS
        return f"{sign}{day_str}{hours:02}:{minutes:02}:{seconds:02}"
    if days > 0:                              # ไม่มีชั่วโมงแต่มีวัน -> Nd MM:SS
        return f"{sign}{day_str}{minutes:02}:{seconds:02}"
    return f"{sign}{minutes:02}:{seconds:02}" # เหลือแค่ MM:SS


def convert_dhms_to_seconds(dhms_str):
    """แปลงสตริงรูปแบบ 'Nd HH:MM:SS' / 'HH:MM:SS' / 'MM:SS' กลับเป็นจำนวนวินาที (รองรับติดลบ)"""
    if isinstance(dhms_str, float) and np.isnan(dhms_str):
        return np.nan
    if not isinstance(dhms_str, str):                 # เผื่อรับตัวเลขมาตรงๆ
        try:
            return int(dhms_str)
        except (ValueError, TypeError):
            return np.nan

    dhms_str = dhms_str.strip()
    is_negative = dhms_str.startswith('-')            # จำเครื่องหมายลบไว้ก่อน
    if is_negative:
        dhms_str = dhms_str[1:]

    total = 0
    try:
        if 'd' in dhms_str:                           # มีส่วน "วัน"
            days_part, _, time_str = dhms_str.partition('d')
            total += int(days_part.strip()) * 24 * 3600
            time_str = time_str.strip()
        else:
            time_str = dhms_str

        parts = [int(x) for x in time_str.split(':')]
        if len(parts) == 3:                           # HH:MM:SS
            total += parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:                         # MM:SS
            total += parts[0] * 60 + parts[1]
        else:
            return np.nan
    except ValueError:
        return np.nan

    return -total if is_negative else total


def second_to_time(total_seconds_float):
    """แปลงจำนวนวินาที (int/float) -> สตริง 'HH:MM:SS' (รองรับติดลบ)"""
    if not isinstance(total_seconds_float, (int, float)):
        raise TypeError("Input must be an int or float.")
    sign = "-" if total_seconds_float < 0 else ""
    total = int(abs(total_seconds_float))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"


# ===========================================================================
# ส่วนที่ 2: ฟังก์ชันคำนวณหลัก (สะสมยอด / เวลาถือเงิน / ธงเตือน)
# ===========================================================================

def calculate_daily_accamt(df):
    """คำนวณยอดเงินสะสม (AccAmt) แบบสะสมทีละรายการ ต่อ 1 คน ต่อ 1 วัน"""
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df = df.sort_values(by=['UserId', 'Timestamp']).reset_index(drop=True)
    df['date'] = df['Timestamp'].dt.date                              # ใช้จัดกลุ่มรายวัน
    df['AccAmt'] = df.groupby(['UserId', 'date'])['EAmt'].cumsum().round()
    return df.drop(columns=['date'])


def cal_time_diff(df, user_col, time_col, time_date, diff_col_name='TimeDifference'):
    """คำนวณผลต่างเวลา (timedelta) ระหว่างรายการติดกัน ต่อคนต่อวัน -> คอลัมน์ TimeDifference"""
    # เตรียมคอลัมน์เวลาให้เป็น datetime (รองรับกรณีมี Date+Time แยกกัน)
    if isinstance(df[time_col].dtype, pd.api.extensions.ExtensionDtype) and df[time_col].dtype.kind == 'M':
        pass
    elif 'Date' in df.columns and 'Time' in df.columns and time_col == 'Timestamp':
        df['Timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        time_col = 'Timestamp'
    else:
        df[time_col] = pd.to_datetime(df[time_col])

    df_sorted = df.sort_values(by=[user_col, time_col]).copy()        # .copy() กัน SettingWithCopyWarning
    df_sorted[diff_col_name] = df_sorted.groupby([user_col, time_date])[time_col].diff()
    return df_sorted


def calculate_holding_time_accumulated(df):
    """คำนวณ 'เวลาถือเงิน' (วินาที) ต่อรายการ -> คอลัมน์ CalculatedTimeSeconds
    กติกา (ต่อคนต่อวัน):
      - ถ้ายอด > limit ต่อเนื่อง และสะสมเกิน 16 นาที  -> ใช้เวลาสะสมตั้งแต่จุดเริ่มเกิน
      - ถ้าเกิน limit แต่ยังไม่ถึง 16 นาที             -> ใช้ผลต่างเวลาแบบแถวต่อแถว
      - ถ้าไม่เกิน limit                              -> ใช้ผลต่างเวลาแบบแถวต่อแถว (และรีเซ็ตจุดเริ่ม)
    """
    df_sorted = df.sort_values(by=['UserId', 'Timestamp']).copy()
    df_sorted['CalculatedTimeSeconds'] = 0.0
    df_sorted['Timestamp'] = pd.to_datetime(df_sorted['Timestamp'])
    df_sorted['Date'] = df_sorted['Timestamp'].dt.date

    for (_user, _date), group in df_sorted.groupby(['UserId', 'Date']):
        over_limit = group['AccAmt'] > group['Limit']
        over_start = None                                            # เวลาเริ่มช่วง "เกิน limit" ต่อเนื่อง

        for i in range(len(group)):
            idx = group.index[i]
            now = group.loc[idx, 'Timestamp']

            if over_limit.loc[idx]:
                if over_start is None:                               # เพิ่งเริ่มเกิน limit
                    over_start = now
                accumulated = (now - over_start).total_seconds()     # เวลาสะสมตั้งแต่เริ่มเกิน
                if accumulated > 16 * 60:                            # เกิน 16 นาที -> ใช้เวลาสะสม
                    df_sorted.loc[idx, 'CalculatedTimeSeconds'] = accumulated
                elif i > 0:                                          # ยังไม่ถึง -> ผลต่างจากแถวก่อน
                    prev = group.loc[group.index[i - 1], 'Timestamp']
                    df_sorted.loc[idx, 'CalculatedTimeSeconds'] = (now - prev).total_seconds()
                # i == 0 -> คงค่า 0 (แถวแรกของกลุ่ม)
            else:                                                    # ไม่เกิน limit
                over_start = None                                    # รีเซ็ตจุดเริ่ม
                if i > 0:
                    prev = group.loc[group.index[i - 1], 'Timestamp']
                    df_sorted.loc[idx, 'CalculatedTimeSeconds'] = (now - prev).total_seconds()

    return df_sorted.drop(columns=['Date'])


def flag_daily(df):
    """ตั้งธง flag_day = 'F' บน 'รายการสุดท้ายของวัน' ที่ยอดคงเหลือ (AccAmt) ยังไม่เป็น 0"""
    df = df.copy()
    for col in ('UserId', 'AccAmt'):
        if col not in df.columns:
            raise ValueError(f"DataFrame ต้องมีคอลัมน์ '{col}'")

    # ใช้ Timestamp ถ้ามี ไม่งั้น fallback ไป EjDate
    ts_col = 'Timestamp' if 'Timestamp' in df.columns else ('EjDate' if 'EjDate' in df.columns else None)
    if ts_col is None:
        raise ValueError("DataFrame ต้องมีคอลัมน์ 'Timestamp' หรือ 'EjDate'")

    df[ts_col] = pd.to_datetime(df[ts_col])
    df['daily_date_key'] = df[ts_col].dt.date
    df = df.sort_values(by=['UserId', ts_col], ascending=True)

    # หา index ของรายการสุดท้ายในแต่ละ (คน, วัน)
    last_idx = df.groupby(['UserId', 'daily_date_key'])[ts_col].idxmax()

    # สร้างคอลัมน์ธงเป็น object (กัน FutureWarning) แล้วติดธงเฉพาะแถวที่เข้าเงื่อนไข
    df['flag_day'] = pd.Series(np.nan, index=df.index, dtype=object)
    is_last = df.index.isin(last_idx)                # เงื่อนไข 1: เป็นรายการสุดท้ายของวัน
    is_not_zero = df['AccAmt'] != 0                  # เงื่อนไข 2: ยอดไม่เป็น 0
    df.loc[is_last & is_not_zero, 'flag_day'] = 'F'
    return df.drop(columns=['daily_date_key'])


def create_flag_15min(df):
    """ตั้งธง flag_15min = 'F' เมื่อยอด > limit ต่อเนื่องเกิน ~16 นาที (คิดต่อคน)"""
    required = ['UserId', 'Timestamp', 'AccAmt', 'Limit']
    if not all(c in df.columns for c in required):
        raise ValueError(f"DataFrame ต้องมีคอลัมน์: {', '.join(required)}")

    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df = df.sort_values(by=['UserId', 'Timestamp']).reset_index(drop=True)
    df['flag_15min'] = pd.Series([None] * len(df), index=df.index, dtype=object)

    for _user, user_df in df.groupby('UserId'):
        over_start = None                            # เวลาเริ่มช่วงเกิน limit ต่อเนื่อง
        for _i, row in user_df.iterrows():
            if row['AccAmt'] > row['Limit']:
                if over_start is None:
                    over_start = row['Timestamp']    # เริ่มจับเวลา
                elif (row['Timestamp'] - over_start) >= pd.Timedelta(minutes=16):
                    df.loc[row.name, 'flag_15min'] = 'F'
            else:
                over_start = None                    # ต่ำกว่า limit -> รีเซ็ต
    return df


# ===========================================================================
# ส่วนที่ 3: ฟังก์ชันจัดรูปแบบ Excel และดูแล log
# ===========================================================================

def highlight_center(cell):
    """สไตล์เซลล์: ถ้าเป็นสตริง (เช่น 'F') ให้พื้นหลังแดง+จัดกึ่งกลาง, ที่เหลือแค่จัดกึ่งกลาง"""
    if isinstance(cell, str):
        return 'background-color: red; text-align: center;'
    return 'text-align: center;'


def cleanup_old_logs(log_directory, max_log_files=12):
    """เก็บ log ไว้ไม่เกิน max_log_files ไฟล์ (ลบไฟล์เก่าสุดทิ้งตามเวลาแก้ไขล่าสุด)"""
    logger.info(f"Starting log cleanup in directory: {log_directory}")
    if not os.path.exists(log_directory):
        logger.warning(f"Log directory '{log_directory}' does not exist. Skipping log cleanup.")
        return

    # เก็บ (path, เวลาที่แก้ไข) ของทุกไฟล์ แล้วเรียงเก่า -> ใหม่
    files = []
    for name in os.listdir(log_directory):
        path = os.path.join(log_directory, name)
        if os.path.isfile(path):
            files.append((path, os.path.getmtime(path)))
    files.sort(key=lambda x: x[1])

    if len(files) <= max_log_files:
        logger.info(f"Number of log files ({len(files)}) within limit ({max_log_files}). No files deleted.")
        return

    for path, _ in files[:-max_log_files]:           # ทุกไฟล์ยกเว้น max_log_files ไฟล์ล่าสุด
        try:
            os.remove(path)
            logger.info(f"Deleted old log file: {os.path.basename(path)}")
        except Exception as e:
            logger.error(f"Error deleting log file '{os.path.basename(path)}': {e}", exc_info=True)


# ===========================================================================
# ส่วนที่ 4: อ่าน+join transaction แต่ละไฟล์ (แยกออกมาให้ run_process อ่านง่าย)
# ===========================================================================

def read_transaction(tran_file_path, file_name):
    """อ่านไฟล์ transaction 1 ไฟล์ แล้วคืน DataFrame ที่ทำความสะอาด UserId แล้ว
    - JS_889  -> sheet 'JS_889'  (กลุ่ม Lumpini)
    - อื่นๆ    -> sheet 'JS_All'  (กลุ่มปกติ, สร้างคอลัมน์ Id_B เพิ่ม)
    """
    if "JS_889" in file_name:
        tran = pd.read_excel(tran_file_path, sheet_name='JS_889', dtype={'UserId': str, 'TranCode': str})
    else:
        tran = pd.read_excel(tran_file_path, sheet_name='JS_All', dtype={'UserId': str, 'TranCode': str})
        tran = extract_str(tran, 'UserId', 'Id_B')   # สร้าง Id_B สำหรับ join ระดับพนักงานพิเศษ
    tran['UserId'] = tran['UserId'].apply(transform)  # ตัด 'P' นำหน้า UserId
    return tran


def join_masters(tran, file_name, masters):
    """join transaction เข้ากับ master ต่างๆ เพื่อเติมข้อมูลพนักงาน / limit / ประเภทรายการ"""
    emp, lvlum, lvnon, lvnonS, tran_m = masters

    # 1) join กับ Employee master เพื่อรู้ Position ของแต่ละคน
    j = pd.merge(tran, emp, how='left', left_on='UserId', right_on='ID')

    if 'JS_889' in file_name:
        # กลุ่ม Lumpini: limit มาจากตารางระดับ Lumpini ตรงๆ
        j = pd.merge(j, lvlum, how='left', on='Position')
    else:
        # กลุ่มปกติ: limit มาจากระดับปกติ (Limit_x) หรือระดับพิเศษรายคน (Limit_y) แล้วเลือกที่ไม่ว่าง
        j = pd.merge(j, lvnon, how='left', on='Position')
        j = pd.merge(j, lvnonS, how='left', left_on='Id_B', right_on='Job')
        j['Limit'] = j['Limit_x'].fillna(j['Limit_y'])
        j = j.drop(columns=['Employee Type', 'Limit_x', 'Limit_y'])

    # 2) join กับ Transaction master เพื่อรู้ว่ารายการเป็น Positive/Negative
    j = pd.merge(j, tran_m, how='left', left_on='TranCode', right_on='TransactionID')
    return j


# ===========================================================================
# ส่วนที่ 5: กระบวนการหลัก
# ===========================================================================

@logger_func
def run_process():
    logger.info(CONFIG.process_name_shortname)
    print("-" * 98)

    # --- เก็บกวาด log เก่าก่อนเริ่ม ---
    if getattr(CONFIG, 'Pythonlogs_Path', None):
        cleanup_old_logs(CONFIG.Pythonlogs_Path, max_log_files=12)

    # --- อ่านตาราง master ทั้งหมดจาก Master_COH.xlsx ---
    master_path = os.path.join(CONFIG.Input_Path, "Master_COH.xlsx")
    try:
        emp_master = pd.read_excel(master_path, sheet_name='Employee_Master', dtype={'ID': str})
        lvlum_master = pd.read_excel(master_path, sheet_name='LevelLumpini_Master')
        lvnon_master = pd.read_excel(master_path, sheet_name='Levelnormal_Master')[['Position', 'Limit']]
        lvnonS_master = pd.read_excel(master_path, sheet_name='LevelnormalS_Master')
        tran_master = pd.read_excel(master_path, sheet_name='Transaction_Master', dtype={'TransactionID': str})
    except FileNotFoundError as e:
        logger.critical(f"ERROR: Master file not found at {master_path}. Details: {e}")
        raise Exception("Program stopped: Master file not found.") from e
    except Exception as e:
        logger.critical(f"ERROR: Failed to read master Excel files from {master_path}. Details: {e}", exc_info=True)
        raise Exception("Program stopped: Error reading master files.") from e
    masters = (emp_master, lvlum_master, lvnon_master, lvnonS_master, tran_master)

    # --- ค้นหาไฟล์ transaction (ขึ้นต้น 'JS_' ลงท้าย '.xlsx') ในโฟลเดอร์ Input ---
    try:
        all_files = os.listdir(CONFIG.Input_Path)
        matching_files = sorted(f for f in all_files if f.startswith("JS_") and f.endswith(".xlsx"))
        logger.info(f"found excel file prefix 'JS_' count {len(matching_files)} file: {matching_files}")
        if not matching_files:
            raise FileNotFoundError(f"not found transaction in {CONFIG.Input_Path}")
    except FileNotFoundError as e:
        logger.critical("program not found necessary file (transaction directory): %s", e)
        raise Exception("program not found transaction directory") from e

    result = None
    for selected_file_name in matching_files:
        tran_file_path = os.path.join(CONFIG.Input_Path, selected_file_name)
        file_name = os.path.splitext(selected_file_name)[0]
        logger.info(f"\n--- Start process: {tran_file_path} ---")
        try:
            # (1) อ่าน + (2) join master
            transaction = read_transaction(tran_file_path, file_name)
            logger.info(f"Complete read transaction excel file: {selected_file_name}")
            j = join_masters(transaction, file_name, masters)
            logger.info(f"complete merge data {selected_file_name}")

            # (3) เตรียมคอลัมน์พื้นฐาน: รวมวันเวลา, ทำเงินให้ติดลบถ้าเป็นรายการ Negative
            j['Timestamp'] = pd.to_datetime(j['EjDate'].astype(str) + ' ' + j['EjTime'].astype(str))
            j['EAmt'] = np.where(j['Result'] == 'Negative', -j['Amt1'], j['Amt1'])
            j['key'] = j['UserId'] + '_' + j['EjDate'].dt.strftime('%Y%m%d')
            j.sort_values(by=['EjDate', 'key', 'EjTime'], ascending=True, inplace=True)

            # (4) คำนวณ: ยอดสะสม -> เวลาถือเงิน -> ผลต่างเวลา
            j = calculate_daily_accamt(j)                           # AccAmt
            j = calculate_holding_time_accumulated(j)               # CalculatedTimeSeconds
            j['Time Diff'] = j['CalculatedTimeSeconds'].apply(second_to_time)

            diff = cal_time_diff(j, user_col='UserId', time_col='Timestamp',
                                 time_date='EjDate', diff_col_name='TimeDifference')
            j['time_different'] = diff['TimeDifference'].apply(format_timedelta_to_dhms)
            j['time_sec'] = j['time_different'].apply(convert_dhms_to_seconds)

            # (5) ตั้งธงเตือน 2 แบบ + เวลาที่เกี่ยวข้องกับธง 15 นาที
            j = flag_daily(j)                                       # flag_day
            j = create_flag_15min(j)                                # flag_15min
            j['Time Flag'] = np.where(j['flag_15min'] == 'F', j['time_different'], 0)
            j['Time Flag_sec'] = np.where(j['flag_15min'] == 'F', j['time_sec'], 0)

            # (6) ตัดคอลัมน์ที่ไม่ต้องการออก (Lumpini กับปกติ ตัดต่างกันเล็กน้อย)
            drop_cols = ['Order', 'ID', 'Rank', 'TransactionID', 'Result', 'key', 'Timestamp']
            if "JS_889" not in file_name:
                drop_cols.insert(1, 'Id_B')
            j = j.drop(columns=drop_cols)

            # (7) จัดรูปแบบ: ไฮไลต์ช่องธงเป็นสีแดง + จัดกึ่งกลาง
            styled = j.style.map(highlight_center, subset=['flag_day', 'flag_15min'])
            logger.info("complete process call function")

            # (8) เขียนผลลัพธ์เป็น Excel -> โฟลเดอร์ Output
            num_match = re.search(r'(\d+)(?:\.xlsx)?$', file_name)
            num = num_match.group(1) if num_match else ""
            kind = "Lum" if "JS_889" in file_name else "nonLum"
            output_file_name = f"cash_on_hand_{kind}_{num}.xlsx"
            full_output_path = os.path.join(CONFIG.Output_Path, output_file_name)
            styled.to_excel(full_output_path, sheet_name="cash on hand", index=False)

            # (9) ย้ายไฟล์ต้นทางไปโฟลเดอร์ back_up
            backup_directory = CONFIG.BackupInput_Path
            if not os.path.exists(backup_directory):
                try:
                    os.makedirs(backup_directory)
                    logger.info(f"Created backup directory: {backup_directory}")
                except Exception as e:
                    logger.critical(f"ERROR: Could not create backup directory {backup_directory}. Details: {e}", exc_info=True)
                    raise Exception("Program stopped: Cannot create backup directory.") from e
            try:
                shutil.move(tran_file_path, os.path.join(backup_directory, selected_file_name))
                logger.info(f"Moved '{selected_file_name}' to backup.")
            except Exception as e:
                logger.error(f"Error moving file '{selected_file_name}' to backup: {e}", exc_info=True)

            result = j
        except Exception as e:
            logger.error(f"Error processing file '{selected_file_name}': {e}", exc_info=True)

    return result


if __name__ == "__main__":
    run_process()
