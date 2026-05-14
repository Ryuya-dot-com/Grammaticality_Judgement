#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Audio Lexical Decision Task (Pygame Version)
"""

import pygame
from pygame.locals import *
import os
import random
import pandas as pd
import numpy as np
import sys
import logging
from datetime import datetime
import time
from scipy import stats

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Pygame初期化
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
pygame.mouse.set_visible(False)
pygame.event.set_grab(False)
logging.info("Pygame初期化完了")

# スクリプトのディレクトリを取得
script_dir = os.path.dirname(os.path.abspath(__file__))

# 日本語フォントのパスを設定
jp_font_path = os.path.join(script_dir, 'fonts', 'static', 'NotoSansJP-Regular.ttf')

# フォントが存在するかチェック
if os.path.exists(jp_font_path):
    default_jp_font = jp_font_path
    logging.info(f"日本語フォントを検出: {jp_font_path}")
else:
    # フォントファイルが見つからない場合はシステムフォントを使用
    logging.info(f"フォントファイルが見つかりません: {jp_font_path}")
    
    if sys.platform.startswith("win"):
        # Windowsの場合
        default_jp_font = "Yu Gothic"
    elif sys.platform.startswith("darwin"):
        # macOSの場合
        default_jp_font = "Hiragino Sans"
    else:
        # Linuxなどの場合
        default_jp_font = "Noto Sans CJK JP"

# 全目標語リスト（災害関連語18語）
all_target_words = [
    "basalt", "combustion", "conflagration", "deluge", "drought", "embankment",
    "epicenter", "famine", "levee", "outage", "reservoir", "rubble",
    "subduction", "subsidence", "torrent", "tremor", "vent", "vortex"
]

# フィラーリスト (12語)
all_filler_words = [
    "alarm", "barriers", "coast", "communities",
    "event", "experts", "path", "region",
    "route", "soil", "technology", "villages"
]

# 非単語18語
all_nonwords = [
    "glabe", "brald", "trobe", "prinths", "salp", "culves",
    "snooth", "clerves", "pelch", "blaunt", "smurb", "progues",
    "droft", "ralm", "plerge", "nulb", "trieves", "streen"
]

# グローバル変数
global_clock_start = None
first_trigger_time = None
experiment_paused = False
pause_start_time = None
sound_image_surface = None

# 数字キーとテンキーの対応表
NUMERIC_KEY_MAP = {
    K_0: ('0', 'number_row'),
    K_1: ('1', 'number_row'),
    K_2: ('2', 'number_row'),
    K_3: ('3', 'number_row'),
    K_4: ('4', 'number_row'),
    K_5: ('5', 'number_row'),
    K_6: ('6', 'number_row'),
    K_7: ('7', 'number_row'),
    K_8: ('8', 'number_row'),
    K_9: ('9', 'number_row'),
    K_KP0: ('0', 'numpad'),
    K_KP1: ('1', 'numpad'),
    K_KP2: ('2', 'numpad'),
    K_KP3: ('3', 'numpad'),
    K_KP4: ('4', 'numpad'),
    K_KP5: ('5', 'numpad'),
    K_KP6: ('6', 'numpad'),
    K_KP7: ('7', 'numpad'),
    K_KP8: ('8', 'numpad'),
    K_KP9: ('9', 'numpad')
}

KEY_EVENT_COLUMNS = [
    'Participant', 'date', 'session_timestamp',
    'trial', 'word', 'type', 'presentation', 'phase',
    'key_code', 'key_name', 'key_label', 'key_source', 'normalized_response',
    'phase_time_ms', 'time', 'onset_time', 'task_type'
]

RESULT_COLUMNS = [
    'trial', 'word', 'type', 'presentation',
    'response', 'rt', 'response_key_name', 'response_key_source',
    'jitter_time', 'time', 'onset_time', 'task_type'
]


class ExperimentAbortRequested(Exception):
    """保存を行ってから安全に中断するための例外"""
    pass

# ---- ログメッセージ関数 ----
def log_message(message):
    """ログメッセージをコンソールに出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

# ---- 高精度タイマー関数 ----
def get_time_ms():
    """現在時刻をミリ秒単位で取得"""
    return time.perf_counter() * 1000


def normalize_response_key(key_code):
    """解析用に反応キーを正規化"""
    if key_code in [K_1, K_KP1]:
        return '1'
    if key_code in [K_2, K_KP2]:
        return '2'
    return None


def get_key_metadata(key_code):
    """キーコードから可読なラベルを取得"""
    key_name = pygame.key.name(key_code)

    if key_code in NUMERIC_KEY_MAP:
        key_label, key_source = NUMERIC_KEY_MAP[key_code]
        return key_name, key_label, key_source

    return key_name, key_name, 'other'


def log_key_event(key_events, trial_number, word, stim_type, presentation, phase,
                  phase_start_time_ms, key_code):
    """キー押下をイベント単位で記録"""
    event_time_ms = get_time_ms()
    key_name, key_label, key_source = get_key_metadata(key_code)
    onset_time_ms = event_time_ms - first_trigger_time if first_trigger_time is not None else None

    key_events.append({
        'trial': trial_number,
        'word': word,
        'type': stim_type,
        'presentation': presentation,
        'phase': phase,
        'key_code': key_code,
        'key_name': key_name,
        'key_label': key_label,
        'key_source': key_source,
        'normalized_response': normalize_response_key(key_code),
        'phase_time_ms': event_time_ms - phase_start_time_ms if phase_start_time_ms is not None else None,
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        'onset_time': onset_time_ms / 1000.0 if onset_time_ms is not None else None,
        'task_type': 'AUDIO'
    })

    return event_time_ms, key_name, key_label, key_source

# ---- 一時停止チェック ----
def check_pause():
    """一時停止キーの組み合わせをチェック"""
    global experiment_paused, pause_start_time
    
    keys = pygame.key.get_pressed()
    # Cmd+Shift+Escをチェック
    if (keys[pygame.K_LMETA] or keys[pygame.K_RMETA]) and keys[pygame.K_LSHIFT] and keys[pygame.K_ESCAPE]:
        if not experiment_paused:
            experiment_paused = True
            pause_start_time = get_time_ms()
            log_message("一時停止しました。")
            return True
    return False

# ---- 一時停止処理 ----
def handle_pause(screen):
    """一時停止状態を処理し、再開を待つ"""
    global experiment_paused, pause_start_time
    
    if not experiment_paused:
        return 0
    
    # 音声を一時停止
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()
    
    # 一時停止メッセージを表示
    screen.fill((0, 0, 0))
    display_text(screen, "一時停止中...\n\n再開するにはCommand+Shift+Escを押してください", font_size=40)
    
    pause_duration = 0
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("pause_screen_closed")
        
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_LMETA] or keys[pygame.K_RMETA]) and keys[pygame.K_LSHIFT] and keys[pygame.K_ESCAPE]:
            if experiment_paused:
                experiment_paused = False
                screen.fill((0, 0, 0))
                pygame.display.flip()
                pygame.mouse.set_visible(False)
                # 音声を再開
                pygame.mixer.music.unpause()
                waiting = False
                pygame.time.wait(500)
                pause_duration = get_time_ms() - pause_start_time
                log_message(f"再開しました。一時停止時間: {pause_duration:.1f}ミリ秒")
        
        pygame.time.wait(50)
    
    return pause_duration

# ---- Text Display Function (Audio_Check.pyと同じ) ----
def display_text(screen, text, y_offset=0, font_size=36, color=(255, 255, 255), line_spacing=1.2):
    """Displays text on screen with center alignment."""
    try:
        if os.path.exists(jp_font_path):
            font = pygame.font.Font(jp_font_path, font_size)
        else:
            font = pygame.font.Font(None, font_size)
        
        lines = text.split('\n')
        screen_width, screen_height = screen.get_size()
        
        rendered_lines = []
        for line in lines:
            if line.strip():
                text_surface = font.render(line.strip(), True, color)
                rendered_lines.append(text_surface)
            else:
                rendered_lines.append(None)
        
        line_height = font.get_height()
        total_height = len(rendered_lines) * line_height * line_spacing
        
        start_y = (screen_height - total_height) // 2 + y_offset
        current_y = start_y
        
        for text_surface in rendered_lines:
            if text_surface:
                text_rect = text_surface.get_rect(centerx=screen_width // 2, 
                                                 centery=current_y + line_height // 2)
                screen.blit(text_surface, text_rect)
            current_y += line_height * line_spacing
        
        pygame.display.flip()
    except Exception as e:
        logging.error(f"テキスト表示エラー: {e}")

# ---- 画像表示関数 ----
def display_image(screen, image_surface):
    """画像を画面中央に表示"""
    if image_surface:
        screen_width, screen_height = screen.get_size()
        image_rect = image_surface.get_rect(center=(screen_width // 2, screen_height // 2))
        screen.fill((0, 0, 0))
        screen.blit(image_surface, image_rect)
        pygame.display.flip()

# ---- 固視点表示関数 ----
def display_fixation(screen, duration_ms, trial_number=0, category="fixation", key_events=None):
    """固視点を指定時間表示（ミリ秒単位）"""
    global first_trigger_time
    
    try:
        font = pygame.font.Font(None, 60)
        text_surface = font.render('+', True, (255, 255, 255))
        
        screen_width, screen_height = screen.get_size()
        text_rect = text_surface.get_rect(center=(screen_width // 2, screen_height // 2))
        
        screen.fill((0, 0, 0))
        screen.blit(text_surface, text_rect)
        pygame.display.flip()
        
        # 開始時刻を記録
        start_time_ms = get_time_ms()
        onset_time_ms = start_time_ms - first_trigger_time if first_trigger_time is not None else start_time_ms
        
        # 長い固視点のみ記録（1秒以上）
        if duration_ms > 1000:
            logging.info(f"固視点表示: 継続時間={duration_ms}ミリ秒, 開始時間={onset_time_ms:.1f}ミリ秒")
        
        # 時間計測（ミリ秒精度）
        while get_time_ms() - start_time_ms < duration_ms:
            # 一時停止チェック
            if check_pause():
                pause_duration = handle_pause(screen)
                start_time_ms += pause_duration  # 一時停止時間を追加
                # 画面を再描画
                screen.fill((0, 0, 0))
                screen.blit(text_surface, text_rect)
                pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == QUIT:
                    raise ExperimentAbortRequested("window_closed_during_fixation")
                if event.type == KEYDOWN:
                    if key_events is not None:
                        log_key_event(
                            key_events=key_events,
                            trial_number=trial_number,
                            word='FIXATION',
                            stim_type=category,
                            presentation=0,
                            phase=category,
                            phase_start_time_ms=start_time_ms,
                            key_code=event.key
                        )

                    if event.key == K_ESCAPE:
                        return False, None
            
            pygame.time.wait(1)  # 1ミリ秒待機
        
        return True, {
            'trial': trial_number,
            'word': 'FIXATION',
            'type': category,
            'presentation': 0,
            'response': None,
            'rt': None,
            'response_key_name': None,
            'response_key_source': None,
            'jitter_time': duration_ms / 1000.0,  # 秒に変換して記録
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            'onset_time': onset_time_ms / 1000.0,  # 秒に変換して記録
            'task_type': 'AUDIO'
        } if duration_ms > 1000 else None
        
    except Exception as e:
        logging.error(f"固視点表示エラー: {e}")
        return False, None

# ---- 画面設定 ----
def setup_screen():
    """Sets up the pygame screen in fullscreen mode."""
    try:
        display_info = pygame.display.Info()
        screen_width = display_info.current_w
        screen_height = display_info.current_h
        logging.info(f"画面解像度: {screen_width}x{screen_height}")
        
        screen = pygame.display.set_mode((screen_width, screen_height), FULLSCREEN | pygame.DOUBLEBUF)
        pygame.mouse.set_visible(False)
        pygame.display.set_caption('Audio Lexical Decision Task')
        return screen
    except pygame.error as e:
        logging.error(f"フルスクリーンモード設定エラー: {e}")
        print("フルスクリーンモードの設定に失敗しました。")
        sys.exit(1)

# ---- sound.png画像の読み込み ----
def load_sound_image():
    """sound.png画像を読み込む"""
    global sound_image_surface
    sound_image_path = os.path.join(script_dir, 'sound.png')
    
    if os.path.exists(sound_image_path):
        try:
            sound_image_surface = pygame.image.load(sound_image_path)
            logging.info(f"sound.png画像を読み込みました: {sound_image_path}")
            return True
        except pygame.error as e:
            logging.error(f"sound.png画像の読み込みエラー: {e}")
            return False
    else:
        logging.warning(f"sound.png画像が見つかりません: {sound_image_path}")
        return False

# ---- コマンドラインから参加者情報を取得する関数 ----
def get_participant_info():
    """コマンドラインから参加者情報を取得します"""
    print("\n=== Audio Lexical Decision Task ===\n")
    
    exp_info = {
        'Participant': '',
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # 参加者ID入力
        participant_id = input("参加者ID (例: 001): ").strip()
        if participant_id:
            exp_info['Participant'] = participant_id
        else:
            # デフォルトIDを生成
            exp_info['Participant'] = datetime.now().strftime("%Y%m%d%H%M%S")
            print(f"参加者IDが入力されませんでした。デフォルトID '{exp_info['Participant']}' を使用します。")
        
    except Exception as e:
        print(f"入力エラー: {e}. デフォルト値を使用します。")
        exp_info['Participant'] = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # 入力情報の確認
    print("\n実験情報:")
    print(f"  Participant: {exp_info['Participant']}")
    print(f"  date: {exp_info['date']}")
    print("\n実験を開始します...")
    
    return exp_info

# ---- 基本刺激リスト作成 ----
def create_base_stimuli():
    """基本となる刺激リストを作成"""
    stimuli = []
    
    # 災害関連単語
    for word in all_target_words:
        stimuli.append({
            'word': word,
            'type': 'target'
        })
    
    # 高頻度語
    for word in all_filler_words:
        stimuli.append({
            'word': word,
            'type': 'filler'
        })
    
    # 非単語
    for word in all_nonwords:
        stimuli.append({
            'word': word,
            'type': 'nonword'
        })
    
    return stimuli

# ---- 利用可能な音声ファイルを確認して刺激リストをフィルタリングする関数 ----
def filter_available_stimuli(stim_list):
    """利用可能な音声ファイルのみを残してフィルタリング"""
    available_stimuli = []
    
    for stim in stim_list:
        word = stim['word']
        stim_type = stim['type']
        
        # 刺激の種類に応じたフォルダパスを取得
        if stim_type == 'target':
            folder = 'stimuli_target_audio'
        elif stim_type == 'filler':
            folder = 'stimuli_filler_audio'
        elif stim_type == 'nonword':
            folder = 'nonword_stimuli_audio'
        else:
            continue
        
        # MP3ファイルが存在するかチェック
        audio_path = os.path.join(script_dir, folder, f"{word}.mp3")
        if os.path.exists(audio_path):
            available_stimuli.append(stim)
            logging.info(f"利用可能な音声ファイル: {audio_path}")
        else:
            # 非単語の場合は別のフォルダも確認
            if stim_type == 'nonword':
                alt_folder = 'stimuli_nonword_audio'
                alt_audio_path = os.path.join(script_dir, alt_folder, f"{word}.mp3")
                if os.path.exists(alt_audio_path):
                    available_stimuli.append(stim)
                    logging.info(f"利用可能な音声ファイル: {alt_audio_path}")
                else:
                    logging.warning(f"利用不可の音声ファイル: {audio_path} または {alt_audio_path} - 刺激から除外")
            else:
                logging.warning(f"利用不可の音声ファイル: {audio_path} - 刺激から除外")
    
    return available_stimuli

# ---- 擬似ランダマイズ関数 ----
def pseudo_randomize_single_set(stim_list):
    """単一セットの擬似ランダマイズ：同じカテゴリが3回連続しないように配置"""
    if len(stim_list) <= 1:
        return stim_list
        
    max_consecutive_same_type = 2  # 同じカテゴリの最大連続数
    valid_sequence = False
    
    attempt_count = 0
    max_attempts = 1000  # 最大試行回数を設定
    
    while not valid_sequence and attempt_count < max_attempts:
        attempt_count += 1
        random.shuffle(stim_list)
        valid_sequence = True
        
        # 同じタイプが3回以上連続しないことを確認
        for i in range(len(stim_list) - max_consecutive_same_type):
            current_type = stim_list[i]['type']
            consecutive_count = 1
            
            for j in range(1, max_consecutive_same_type + 1):
                if i + j < len(stim_list) and stim_list[i + j]['type'] == current_type:
                    consecutive_count += 1
                    
            if consecutive_count > max_consecutive_same_type:
                valid_sequence = False
                break
    
    if not valid_sequence:
        logging.warning(f"指定の制約を満たす刺激順序を{max_attempts}回試行して見つけられませんでした。")
        
    return stim_list

# ---- 2回提示用のリスト作成関数 ----
def create_two_presentation_lists(base_stimuli):
    """2回提示用のリストを作成（セット間の重複も防ぐ）"""
    
    # 1回目のリストを作成
    first_presentation = [stim.copy() for stim in base_stimuli]  # ディープコピー
    first_presentation = pseudo_randomize_single_set(first_presentation)
    
    # 2回目のリストを作成
    second_presentation = [stim.copy() for stim in base_stimuli]  # ディープコピー
    
    # セット間の制約：1回目の最後の単語と2回目の最初が異なるようにする
    max_attempts = 100
    for attempt in range(max_attempts):
        second_presentation = pseudo_randomize_single_set(second_presentation)
        
        # 1回目の最後と2回目の最初が異なるかチェック
        if first_presentation[-1]['word'] != second_presentation[0]['word']:
            break
    
    # 各提示回を識別するためのフィールドを追加
    for i, stim in enumerate(first_presentation):
        stim['presentation'] = 1  # 1回目
        stim['global_trial'] = i + 1
    
    for i, stim in enumerate(second_presentation):
        stim['presentation'] = 2  # 2回目
        stim['global_trial'] = i + len(first_presentation) + 1
    
    # 結合
    combined_list = first_presentation + second_presentation
    
    # ログ出力
    logging.info(f"1回目最後の単語: {first_presentation[-1]['word']}")
    logging.info(f"2回目最初の単語: {second_presentation[0]['word']}")
    
    # 刺激タイプのシーケンスをログ出力
    type_sequence_1 = [stim['type'] for stim in first_presentation]
    type_sequence_2 = [stim['type'] for stim in second_presentation]
    logging.info(f"1回目の刺激順序: {type_sequence_1}")
    logging.info(f"2回目の刺激順序: {type_sequence_2}")
    
    return combined_list

# ---- 指示表示関数 ----
def show_instructions(screen):
    """実験の指示を表示"""
    instruction_text = """これから単語が音声で提示されます。
聞こえた単語が「英語として実在する単語である」場合は
人差し指のボタン (1) を押してください。

「英語として実在しない」場合は
中指のボタン (2) を押してください。

できるかぎり早く正確にボタンを押してください。
単語の提示時間は3秒となります。

全部で約10分の課題となります。"""
    
    screen.fill((0, 0, 0))
    display_text(screen, instruction_text, font_size=36)
    
    # 5キーまたはESCキーを待機
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_on_instructions")
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return False
                elif event.key == K_5:
                    waiting = False
    
    screen.fill((0, 0, 0))
    pygame.display.flip()
    return True

# ---- トリガー待機関数 ----
def wait_for_trigger(screen):
    """しばらくお待ちください"""
    global first_trigger_time
    
    screen.fill((0, 0, 0))
    display_text(screen, "しばらくお待ちください...", font_size=40)
    
    logging.info("しばらくお待ちください")
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                raise ExperimentAbortRequested("window_closed_while_waiting_for_trigger")
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    logging.info("ESCキーが押されました: 実験を中断します")
                    return False, None
                elif event.key == K_5:
                    first_trigger_time = get_time_ms()
                    logging.info(f"トリガー('5')検出: 実験開始 (時間: {first_trigger_time:.1f}ミリ秒)")
                    
                    # トリガーイベントを記録
                    trigger_data = {
                        'trial': 0,
                        'word': 'TRIGGER',
                        'type': 'system',
                        'presentation': 0,
                        'response': '5',
                        'rt': 0.0,
                        'response_key_name': None,
                        'response_key_source': None,
                        'jitter_time': 0.0,
                        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        'onset_time': 0.0,
                        'task_type': 'AUDIO'
                    }
                    
                    waiting = False
    
    screen.fill((0, 0, 0))
    pygame.display.flip()
    pygame.event.clear()
    
    return True, trigger_data

# ---- データ保存関数 ----
def save_results(results, key_events, exp_info, current_time):
    """実験結果をCSVファイルに保存"""
    if not results:
        logging.warning("保存するデータがありません")
        return

    if key_events is None:
        key_events = []
        
    results_dir = os.path.join(os.getcwd(), 'results')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    # ログファイルの設定
    log_file = os.path.join(results_dir, f"{exp_info['Participant']}_{current_time}_audio_log.txt")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
        
    results_df = pd.DataFrame(results)
    for column in RESULT_COLUMNS:
        if column not in results_df.columns:
            results_df[column] = None
    results_df = results_df[RESULT_COLUMNS]
    
    # 信号検知理論のためのダミーコーディングを追加
    # 実単語（災害関連語と高頻度語）はシグナルあり=1、非単語はシグナルなし=0
    results_df['signal_present'] = results_df['type'].apply(
        lambda x: 1 if x in ['target', 'filler'] else 0 if x == 'nonword' else None
    )
    
    # 反応コーディング（'1'=「実在語」、'2'=「非単語」）
    results_df['response_binary'] = results_df['response'].apply(
        lambda x: 1 if x == '1' else 0 if x == '2' else None
    )
    
    # SDT分類を追加
    conditions = [
        # ヒット (Hit): シグナルあり & 「単語だ」と判断
        (results_df['signal_present'] == 1) & (results_df['response_binary'] == 1),
        # 見逃し (Miss): シグナルあり & 「単語ではない」と判断
        (results_df['signal_present'] == 1) & (results_df['response_binary'] == 0),
        # 誤警報 (False Alarm): シグナルなし & 「単語だ」と判断
        (results_df['signal_present'] == 0) & (results_df['response_binary'] == 1),
        # 正棄却 (Correct Rejection): シグナルなし & 「単語ではない」と判断
        (results_df['signal_present'] == 0) & (results_df['response_binary'] == 0)
    ]
    choices = ['hit', 'miss', 'false_alarm', 'correct_rejection']
    results_df['sdt_category'] = np.select(conditions, choices, default=None)
    
    # 各カテゴリの合計を計算（サマリー情報として）
    target_total = sum(results_df['type'] == 'target')
    filler_total = sum(results_df['type'] == 'filler')
    nonword_total = sum(results_df['type'] == 'nonword')
    
    hit_count = sum(results_df['sdt_category'] == 'hit')
    miss_count = sum(results_df['sdt_category'] == 'miss')
    fa_count = sum(results_df['sdt_category'] == 'false_alarm')
    cr_count = sum(results_df['sdt_category'] == 'correct_rejection')
    
    # ヒット率と誤警報率の計算
    hit_rate = hit_count / (hit_count + miss_count) if (hit_count + miss_count) > 0 else float('nan')
    fa_rate = fa_count / (fa_count + cr_count) if (fa_count + cr_count) > 0 else float('nan')
    
    # log変換を適用したヒット率と誤警報率 (0と1の値を避けるための調整)
    adjusted_hit_rate = (hit_count + 0.5) / (hit_count + miss_count + 1)
    adjusted_fa_rate = (fa_count + 0.5) / (fa_count + cr_count + 1)
    
    # d'とcriteria (c) の計算
    d_prime = stats.norm.ppf(adjusted_hit_rate) - stats.norm.ppf(adjusted_fa_rate)
    c = -0.5 * (stats.norm.ppf(adjusted_hit_rate) + stats.norm.ppf(adjusted_fa_rate))
    
    # サマリー情報をログに記録
    logging.info(f"SDT分析: ヒット率={hit_rate:.3f}, 誤警報率={fa_rate:.3f}, d'={d_prime:.3f}, c={c:.3f}")
    
    # CSVに保存
    summary_data = {
        'Participant': exp_info['Participant'],
        'date': exp_info['date'],
        'task_type': 'AUDIO',
        'target_total': target_total,
        'filler_total': filler_total,
        'nonword_total': nonword_total,
        'hit_count': hit_count,
        'miss_count': miss_count,
        'false_alarm_count': fa_count,
        'correct_rejection_count': cr_count,
        'hit_rate': hit_rate,
        'false_alarm_rate': fa_rate,
        'd_prime': d_prime,
        'criterion_c': c
    }
    summary_df = pd.DataFrame([summary_data])
    
    # 結果と要約を保存
    file_prefix = f"{exp_info['Participant']}_{current_time}_audio"
    csv_filename = os.path.join(results_dir, f"{file_prefix}_results.csv")
    summary_filename = os.path.join(results_dir, f"{file_prefix}_sdt_summary.csv")
    key_event_filename = os.path.join(results_dir, f"{file_prefix}_key_events.csv")
    key_events_df = pd.DataFrame(key_events)
    key_events_df['Participant'] = exp_info['Participant']
    key_events_df['date'] = exp_info['date']
    key_events_df['session_timestamp'] = current_time
    for column in KEY_EVENT_COLUMNS:
        if column not in key_events_df.columns:
            key_events_df[column] = None
    key_events_df = key_events_df[KEY_EVENT_COLUMNS]
    
    results_df.to_csv(csv_filename, index=False)
    summary_df.to_csv(summary_filename, index=False)
    key_events_df.to_csv(key_event_filename, index=False)
    
    logging.info(f"結果保存完了: {csv_filename}")
    logging.info(f"SDT要約保存完了: {summary_filename}")
    logging.info(f"キーイベント保存完了: {key_event_filename}")

# ---- 音声ファイルのパスを取得する関数 ----
def get_audio_path(word, stim_type):
    """刺激の種類に応じた音声ファイルのパスを取得"""
    if stim_type == 'target':
        folder = 'stimuli_target_audio'
    elif stim_type == 'filler':
        folder = 'stimuli_filler_audio'
    elif stim_type == 'nonword':
        folder = 'nonword_stimuli_audio'
    else:
        return None
    
    audio_path = os.path.join(script_dir, folder, f"{word}.mp3")
    
    # 非単語の場合、別のフォルダも確認
    if stim_type == 'nonword' and not os.path.exists(audio_path):
        alt_folder = 'stimuli_nonword_audio'
        audio_path = os.path.join(script_dir, alt_folder, f"{word}.mp3")
    
    return audio_path if os.path.exists(audio_path) else None

# ---- メイン実験関数 ----
def run_audio_ldt():
    """Audio LDT実験のメイン処理"""
    global first_trigger_time, sound_image_surface
    
    # 実験情報の設定
    exp_info = get_participant_info()
    
    # 現在の時刻を取得
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    logging.info(f"実験開始時刻: {current_time}")
    
    # データ保存のためのファイル名と保存先設定
    results_dir = os.path.join(os.getcwd(), 'results')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    # 画面設定
    screen = setup_screen()
    
    # sound.png画像を読み込む
    load_sound_image()
    
    # 基本刺激リストを作成
    base_stimuli = create_base_stimuli()
    
    # 利用可能な音声ファイルのみに刺激をフィルタリング
    base_stimuli = filter_available_stimuli(base_stimuli)
    
    # 2回提示用のリストを作成
    stimuli = create_two_presentation_lists(base_stimuli)
    
    # 刺激数の確認
    logging.info(f"総刺激数: {len(stimuli)} (各単語2回提示)")
    if len(stimuli) == 0:
        logging.error("有効な刺激がありません。音声ファイルを確認してください。")
        # エラーメッセージを表示
        screen.fill((0, 0, 0))
        error_text = """音声ファイルが見つかりませんでした。

以下のフォルダ構成を確認してください：
- stimuli_target_audio/
- stimuli_filler_audio/
- nonword_stimuli_audio/"""
        display_text(screen, error_text, font_size=36, color=(255, 0, 0))
        pygame.time.wait(5000)
        pygame.quit()
        return
    
    # jitter時間の設定（2〜4秒、96試行分、平均約3秒）
    # 実験時間を10分に最適化
    jitter_times = {
        2: 8,   # 2秒のjitterを8回 = 16秒
        3: 78,  # 3秒のjitterを78回 = 234秒  
        4: 10   # 4秒のjitterを10回 = 40秒
    }
    
    # jitter時間のリスト作成
    jitter_list = []
    for time_val, count in jitter_times.items():
        jitter_list.extend([time_val] * count)
    
    # jitter時間のシャッフル
    random.shuffle(jitter_list)
    
    # 検証情報の出力
    if stimuli:
        total_jitter = sum(jitter_list)
        average_jitter = total_jitter / len(jitter_list)
        total_experiment_time = 10 + 288 + total_jitter + 10 + 2
        
        logging.info(f"Jitter合計: {total_jitter}秒")
        logging.info(f"Jitter平均: {average_jitter:.3f}秒")
        logging.info(f"Jitter総数: {len(jitter_list)}個")
        logging.info(f"予想実験時間: {total_experiment_time}秒 ({total_experiment_time/60:.1f}分)")
    
    # 実験結果の記録用
    results = []
    key_events = []
    
    logging.info("AudioLDT実験を開始します（2回提示、96試行）")

    try:
        # 指示の表示
        if not show_instructions(screen):
            pygame.quit()
            return

        # トリガーを待機
        success, trigger_data = wait_for_trigger(screen)
        if not success:
            pygame.quit()
            return

        if trigger_data:
            results.append(trigger_data)
            key_events.append({
                'trial': 0,
                'word': 'TRIGGER',
                'type': 'system',
                'presentation': 0,
                'phase': 'trigger_wait',
                'key_code': K_5,
                'key_name': '5',
                'key_label': '5',
                'key_source': 'number_row',
                'normalized_response': None,
                'phase_time_ms': 0.0,
                'time': trigger_data['time'],
                'onset_time': 0.0,
                'task_type': 'AUDIO'
            })

        # 最初のlong rest (10秒)
        success, fixation_data = display_fixation(screen, 10000, 0, "initial_rest", key_events)  # 10000ミリ秒
        if not success:
            save_results(results, key_events, exp_info, current_time)
            pygame.quit()
            return

        if fixation_data:
            results.append(fixation_data)

        logging.info("初期レスト終了")

        # 各試行のループ
        for i, stim in enumerate(stimuli):
            word = stim['word']
            presentation = stim['presentation']

            # 音声ファイルのパスを取得
            audio_path = get_audio_path(word, stim['type'])

            if audio_path is None:
                logging.error(f"音声ファイルが見つかりません: {word}")
                # エラーでも記録を残す
                trial_data = {
                    'trial': i + 1,
                    'word': word,
                    'type': stim['type'],
                    'presentation': presentation,
                    'response': 'ERROR',
                    'rt': None,
                    'response_key_name': None,
                    'response_key_source': None,
                    'jitter_time': jitter_list[i % len(jitter_list)],
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    'onset_time': (get_time_ms() - first_trigger_time) / 1000.0,
                    'task_type': 'AUDIO'
                }
                results.append(trial_data)
                continue

            # 固視点を表示
            display_fixation(screen, 0)  # 即座に次へ

            try:
                # 刺激提示時間の開始（ミリ秒単位）
                current_time_ms = get_time_ms()
                onset_time_ms = current_time_ms - first_trigger_time
                stim_start_time_ms = current_time_ms

                # sound.pngを表示（音声再生中のみ）
                if sound_image_surface:
                    display_image(screen, sound_image_surface)
                else:
                    # sound.pngがない場合は単語を表示
                    screen.fill((0, 0, 0))
                    font = pygame.font.Font(None, 60)
                    text_surface = font.render("♪", True, (255, 255, 255))
                    screen_width, screen_height = screen.get_size()
                    text_rect = text_surface.get_rect(center=(screen_width // 2, screen_height // 2))
                    screen.blit(text_surface, text_rect)
                    pygame.display.flip()

                # Pygameで音声再生
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
                logging.info(f"音声再生: {word} (提示{presentation}回目, sound.png表示中)")

                # キー入力の取得（3000ミリ秒間）
                response = None
                rt_value = None
                response_key_name = None
                response_key_source = None

                while get_time_ms() - stim_start_time_ms < 3000:  # 3000ミリ秒
                    # 一時停止チェック
                    if check_pause():
                        pause_duration = handle_pause(screen)
                        stim_start_time_ms += pause_duration  # 一時停止時間を追加
                        # 画面を再描画
                        if sound_image_surface:
                            display_image(screen, sound_image_surface)

                    for event in pygame.event.get():
                        if event.type == QUIT:
                            pygame.mixer.music.stop()
                            raise ExperimentAbortRequested("window_closed_during_stimulus")

                        if event.type == KEYDOWN:
                            event_time_ms, key_name, _, key_source = log_key_event(
                                key_events=key_events,
                                trial_number=i + 1,
                                word=word,
                                stim_type=stim['type'],
                                presentation=presentation,
                                phase='stimulus',
                                phase_start_time_ms=stim_start_time_ms,
                                key_code=event.key
                            )

                            if event.key == K_ESCAPE:
                                logging.info("ESCキーが押されました: 実験を中断します")
                                pygame.mixer.music.stop()
                                save_results(results, key_events, exp_info, current_time)
                                pygame.quit()
                                return
                            elif normalize_response_key(event.key) == '1' and response is None:
                                response = '1'
                                rt_value = event_time_ms - stim_start_time_ms  # ミリ秒単位
                                response_key_name = key_name
                                response_key_source = key_source
                            elif normalize_response_key(event.key) == '2' and response is None:
                                response = '2'
                                rt_value = event_time_ms - stim_start_time_ms  # ミリ秒単位
                                response_key_name = key_name
                                response_key_source = key_source

                    pygame.time.wait(1)  # 1ミリ秒待機

                # 音声停止
                pygame.mixer.music.stop()

                # 結果の保存
                trial_data = {
                    'trial': i + 1,
                    'word': word,
                    'type': stim['type'],
                    'presentation': presentation,
                    'response': response,
                    'rt': rt_value,  # ミリ秒単位
                    'response_key_name': response_key_name,
                    'response_key_source': response_key_source,
                    'jitter_time': jitter_list[i % len(jitter_list)],
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    'onset_time': onset_time_ms / 1000.0,  # 秒に変換して記録
                    'task_type': 'AUDIO'
                }
                results.append(trial_data)

                if rt_value is not None:
                    logging.info(f"試行 {i+1}: {word} ({stim['type']}, 提示{presentation}) - 反応: {response}, RT: {rt_value:.1f}ms")
                else:
                    logging.info(f"試行 {i+1}: {word} ({stim['type']}, 提示{presentation}) - 無反応")

            except ExperimentAbortRequested:
                raise
            except Exception as e:
                logging.error(f"音声再生エラー: {word} - {e}")
                # エラーが発生した場合でも続行
                trial_data = {
                    'trial': i + 1,
                    'word': word,
                    'type': stim['type'],
                    'presentation': presentation,
                    'response': 'ERROR',
                    'rt': None,
                    'response_key_name': None,
                    'response_key_source': None,
                    'jitter_time': jitter_list[i % len(jitter_list)],
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    'onset_time': onset_time_ms / 1000.0,
                    'task_type': 'AUDIO'
                }
                results.append(trial_data)

            # Jitter期間（次の刺激までの間隔）
            jitter_duration_ms = jitter_list[i % len(jitter_list)] * 1000  # 秒をミリ秒に変換
            success, fixation_data = display_fixation(screen, jitter_duration_ms, i+1, f"jitter_{i+1}", key_events)
            if not success:
                save_results(results, key_events, exp_info, current_time)
                pygame.quit()
                return

            if fixation_data:
                results.append(fixation_data)

        # 最後の長いrest (10秒)
        success, fixation_data = display_fixation(screen, 10000, len(stimuli)+1, "final_rest", key_events)  # 10000ミリ秒
        if not success:
            save_results(results, key_events, exp_info, current_time)
            pygame.quit()
            return

        if fixation_data:
            results.append(fixation_data)

        logging.info("最終レスト終了")

        # 実験終了のメッセージ
        screen.fill((0, 0, 0))
        display_text(screen, "終了", font_size=60)
        pygame.time.wait(2000)

        # データ保存と終了
        save_results(results, key_events, exp_info, current_time)
        pygame.quit()
    except ExperimentAbortRequested as abort_reason:
        logging.info(f"実験を保存して終了します: {abort_reason}")
        save_results(results, key_events, exp_info, current_time)
        pygame.quit()
        return

# ---- 実験の実行 ----
if __name__ == "__main__":
    try:
        # AudioLDT実験を実行
        run_audio_ldt()
    except Exception as e:
        # エラーが発生した場合もデータを保存
        logging.error(f"エラーが発生しました: {e}")
        import traceback
        logging.error(traceback.format_exc())
        pygame.quit()


#  
