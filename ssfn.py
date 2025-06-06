import os
import shutil
from src.util.logger import Logger

class SSFNHandler:
    def __init__(self):
        self.logger = Logger()

    def use_local_ssfn(self, local_ssfn_filepath: str, steam_path: str) -> bool:
        # 제공된 로컬 SSFN 파일이 실제로 존재하는지 확인합니다.
        if not os.path.exists(local_ssfn_filepath):
            self.logger.log("ERROR", f"로컬 SSFN 파일을 찾을 수 없습니다: {local_ssfn_filepath}")
            return False

        try:
            removed_files = 0
            # 대상 Steam 디렉토리에서 기존 'ssfn' 파일을 모두 제거합니다.
            self.logger.log("INFO", f"'{steam_path}'에서 기존 SSFN 파일을 확인하고 제거합니다.")
            for file in os.listdir(steam_path):
                if file.startswith('ssfn'):
                    full_file_path = os.path.join(steam_path, file)
                    os.remove(full_file_path)
                    removed_files += 1
                    self.logger.log("INFO", f"제거됨: {full_file_path}")

            if removed_files > 0:
                self.logger.log("INFO", f"'{steam_path}'에서 {removed_files}개의 오래된 SSFN 파일을 제거했습니다.")
            else:
                self.logger.log("INFO", f"'{steam_path}'에서 제거할 기존 SSFN 파일이 없습니다.")

            # 제공된 로컬 파일 경로에서 파일 이름(예: 'ssfn1234567890')을 추출합니다.
            ssfn_filename = os.path.basename(local_ssfn_filepath)
            # SSFN 파일이 복사될 Steam 디렉토리 내의 최종 경로를 구성합니다.
            destination_path = os.path.join(steam_path, ssfn_filename)

            # 사용자의 로컬 SSFN 파일을 Steam 디렉토리로 복사합니다.
            shutil.copyfile(local_ssfn_filepath, destination_path)
            self.logger.log("INFO", f"'{ssfn_filename}' 파일이 '{steam_path}'(으)로 성공적으로 복사되었습니다.")
            return True

        except Exception as e:
            # 파일 작업 중 오류가 발생하면 로깅하고 False를 반환합니다.
            self.logger.log("ERROR", f"로컬 SSFN 파일을 사용하는 데 실패했습니다. 오류: {e}")
            return False