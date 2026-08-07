"""
config_util.py
------------------------------------------------------------------
เก็บค่าตั้งค่า (path ต่างๆ) ให้ทั้งโปรเจกต์ COH เรียกใช้ผ่าน CONFIG

ค่า path ถูกคำนวณอัตโนมัติจากตำแหน่งของไฟล์นี้
(PROJECT_ROOT = โฟลเดอร์แม่ของ scrip)

ถ้าต้องการกำหนด path เอง ให้แก้ค่าในส่วน "OVERRIDE" ด้านล่างได้เลย
"""
import os


class ConfigUtil:
    # ----- คำนวณตำแหน่งโฟลเดอร์อัตโนมัติ -----
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))   # ...\scrip\util
    SCRIPT_DIR = os.path.dirname(_THIS_DIR)                   # ...\scrip
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)               # ...\Cash_on_hand

    # ----- ชื่อโปรเซส (ใช้แสดงใน log) -----
    process_name_shortname = "COH (Cash on Hand)"

    # ----- path หลัก (คำนวณจาก PROJECT_ROOT) -----
    Input_Path = os.path.join(PROJECT_ROOT, "Input")
    Output_Path = os.path.join(PROJECT_ROOT, "Output")
    BackupInput_Path = os.path.join(Input_Path, "back_up")
    Pythonlogs_Path = os.path.join(PROJECT_ROOT, "logs")

    # ไฟล์วันหยุด (อ้างถึงเฉพาะในโค้ดที่ comment ไว้ ปัจจุบันชี้ไป Master_COH.xlsx)
    Holiday_Path = os.path.join(Input_Path, "Master_COH.xlsx")

    # ==================================================================
    # OVERRIDE: ถ้าต้องการกำหนด path เอง ให้ uncomment แล้วแก้ค่าตรงนี้
    # Input_Path       = r"D:\Cash_on_hand\Input"
    # Output_Path      = r"D:\Cash_on_hand\Output"
    # BackupInput_Path = r"D:\Cash_on_hand\Input\back_up"
    # Pythonlogs_Path  = r"D:\Cash_on_hand\logs"
    # ==================================================================

    @classmethod
    def excel_to_list(cls, path_attr, sheet_name=0, column=None):
        """
        อ่าน Excel จาก path ที่เก็บไว้ใน CONFIG (ระบุด้วยชื่อ attribute)
        แล้วคืนค่าเป็น list

        path_attr : ชื่อ attribute เช่น "Holiday_Path"
        column    : ชื่อคอลัมน์ที่ต้องการ (ถ้าไม่ระบุ = ใช้คอลัมน์แรก)
        """
        import pandas as pd  # import แบบ lazy เพื่อไม่ให้ config หนักตอน import

        path = getattr(cls, path_attr)
        df = pd.read_excel(path, sheet_name=sheet_name)
        if column is not None and column in df.columns:
            series = df[column]
        else:
            series = df.iloc[:, 0]
        return series.dropna().tolist()


# ให้โค้ดอื่นเรียกใช้ผ่าน CONFIG ได้เลย (ใช้คลาสตรงๆ ไม่ต้องสร้าง instance)
CONFIG = ConfigUtil
