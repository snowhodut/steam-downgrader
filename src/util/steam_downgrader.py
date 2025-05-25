# src/util/steam_downgrader.py (기존 rollback.py 파일의 내용을 완전히 교체)

import os
import time
import subprocess
from src.util.logger import Logger
from src.helper.config import Config
from src.steam.reg import SteamReg # SteamReg 클래스를 가져옵니다.

class SteamDowngrader: # 클래스 이름 변경

    def __init__(self):
        self.logger = Logger()
        self.config = Config()
        self.steam_reg = SteamReg() # 레지스트리에서 Steam 경로를 가져오기 위함
        self.steam_path = self.config.get_steam_path()
        self.steam_exe_path = self.steam_reg.get_steam_exe_path()


    def _kill_steam_process(self):
        """실행 중인 Steam 프로세스를 종료합니다."""
        try:
            self.logger.log("INFO", "Steam 프로세스를 종료하는 중...")
            # subprocess.run을 사용하여 더 강력하고 오류 확인이 가능한 방식으로 프로세스 종료
            # `check=True`는 non-zero exit code 시 CalledProcessError 발생.
            # `capture_output=True`는 표준 출력/오류를 캡처.
            # `text=True`는 출력을 문자열로 처리.
            subprocess.run(["taskkill", "/f", "/im", "steam.exe"], check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW) # 창 안 뜨게 추가
            time.sleep(1) # 종료 완료 대기
            self.logger.log("INFO", "Steam 프로세스 종료 완료.")
        except subprocess.CalledProcessError as e:
            # 프로세스가 실행 중이 아니면 taskkill이 오류를 반환할 수 있으므로 경고로 처리
            self.logger.log("WARNING", f"Steam 종료 중 경고: {e.stderr.strip()} (Steam이 이미 실행 중이 아니었을 수 있습니다.)")
            time.sleep(1)
        except Exception as e:
            self.logger.log("ERROR", f"Steam 종료 중 예상치 못한 오류 발생: {e} (관리자 권한으로 실행했는지 확인하세요.)")
            time.sleep(1)


    def _create_steam_cfg(self):
        """Steam 업데이트를 영구적으로 막는 steam.cfg 파일을 생성합니다."""
        steam_cfg_path = os.path.join(self.steam_path, "steam.cfg")
        # 가이드에 제시된 업데이트 방지 내용
        cfg_content = "BootStrapperInhibitAll=enable\n"

        try:
            with open(steam_cfg_path, "w", encoding="utf-8") as f:
                f.write(cfg_content)
            self.logger.log("INFO", f"'{steam_cfg_path}' 파일 생성 완료. Steam 업데이트가 방지됩니다.")
        except Exception as e:
            self.logger.log("ERROR", f"'{steam_cfg_path}' 파일 생성 실패: {e}")
            self.logger.exit_program()

    def _edit_loginusers_vdf_for_offline(self):
        """
        loginusers.vdf 파일을 수정하여 특정 계정이 오프라인 모드로 자동 로그인되도록 합니다.
        이는 Steam이 로그인 창을 띄우는 대신 바로 오프라인 모드로 진입하게 할 수 있습니다.
        """
        loginusers_vdf_path = os.path.join(self.steam_path, "config", "loginusers.vdf")

        if not os.path.exists(loginusers_vdf_path):
            self.logger.log("WARNING", f"'{loginusers_vdf_path}' 파일을 찾을 수 없습니다. 오프라인 로그인 설정 건너뜀.")
            return

        try:
            # vdf 파일은 일반 텍스트이므로 읽고 수정할 수 있습니다.
            with open(loginusers_vdf_path, "r+", encoding="utf-8") as f:
                content = f.read()
                f.seek(0) # 파일 포인터를 처음으로 이동

                # 모든 사용자에 대해 RememberPassword, WantsOfflineMode, SkipOfflineModeWarning, AllowAutoLogin을 "1"로 설정
                # 매우 간단한 정규식으로 찾아서 대체합니다. 더 복잡한 VDF 파서는 필요하지 않을 수 있습니다.
                content = content.replace('"RememberPassword"		"0"', '"RememberPassword"		"1"')
                content = content.replace('"RememberPassword"		"1"', '"RememberPassword"		"1"') # 이미 1인 경우 대비

                if '"WantsOfflineMode"' not in content:
                    # WantsOfflineMode가 없는 경우, 아무 SteamID64 뒤에 추가 (정확한 위치는 아닐 수 있으나 작동 가능성)
                    # 더 견고하게 하려면 vdf 파서 라이브러리 (예: vdf) 사용 권장
                    self.logger.log("WARNING", "loginusers.vdf에서 'WantsOfflineMode'를 찾을 수 없습니다. 수동으로 추가해야 할 수도 있습니다.")
                content = content.replace('"WantsOfflineMode"		"0"', '"WantsOfflineMode"		"1"')
                content = content.replace('"WantsOfflineMode"		"1"', '"WantsOfflineMode"		"1"')

                if '"SkipOfflineModeWarning"' not in content:
                    self.logger.log("WARNING", "loginusers.vdf에서 'SkipOfflineModeWarning'를 찾을 수 없습니다. 수동으로 추가해야 할 수도 있습니다.")
                content = content.replace('"SkipOfflineModeWarning"	"0"', '"SkipOfflineModeWarning"	"1"')
                content = content.replace('"SkipOfflineModeWarning"	"1"', '"SkipOfflineModeWarning"	"1"')

                if '"AllowAutoLogin"' not in content:
                    self.logger.log("WARNING", "loginusers.vdf에서 'AllowAutoLogin'를 찾을 수 없습니다. 수동으로 추가해야 할 수도 있습니다.")
                content = content.replace('"AllowAutoLogin"		"0"', '"AllowAutoLogin"		"1"')
                content = content.replace('"AllowAutoLogin"		"1"', '"AllowAutoLogin"		"1"')

                f.truncate(0) # 기존 내용 삭제
                f.write(content)
            self.logger.log("INFO", f"'{loginusers_vdf_path}' 파일 수정 완료. 오프라인 로그인 설정 시도.")
        except Exception as e:
            self.logger.log("ERROR", f"'{loginusers_vdf_path}' 파일 수정 실패: {e}")
            # 이 오류가 발생해도 프로그램 종료 대신 경고만 출력하여 다음 단계 진행 시도
            self.logger.log("WARNING", "loginusers.vdf 수정에 실패했으나, Steam 실행은 시도합니다.")

    def execute_downgrade_online(self):
        self.logger.log("ROLLBACK", "Steam 클라이언트 온라인 다운그레이드 시작...")

        # 1. Steam 강제 종료
        self._kill_steam_process()
        time.sleep(2) # 종료 후 잠시 대기

        # 2. -forcesteamupdate -forcepackagedownload 명령어로 다운그레이드 실행
        wayback_date = self.config.downgrade_wayback_date
        manifest_url_base = f"http://web.archive.org/web/{wayback_date}if_/media.steampowered.com/client"
        
        # Steam 실행 명령어 구성
        # -textmode: GUI 없이 백그라운드에서 업데이트 진행
        # -exitsteam: 업데이트 완료 후 Steam 자동 종료
        # -clearbeta: 혹시 모를 베타 잔여 설정 제거 (가이드 언급)
        # 중요: 명령어가 한 줄 문자열이어야 하고 경로에 공백이 있으면 따옴표로 감싸야 함.
        launch_command = [
            f'"{self.steam_exe_path}"',
            "-forcesteamupdate",
            "-forcepackagedownload",
            f"-overridepackageurl {manifest_url_base}",
            "-textmode",
            "-exitsteam",
            "-clearbeta" # 가이드에 따라 추가
        ]
        
        self.logger.log("ROLLBACK", f"Steam 다운그레이드 명령어 실행 중: {' '.join(launch_command)}")
        try:
            # subprocess.run을 사용하여 외부 프로세스 실행 및 완료 대기
            # shell=True는 문자열 명령어를 쉘로 실행. 따옴표 처리에 주의.
            subprocess.run(' '.join(launch_command), shell=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW) # 창 안 뜨게 추가
            self.logger.log("ROLLBACK", "Steam 다운그레이드 프로세스 실행 완료. Steam이 자동 종료되었을 것입니다.")
            time.sleep(5) # 다운그레이드 프로세스 완료 및 종료 대기

        except subprocess.CalledProcessError as e:
            self.logger.log("ERROR", f"Steam 다운그레이드 실행 실패. Stderr: {e.stderr.strip()}")
            self.logger.log("ERROR", "가이드: 'Steam이 레지스트리 경로 쓰기 불가 다이얼로그를 표시했다면, Repair를 클릭하세요.'")
            self.logger.exit_program()
        except Exception as e:
            self.logger.log("ERROR", f"Steam 다운그레이드 실행 중 예상치 못한 오류 발생: {e}")
            self.logger.exit_program()

        # 3. steam.cfg 파일 생성 (업데이트 방지)
        self._create_steam_cfg()

        # 4. loginusers.vdf 수정 (오프라인 로그인 강제)
        self._edit_loginusers_vdf_for_offline()

        # 5. 다운그레이드된 Steam 클라이언트 실행 시도
        self.logger.log("INFO", "다운그레이드된 Steam 클라이언트 실행 시도 중...")
        # -vgui 옵션을 추가하여 구형 UI 강제
        # 네트워크 차단은 수동 또는 외부 스크립트로 진행해야 함
        final_launch_command = [
            f'"{self.steam_exe_path}"',
            "-vgui" # 구형 UI 강제
        ]
        
        try:
            # subprocess.Popen을 사용하여 Steam을 비동기적으로 실행하고 프로그램은 계속 진행
            # 이 시점에서 사용자가 수동으로 네트워크를 차단해야 합니다.
            subprocess.Popen(' '.join(final_launch_command), shell=True, creationflags=subprocess.CREATE_NO_WINDOW) # 창 안 뜨게 추가
            self.logger.log("OK", "Steam 클라이언트가 실행될 것입니다. 업데이트를 확인하거나 로그인 시도하세요.")
            self.logger.log("WARNING", "매우 중요: Steam 클라이언트가 시작되는 즉시 네트워크를 완전히 차단해야 업데이트를 피할 수 있습니다.")
            self.logger.log("WARNING", "네트워크 차단 후, SSFN 파일을 통해 로그인 시도해 보세요.")
        except Exception as e:
            self.logger.log("ERROR", f"Steam 클라이언트 실행 실패: {e}")
            self.logger.exit_program()