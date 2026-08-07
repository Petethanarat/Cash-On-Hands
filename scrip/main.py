from util.logger_util import logger,logger_func
from util.config_util import CONFIG ,ConfigUtil
from COH import run_process

def main():
    try:
        # subprocess.run(["playwright", "install"]) 
        # logger.info(CONFIG.process_name_shortname)
        # logger.info(CONFIG.Holiday_Path)
        # ConfigUtil.excel_to_list("Holiday_Path")
        # logger.info(CONFIG.Holiday_Path
        
        # master_file_path = r"D:\TEST\LP_STANG\Input\Master_COH.xlsx"
        # transaction_file_path = r"D:\TEST\LP_STANG\OG\JS_889_202504.xlsx"
        run_process()
        # run_process()
    except Exception as e:
        logger.critical("Program crashed due to an unhandled exception: %s", e, exc_info=True)
        raise Exception("The program is under exception error") from e
if __name__ == "__main__":
    main()