"""
file_util.py
------------------------------------------------------------------
รวมฟังก์ชันช่วยจัดการไฟล์/โฟลเดอร์ทั่วไปของโปรเจกต์ COH

ปัจจุบัน COH.py แค่ import ไว้ ยังไม่ได้เรียกใช้เมธอดโดยตรง
จึงเตรียมเมธอดพื้นฐานที่น่าจะได้ใช้เอาไว้ก่อน
"""
import os
import shutil

from util.logger_util import logger


class FileUtil:
    @staticmethod
    def ensure_dir(path):
        """สร้างโฟลเดอร์ถ้ายังไม่มี (รวม parent ทั้งหมด)"""
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def move(src, dst):
        """ย้ายไฟล์ src ไป dst (สร้างโฟลเดอร์ปลายทางให้อัตโนมัติ)"""
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        logger.info("moved '%s' -> '%s'", src, dst)
        return dst

    @staticmethod
    def copy(src, dst):
        """คัดลอกไฟล์ src ไป dst (สร้างโฟลเดอร์ปลายทางให้อัตโนมัติ)"""
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        logger.info("copied '%s' -> '%s'", src, dst)
        return dst

    @staticmethod
    def list_files(directory, prefix="", suffix=""):
        """คืน list ชื่อไฟล์ในโฟลเดอร์ ที่ขึ้นต้น/ลงท้ายตามที่กำหนด (เรียงตามชื่อ)"""
        if not os.path.isdir(directory):
            return []
        files = [
            f for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
            and f.startswith(prefix)
            and f.endswith(suffix)
        ]
        files.sort()
        return files
