import yaml
from yaml import SafeLoader
import os # os 모듈 추가 (경로 존재 여부 확인용)
from src.steam.reg import SteamReg # SteamReg 클래스를 임포트합니다.

class Config():
    def __init__(self):
        try:
            with open("config.yaml", "r", encoding='utf-8') as file:
                self.config = yaml.load(file, Loader=SafeLoader)

            self.build_version: str = "1.5"
            self.username: str = self.config["username"]

            # --- 변경된 부분 ---
            # SteamReg를 사용하여 Steam 경로를 자동으로 감지합니다.
            self.steam_reg = SteamReg()
            try:
                # 레지스트리에서 SteamPath를 가져옵니다.
                self.steam_path: str = self.steam_reg.get_steam_path()
                # 가져온 경로가 실제로 존재하는 유효한 디렉토리인지 확인합니다.
                if not os.path.isdir(self.steam_path):
                    raise ValueError(f"감지된 Steam 경로가 유효하지 않습니다: {self.steam_path}")
            except Exception as e:
                # 레지스트리에서 Steam 경로를 찾지 못하거나 유효하지 않은 경우
                # 사용자에게 config.yaml에 수동으로 입력하도록 안내합니다.
                print(f"경고: Steam 경로를 자동으로 감지하지 못했습니다. {e}")
                print("config.yaml 파일의 'steam_path'에 Steam 설치 경로를 수동으로 입력해야 합니다.")
                # config.yaml에서 steam_path를 fallback으로 읽도록 합니다 (옵션)
                self.steam_path: str = self.config.get("steam_path")
                if not self.steam_path or not os.path.isdir(self.steam_path):
                    raise ValueError("config.yaml에서도 유효한 Steam 경로를 찾을 수 없습니다. 경로를 설정해주세요.")

        except FileNotFoundError:
            print("ERROR: config.yaml 파일을 찾을 수 없습니다. 프로젝트 루트 폴더에 있는지 확인하세요.")
            exit()
        except KeyError as e:
            print(f"ERROR: config.yaml 파일에 필수 키가 누락되었습니다: {e}. 파일을 확인하세요.")
            exit()
        except ValueError as e: # 새로 추가된 Steam 경로 관련 오류
            print(f"CRITICAL ERROR: {e}")
            exit()
        except Exception as e:
            print(f"ERROR: config.yaml 로드 또는 Steam 경로 감지 중 오류 발생: {e}")
            exit()

    def get_steam_path(self) -> str:
        return self.steam_path