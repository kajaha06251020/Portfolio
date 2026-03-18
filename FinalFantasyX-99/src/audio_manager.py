"""
オーディオ管理システム
BGM・SE再生を管理
"""

import pygame
from pathlib import Path
from enum import Enum


class AudioType(Enum):
    """オーディオタイプ"""
    BGM = "bgm"
    SE = "se"


class AudioManager:
    """オーディオ管理クラス"""
    
    def __init__(self):
        """オーディオマネージャーを初期化"""
        pygame.mixer.init()
        
        self.bgm_volume = 0.7
        self.se_volume = 0.8
        self.current_bgm = None
        self.bgm_playing = False
        
        # オーディオファイルのキャッシュ
        self.bgm_cache = {}
        self.se_cache = {}

        # 対応拡張子
        self.bgm_exts = [".mid", ".midi", ".mp3", ".ogg", ".wav"]
        self.se_exts = [".mp3", ".ogg", ".wav"]
        
        # オーディオディレクトリ
        self.audio_dir = Path(__file__).parent.parent / "assets" / "sounds"
        self.bgm_dir = self.audio_dir / "bgm"
        self.se_dir = self.audio_dir / "se"

    def _resolve_audio_file(self, audio_id: str, audio_type: AudioType):
        """オーディオIDに対応するファイルパスを解決"""
        exts = self.bgm_exts if audio_type == AudioType.BGM else self.se_exts
        base_dir = self.bgm_dir if audio_type == AudioType.BGM else self.se_dir

        # 1) サブディレクトリ構成（従来互換）
        for ext in exts:
            candidate = base_dir / f"{audio_id}{ext}"
            if candidate.exists():
                return candidate

        # 2) sounds直下に audio_id.xxx
        for ext in exts:
            candidate = self.audio_dir / f"{audio_id}{ext}"
            if candidate.exists():
                return candidate

        # 3) audio_id が拡張子付きの場合
        direct = self.audio_dir / audio_id
        if direct.exists():
            return direct

        # 4) sounds配下を再帰検索（例: sounds/Menu/menu_select.wav を menu_select で解決）
        for ext in exts:
            target_name = f"{audio_id}{ext}" if not audio_id.endswith(ext) else audio_id
            for found in self.audio_dir.rglob(target_name):
                if found.is_file():
                    return found

        return None
    
    def load_bgm(self, bgm_id: str) -> bool:
        """
        BGMを読み込み
        
        Args:
            bgm_id (str): BGM ID (例: "bgm_field_1")
        
        Returns:
            bool: 読み込み成功フラグ
        """
        # キャッシュをチェック
        if bgm_id in self.bgm_cache:
            return True
        
        bgm_file = self._resolve_audio_file(bgm_id, AudioType.BGM)
        if bgm_file:
            self.bgm_cache[bgm_id] = bgm_file
            return True
        
        # ファイルが見つからない場合はスキップ
        print(f"⚠️ BGMファイルが見つかりません: {bgm_id}")
        return False
    
    def load_se(self, se_id: str) -> bool:
        """
        SE(効果音)を読み込み
        
        Args:
            se_id (str): SE ID (例: "se_hit")
        
        Returns:
            bool: 読み込み成功フラグ
        """
        # キャッシュをチェック
        if se_id in self.se_cache:
            return True
        
        se_file = self._resolve_audio_file(se_id, AudioType.SE)
        if se_file:
            try:
                sound = pygame.mixer.Sound(str(se_file))
                self.se_cache[se_id] = sound
                return True
            except Exception as e:
                print(f"SEの読み込みに失敗: {se_id} - {e}")
                return False
        
        # ファイルが見つからない場合はスキップ
        print(f"⚠️ SEファイルが見つかりません: {se_id}")
        return False
    
    def play_bgm(self, bgm_id: str, loop: int = -1, fade_in: int = 0) -> bool:
        """
        BGMを再生
        
        Args:
            bgm_id (str): BGM ID
            loop (int): ループ回数 (-1 = 無限ループ)
            fade_in (int): フェードイン時間(ms)
        
        Returns:
            bool: 再生成功フラグ
        """
        # 現在のBGMと同じ場合はスキップ
        if self.current_bgm == bgm_id and pygame.mixer.music.get_busy():
            return True
        
        # 前のBGMを停止
        self.stop_bgm()
        
        # BGMを読み込み
        if not self.load_bgm(bgm_id):
            return False
        
        try:
            bgm_path = self.bgm_cache[bgm_id]
            pygame.mixer.music.load(str(bgm_path))
            pygame.mixer.music.set_volume(self.bgm_volume)
            pygame.mixer.music.play(loops=loop, fade_ms=fade_in)
            
            self.current_bgm = bgm_id
            self.bgm_playing = True
            print(f"🎵 BGM再生: {bgm_id}")
            return True
        
        except Exception as e:
            print(f"❌ BGM再生エラー: {e}")
            return False
    
    def play_se(self, se_id: str) -> bool:
        """
        SE(効果音)を再生
        
        Args:
            se_id (str): SE ID
        
        Returns:
            bool: 再生成功フラグ
        """
        # SEを読み込み
        if not self.load_se(se_id):
            return False
        
        try:
            se = self.se_cache[se_id]
            se.set_volume(self.se_volume)
            pygame.mixer.find_channel().play(se)
            return True
        
        except Exception as e:
            print(f"❌ SE再生エラー: {e}")
            return False
    
    def stop_bgm(self):
        """BGMを停止"""
        pygame.mixer.music.stop()
        self.bgm_playing = False
    
    def pause_bgm(self):
        """BGMを一時停止"""
        pygame.mixer.music.pause()
    
    def unpause_bgm(self):
        """BGMを再開"""
        pygame.mixer.music.unpause()
    
    def set_bgm_volume(self, volume: float):
        """
        BGM音量を設定
        
        Args:
            volume (float): 音量 (0.0 - 1.0)
        """
        self.bgm_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.bgm_volume)
    
    def set_se_volume(self, volume: float):
        """
        SE音量を設定
        
        Args:
            volume (float): 音量 (0.0 - 1.0)
        """
        self.se_volume = max(0.0, min(1.0, volume))


# グローバルオーディオマネージャー
audio_manager = None


def get_audio_manager() -> AudioManager:
    """グローバルオーディオマネージャーを取得"""
    global audio_manager
    if audio_manager is None:
        audio_manager = AudioManager()
    return audio_manager
