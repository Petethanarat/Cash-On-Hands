"""
logger_util.py
------------------------------------------------------------------
ระบบบันทึก log กลางของโปรเจกต์ COH

ให้ 2 อย่าง:
    logger       : logging.Logger เขียนทั้งลงไฟล์ (ในโฟลเดอร์ logs) และหน้าจอ
    logger_func  : decorator สำหรับ log ตอนเข้า/ออก/ error ของฟังก์ชัน
"""
import os
import sys
import logging
import functools
from datetime import datetime

from util.config_util import CONFIG


# ----- เตรียมโฟลเดอร์เก็บ log -----
os.makedirs(CONFIG.Pythonlogs_Path, exist_ok=True)
_log_file = os.path.join(
    CONFIG.Pythonlogs_Path,
    f"COH_{datetime.now():%Y%m%d_%H%M%S}.log",
)

# ----- สร้าง logger (กันสร้าง handler ซ้ำเวลา import หลายรอบ) -----
logger = logging.getLogger("COH")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    _fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # เขียนลงไฟล์ (เก็บทุกระดับตั้งแต่ DEBUG)
    _file_handler = logging.FileHandler(_log_file, encoding="utf-8")
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(_fmt)
    logger.addHandler(_file_handler)

    # แสดงบนหน้าจอ (ตั้งแต่ INFO ขึ้นไป)
    _stream_handler = logging.StreamHandler(sys.stdout)
    _stream_handler.setLevel(logging.INFO)
    _stream_handler.setFormatter(_fmt)
    logger.addHandler(_stream_handler)

    logger.propagate = False


def logger_func(func):
    """
    Decorator: log ตอนเริ่ม / จบ / เกิด exception ของฟังก์ชัน
    ใช้แบบ @logger_func เหนือฟังก์ชันที่ต้องการติดตาม
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info("=== START: %s ===", func.__name__)
        try:
            result = func(*args, **kwargs)
            logger.info("=== END: %s ===", func.__name__)
            return result
        except Exception as e:
            logger.error("EXCEPTION in %s: %s", func.__name__, e, exc_info=True)
            raise
    return wrapper
