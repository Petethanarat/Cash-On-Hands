# WORKFLOW — Cash on Hand (COH)

เอกสารอธิบายขั้นตอนการทำงานของระบบประมวลผล "เงินสดในมือ (Cash on Hand)"
เพื่อหาเหตุการณ์ที่พนักงานถือเงินผิดกฎ แล้วออกรายงาน Excel ที่ไฮไลต์ธงเตือน

---

## 1. ภาพรวมโดยย่อ

```
Input (ไฟล์ JS_*.xlsx + Master_COH.xlsx)
        │
        ▼
[อ่าน master]──►[อ่าน transaction]──►[join]──►[คำนวณยอด/เวลา]──►[ตั้งธงเตือน]
        │
        ▼
Output (cash_on_hand_*.xlsx ไฮไลต์แดง)  +  ย้ายไฟล์ต้นทางไป Input\back_up
```

- โค้ดหลัก (เวอร์ชันใช้งานปัจจุบัน): **`scrip\coh_pipeline.py`**
- โค้ดเดิม (เก็บไว้อ้างอิง ไม่รันแล้ว): `scrip\COH.py`
- โมดูลช่วย: `scrip\util\` (`config_util`, `logger_util`, `file_util`)

---

## 2. โครงสร้างโฟลเดอร์

```
D:\Cash_on_hand
├── COH_Report.pbix          รายงาน Power BI
├── Input\                   ไฟล์นำเข้า
│   ├── Master_COH.xlsx          ตาราง master (ดูข้อ 3)
│   ├── JS_889_*.xlsx            transaction กลุ่ม Lumpini
│   ├── JS_All_Not889_*.xlsx     transaction กลุ่มปกติ
│   └── back_up\                 ที่เก็บไฟล์ต้นทางหลังประมวลผลเสร็จ
├── Output\                  ไฟล์ผลลัพธ์ cash_on_hand_*.xlsx
├── logs\                    ไฟล์ log (เก็บล่าสุด 12 ไฟล์)
└── scrip\                   ซอร์สโค้ด
    ├── coh_pipeline.py          ◄ โค้ดหลัก (รันไฟล์นี้)
    ├── COH.py                   โค้ดเดิม
    ├── main.py                  ตัวเรียก run_process ของ COH.py เดิม
    └── util\                    โมดูลช่วยกลาง
```

---

## 3. ข้อมูลนำเข้า (Input)

### 3.1 `Master_COH.xlsx` — มี 5 sheet
| Sheet | ใช้ทำอะไร | คีย์ที่ใช้ join |
|---|---|---|
| `Employee_Master` | ข้อมูลพนักงาน + ตำแหน่ง (Position) | `ID` ↔ `UserId` |
| `LevelLumpini_Master` | limit ตามตำแหน่ง (กลุ่ม Lumpini) | `Position` |
| `Levelnormal_Master` | limit ตามตำแหน่ง (กลุ่มปกติ) | `Position` |
| `LevelnormalS_Master` | limit พิเศษรายบุคคล (กลุ่มปกติ) | `Job` ↔ `Id_B` |
| `Transaction_Master` | ระบุรายการเป็น Positive/Negative | `TransactionID` ↔ `TranCode` |

### 3.2 ไฟล์ transaction `JS_*.xlsx`
- ชื่อขึ้นต้น `JS_` และลงท้าย `.xlsx`
- **`JS_889...`** → อ่าน sheet `JS_889` = กลุ่ม **Lumpini**
- **ชื่ออื่น** → อ่าน sheet `JS_All` = กลุ่ม **ปกติ (nonLum)**

---

## 4. ขั้นตอนการประมวลผล (ทีละสเต็ปใน `run_process`)

โปรแกรมวนทำ **ทีละไฟล์ transaction** ตามลำดับต่อไปนี้:

1. **เก็บกวาด log เก่า** — เก็บไว้ไม่เกิน 12 ไฟล์
2. **อ่าน master ทั้ง 5 sheet** จาก `Master_COH.xlsx`
3. **อ่าน transaction** (`read_transaction`)
   - ทำความสะอาด `UserId` ด้วย `transform()` = ตัด 'P' นำหน้า
   - กลุ่มปกติสร้างคอลัมน์ `Id_B` เพิ่ม (ตัด 4 ตัวแรกของ UserId ที่ขึ้นต้น 'B')
4. **join กับ master** (`join_masters`)
   - เติม `Position` จาก Employee
   - เติม `Limit`:
     - Lumpini → จากตารางระดับ Lumpini ตรงๆ
     - ปกติ → limit ตามตำแหน่ง (`Limit_x`) ถ้าไม่มีใช้ limit พิเศษรายคน (`Limit_y`)
   - เติมผล Positive/Negative จาก Transaction master
5. **เตรียมคอลัมน์พื้นฐาน**
   - `Timestamp` = รวม `EjDate` + `EjTime`
   - `EAmt` = จำนวนเงิน (ติดลบถ้ารายการเป็น Negative)
   - `key` = `UserId_yyyymmdd`
6. **คำนวณ** (เรียงตามลำดับ — สำคัญ)
   - `calculate_daily_accamt` → **`AccAmt`** ยอดเงินสะสมต่อคนต่อวัน
   - `calculate_holding_time_accumulated` → **`CalculatedTimeSeconds`** เวลาถือเงิน
   - `cal_time_diff` → **`TimeDifference`** ผลต่างเวลาระหว่างรายการ
   - แปลงเป็นสตริงอ่านง่าย: `Time Diff`, `time_different`, `time_sec`
7. **ตั้งธงเตือน (flag)**
   - `flag_daily` → **`flag_day = 'F'`** เมื่อรายการสุดท้ายของวัน ยอด ≠ 0
   - `create_flag_15min` → **`flag_15min = 'F'`** เมื่อถือเงินเกิน limit ต่อเนื่อง ≥ ~16 นาที
   - `Time Flag`, `Time Flag_sec` = เวลาที่ผูกกับ flag_15min
8. **จัดรูปแบบ + เขียน Excel**
   - ไฮไลต์ช่อง `flag_day`/`flag_15min` เป็นสีแดง + จัดกึ่งกลาง
   - ตั้งชื่อผลลัพธ์: `cash_on_hand_Lum_<เลข>.xlsx` หรือ `cash_on_hand_nonLum_<เลข>.xlsx`
9. **ย้ายไฟล์ต้นทาง** ไป `Input\back_up\`

---

## 5. ความหมายของธงเตือน (สิ่งที่ต้องดูในรายงาน)

| ธง | เงื่อนไข | ความหมายเชิงธุรกิจ |
|---|---|---|
| **`flag_day = F`** | รายการสุดท้ายของวันของคนนั้น แต่ยอดคงเหลือ (`AccAmt`) ไม่เป็น 0 | สิ้นวันแล้วยังถือเงินอยู่ ไม่เคลียร์ให้เป็นศูนย์ |
| **`flag_15min = F`** | ยอด (`AccAmt`) เกิน `Limit` ต่อเนื่องนานเกิน ~16 นาที | ถือเงินเกินเพดานนานเกินกำหนด |

---

## 6. ผลลัพธ์ (Output)

- ไฟล์ `Output\cash_on_hand_Lum_<yyyymm>.xlsx` และ `cash_on_hand_nonLum_<yyyymm>.xlsx`
- sheet ชื่อ `cash on hand`, ช่องธงถูกไฮไลต์แดง
- ไฟล์ transaction ต้นทางถูกย้ายไป `Input\back_up\` (ไม่หาย แค่ย้าย)

---

## 7. วิธีรัน

```powershell
# ต้องมีไลบรารี: pandas, numpy, openpyxl (tkinter มากับ Python บน Windows)
cd D:\Cash_on_hand\scrip
python coh_pipeline.py
```

- path ทั้งหมดถูกคำนวณอัตโนมัติจากตำแหน่งโฟลเดอร์ (ดู `util\config_util.py`)
  ถ้าต้องการกำหนดเอง ให้แก้ในส่วน `OVERRIDE` ของไฟล์นั้น
- **ก่อนรันซ้ำ** ต้องมีไฟล์ `JS_*.xlsx` อยู่ใน `Input` (ถ้ารันไปแล้วไฟล์จะถูกย้ายไป `back_up` —
  ต้องย้ายกลับมา `Input` ก่อนถึงจะประมวลผลใหม่ได้)

---

## 8. หมายเหตุ / ข้อควรระวัง

- `coh_pipeline.py` ให้ผลลัพธ์เหมือน `COH.py` เดิมทุกอย่าง แต่กระชับกว่า มีคอมเมนต์ครบ
  และแก้ `FutureWarning` ของ pandas (`Styler.applymap`→`map`, การกำหนด dtype ของคอลัมน์ธง) แล้ว
- ฟังก์ชัน `calculate_holding_time_accumulated` และ `create_flag_15min` วนลูปแบบ row-by-row
  จึงช้าเมื่อข้อมูลเยอะ (ไฟล์ nonLum ~38,000 แถว ใช้เวลาราวครึ่งนาที) — ยังทำงานถูกต้อง
- ถ้าไฟล์ master ไม่ครบ sheet หรือชื่อคอลัมน์เปลี่ยน โปรแกรมจะหยุดพร้อม log ระบุสาเหตุ
```
