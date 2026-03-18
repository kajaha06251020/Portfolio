# セーブ＆ゲームオーバーシステム設計仕様書

**日付:** 2026-03-18
**対象:** FinalFantasyX-99
**ステータス:** 承認済み

---

## 概要

セーブシステムとゲームオーバー処理を実装する。

- **セーブ**: 3スロット制。ダンジョンのセーブポイントタイル・オブジェクト・NPC（王様・神父）から保存。
- **ゲームオーバー**: 全滅 → 「全滅した...」画面 + SE → 任意キー → 最後のセーブ地点へ自動復帰 + ペナルティ適用。
- **フィールドでのセーブは不可。**

---

## セーブデータ構造

`saves/slot_N.json`（N = 1〜3）に以下を保存する。

```json
{
  "meta": {
    "slot": 1,
    "timestamp": "2026-03-18T20:00:00",
    "playtime_seconds": 3600,
    "map_display_name": "ドラゴンの洞窟",
    "party_leader_level": 12
  },
  "location": {
    "map_id": "dragon_cave",
    "player_x": 5,
    "player_y": 8,
    "layer": "physical",
    "save_type": "npc_priest"
  },
  "party": [
    {
      "name": "アルマ",
      "hp": 180, "max_hp": 180,
      "mp": 60,  "max_mp": 60,
      "level": 12, "current_exp": 4200,
      "current_job": "warrior",
      "job_points": 0, "job_mastery": 0,
      "base_max_hp": 180, "base_max_mp": 60,
      "base_attack": 18, "base_defense": 9, "base_magic": 23,
      "attack": 20, "defense": 10, "magic": 25,
      "equipment": {
        "weapon": "sword_mythril",
        "head": null,
        "body": "armor_chain",
        "accessory1": null,
        "accessory2": null
      },
      "alive": true
    }
  ],
  "inventory": {
    "potion": 5,
    "ether": 2,
    "thieves_key": 1
  },
  "gold": 1500,
  "world_state": {
    "flags": {},
    "layers": {},
    "quest_states": {}
  }
}
```

### `save_type` の値

| 値 | 意味 |
|---|---|
| `"tile"` | セーブポイントタイルで保存 |
| `"object"` | セーブポイントオブジェクトで保存 |
| `"npc_priest"` | 神父NPCで保存 |
| `"npc_king"` | 王様NPCで保存 |

---

## SaveManager アーキテクチャ

### ファイル

`src/world/save_manager.py`

### インターフェース

```python
class SaveManager:
    SLOT_COUNT = 3
    SAVE_DIR = "saves/"

    def __init__(self, game): ...

    def save(self, slot: int, save_type: str = "tile") -> bool
        """指定スロットにゲーム状態を書き込む"""

    def load(self, slot: int) -> bool
        """指定スロットからゲーム状態を復元"""

    def load_latest(self) -> bool
        """最も新しいタイムスタンプのスロットをロード"""

    def get_slot_info(self, slot: int) -> dict | None
        """スロット情報を返す（UIに表示用）。空なら None"""

    def apply_game_over_penalty(self) -> None
        """ロード後にペナルティ適用"""

    def has_any_save(self) -> bool
        """いずれかのスロットにセーブデータがあるか"""

    def get_save_type(self) -> str | None
        """最後にロードしたセーブデータの save_type を返す"""

    def _serialize(self, save_type: str) -> dict
    def _deserialize(self, data: dict) -> None
    def _slot_path(self, slot: int) -> Path
```

### データアクセス

| データ | アクセス方法 |
|---|---|
| パーティ（シリアライズ） | `game.character_data.get_party()` で生データを取得（全フィールド含む） |
| パーティ（デシリアライズ） | `game.character_data.replace_party(data["party"])` でマージ復元 |
| インベントリ | `game.inventory` |
| ゴールド | `game.gold` |
| ワールドフラグ | `game.world_state_manager._state` のディープコピー |
| マップ位置 | `game.scenes["map"].current_map` / `player.grid_x` / `player.grid_y` |
| プレイ時間 | `game.playtime_seconds`（新規追加） |
| マップ表示名 | `game.scenes["map"].current_map_data.get("display_name")` |
| レイヤー | `game.scenes["map"]._current_layer` |

**注意:** `_serialize` では `game.character_data.get_party()` の返り値（`_party` リスト）を `copy.deepcopy` して保存する。これにより `current_exp`・`base_max_hp` 等の全フィールドが漏れなく保存される。

### ゲームオーバーペナルティ

```python
def apply_game_over_penalty(self):
    party = self.game.party
    if party:
        party[0]["hp"] = party[0]["max_hp"]
        party[0]["mp"] = party[0]["max_mp"]
        for member in party[1:]:
            member["hp"] = 0
            member["mp"] = 0
    self.game.gold = max(self.game.gold // 2, 0)
```

---

## セーブトリガー 3種

### 1. ダンジョンタイル `Type="save_point"`

Tiledのタイルプロパティに `Type=save_point` を設定。プレイヤーが踏んだとき自動でセーブスロット選択UIを開く。

```
map_scene.update() → step_completed
    → _check_save_point_tile(x, y)
    → tmx tile Type == "save_point"
    → show_save_slot_ui(save_type="tile")
```

### 2. ダンジョンオブジェクト `type="save_point"`

Tiledオブジェクトレイヤーに配置。アクションボタン（スペース/Z）で起動。

```
map_scene.handle_events() → action key
    → _try_interact_save_point()
    → object type == "save_point"
    → show_save_slot_ui(save_type="object")
```

### 3. NPC（王様・神父）— Lua API

```lua
-- scripts/npc/king.lua
npc.say("王様", "旅人よ、記録をつけておくがよい。")
event.open_save("npc_king")

-- scripts/npc/priest.lua
npc.say("神父", "神のご加護を。")
event.open_save("npc_priest")
```

```python
# scripting/api.py
"event.open_save" → coroutine.yield("open_save", save_type)
# map_scene.py の dialogue処理で "open_save" コマンドをキャッチ
# → show_save_slot_ui(save_type)
```

---

## セーブスロット選択UI

`src/ui/save_slot_ui.py`

```
┌──────────────────────────────────────────┐
│  ▶  スロット 1    ドラゴンの洞窟  Lv.12  │
│     2026-03-18 20:00    プレイ: 1:00:00  │
├──────────────────────────────────────────┤
│     スロット 2    （データなし）          │
├──────────────────────────────────────────┤
│     スロット 3    城下町         Lv. 8   │
│     2026-03-17 15:30    プレイ: 0:30:00  │
└──────────────────────────────────────────┘
```

- **セーブ時**: スロット選択 → 既存データがある場合「上書きしますか？」→ 保存
- **ゲームオーバー時**: スロット選択UIは表示しない（`load_latest()` で自動ロード）
- `save_slot_ui.show(mode="save", save_type, callback)` で呼び出す

---

## ゲームオーバーフロー

### GameOverScene

`src/scenes/game_over_scene.py`

```
全滅検出（battle_scene._check_battle_result）
    ↓
game.change_scene("game_over")
    ↓
GameOverScene.on_enter()
  - BGM停止
  - ゲームオーバーSE再生（se_gameover）
  - フェードイン（暗い背景に「全滅した...」テキスト）
    ↓
任意キー押下
    ↓
save_manager.has_any_save() == True
    ↓
save_manager.load_latest()
save_manager.apply_game_over_penalty()
    ↓
game.change_scene("map")  ← map_scene.on_enter() が実行される
    ↓
on_enter() 完了後、update() の最初のフレームで:
  map_scene._pending_priest_dialogue フラグを確認
    ↓
True の場合:
  dialogue_renderer.show_dialogue("神父",
    "死んでしまうとはな...\nこれも神様の思し召しであろう。\nさぁ、行くがよい！！")
  フラグをクリア

### 神父セリフのフラグ伝達方法

```python
# GameOverScene → MapScene へ伝達
if save_manager.get_save_type() == "npc_priest":
    game.scenes["map"]._pending_priest_dialogue = True
game.change_scene("map")
```

`_pending_priest_dialogue` は `map_scene.__init__` で `False` に初期化し、`update()` の冒頭（フェード終了後）に確認してダイアログを発火する。`on_enter()` ではなく `update()` で処理することで、TMXロード・BGM再生・フェードイン完了後にセリフが表示される。
```

### セーブデータがない場合

ゲームオーバー後にセーブデータが存在しない場合はタイトルへ戻る。

```
save_manager.has_any_save() == False
    ↓
game.change_scene("title")
```

---

## game.playtime_seconds の追加

`game.py` に `playtime_seconds: float = 0.0` を追加する。`game.py` には `update()` メソッドが存在しないため、`run()` ループ内の `clock.tick(FPS)` 戻り値を使って加算する。

```python
# game.py の run() ループ内
dt = self.clock.tick(FPS) / 1000.0   # ミリ秒 → 秒
self.playtime_seconds += dt
```

`clock.tick(FPS)` の戻り値はすでにループ末尾で呼ばれているため、その行を `dt = self.clock.tick(FPS) / 1000.0` に置き換えるだけでよい。

---

## 実装ファイル一覧

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/world/save_manager.py` | 新規 | SaveManager（シリアライズ・ロード・ペナルティ） |
| `src/scenes/game_over_scene.py` | 新規 | GameOverScene（テキスト表示・SE・キー待ち） |
| `src/ui/save_slot_ui.py` | 新規 | スロット選択UI（セーブ時のみ） |
| `saves/` | 新規 | セーブファイル置き場（.gitignore に追加） |
| `src/game.py` | 変更 | SaveManager初期化・playtime_seconds追加・game_over登録 |
| `src/scenes/battle_scene.py` | 変更 | 全滅時に game_over シーンへ遷移 |
| `src/scenes/map_scene.py` | 変更 | セーブポイントタイル/オブジェクト判定・神父セリフ処理 |
| `src/scripting/api.py` | 変更 | `event.open_save(save_type)` Lua API追加 |

---

## スコープ外

- タイトル画面の「データをロード」機能（別タスクで対応）
- セーブデータの暗号化・改ざん防止
- クラウドセーブ
