# 町探索・ショップ・宝箱・ダンジョンギミック 設計仕様書

## 概要

地上層(physical)の探索体験を充実させる。町の建物への出入り、ショップでの売買、
宿屋での回復、宝箱の取得、ダンジョンギミック(スイッチ・落とし穴・鍵付きドア・一方通行)を実装する。

**アプローチ:** シーンベース(Approach A) — ショップは独立した `ShopScene` として実装。
FF1〜6風のワールドマップ方式。

**実装順序:** 町マップ+ショップ → 宿屋 → 宝箱 → ダンジョンギミック

---

## 0. シーンスタック (アーキテクチャ変更)

### 課題

現在の `Game.change_scene()` はシーンを完全に切り替える。ショップのように
「MapScene を保持したまま別シーンを開き、終了後に戻る」パターンに対応できない。
対話コルーチンの状態も失われる。

### 解決: push_scene / pop_scene

`Game` クラスにシーンスタックを追加する:

```python
class Game:
    def __init__(self):
        # 既存
        self.scenes = { ... }
        self.current_scene = "title"

        # 新規: シーンスタック
        self._scene_stack: list[str] = []

    def push_scene(self, scene_name: str) -> None:
        """現在のシーンをスタックに退避し、新しいシーンに遷移。"""
        self._scene_stack.append(self.current_scene)
        self.current_scene = scene_name
        self.scenes[scene_name].on_enter()

    def pop_scene(self) -> None:
        """スタックから前のシーンを復帰。"""
        if self._scene_stack:
            self.current_scene = self._scene_stack.pop()
            self.scenes[self.current_scene].on_resume()  # 新規ライフサイクル

    def change_scene(self, scene_name: str) -> None:
        """既存: スタックをクリアして完全遷移(タイトル→マップ等)。"""
        self._scene_stack.clear()
        self.current_scene = scene_name
        self.scenes[scene_name].on_enter()
```

`BaseScene` に `on_resume()` メソッドを追加(デフォルト空):
- MapScene の `on_resume()` でコルーチンの resume を再開

使い方:
- ショップ: `game.push_scene("shop")` → ShopScene 終了時 `game.pop_scene()` → MapScene に戻る
- メニュー: 既存の `change_scene("menu")` はそのまま(メニューは完全遷移)
- バトル: 既存の `change_scene("battle")` はそのまま

---

## 1. 町マップ構造

### 方針

建物内部を個別TMXマップとして作成し、既存のワープシステムで接続する。
新規コードは不要 — TMXにワープオブジェクトを配置するだけで動作する。

### マップ構成

```
castle_town.tmx (既存)
  ├── ドア → castle_town_weapon.tmx  (武器屋内部, 8x6)
  ├── ドア → castle_town_armor.tmx   (防具屋内部, 8x6)
  ├── ドア → castle_town_item.tmx    (道具屋内部, 8x6)
  ├── ドア → castle_town_inn.tmx     (宿屋内部, 8x6)
  └── ドア → castle_town_magic.tmx   (魔法屋内部, 8x6)
```

各建物内部:
- カウンター奥にショップ店員NPC
- 入口にワープオブジェクト(町マップに戻る)
- encounter_rate: 0 (安全地帯)

### maps.json 追加例

既存の maps.json は配列形式 (`{"maps": [...]}`) なので、それに合わせる:

```json
{
  "map_id": "castle_town_weapon",
  "name": "Weapon Shop",
  "display_name": "城下町 武器屋",
  "tmx": "castle_town_weapon.tmx",
  "width": 8,
  "height": 6,
  "encounter_rate": 0,
  "music": "town",
  "safe_zones": [],
  "encounter_zones": [],
  "transitions": [],
  "npcs": ["shopkeeper_weapon"]
}
```

### TMXフォールバック

TMXファイルが存在しない場合、コードで簡易マップを生成する。
床タイル+壁タイル+カウンターの最小構成で、開発中はこれで動作確認可能。

---

## 2. ショップシステム

### 新規ファイル

- `src/scenes/shop_scene.py` — ShopScene クラス
- `data/shops.json` — ショップ品揃え定義

### データ形式 (data/shops.json)

既存の `data/items.json` のアイテムIDを使用する:

```json
{
  "castle_town_weapon": {
    "name": "城下町 武器屋",
    "type": "weapon",
    "items": ["sword_steel", "sword_mythril", "axe_battle", "staff_magic"],
    "sell_rate": 0.5
  },
  "castle_town_armor": {
    "name": "城下町 防具屋",
    "type": "armor",
    "items": ["helmet_steel", "helmet_mythril", "armor_leather", "armor_plate"],
    "sell_rate": 0.5
  },
  "castle_town_item": {
    "name": "城下町 道具屋",
    "type": "item",
    "items": ["potion", "potion_high", "antidote", "ether", "eye_drops", "full_life"],
    "sell_rate": 0.5
  },
  "castle_town_magic": {
    "name": "城下町 魔法屋",
    "type": "special",
    "items": ["scroll_fire", "scroll_ice", "scroll_thunder"],
    "sell_rate": 0.25
  }
}
```

**前提条件:** 魔法屋の巻物アイテム (`scroll_fire`, `scroll_ice`, `scroll_thunder`) は
`data/items.json` の `consumable` セクションに追加が必要:

```json
{
  "item_id": "scroll_fire",
  "name": "ファイアの書",
  "description": "ファイアの魔法を習得する巻物。",
  "price": 500,
  "effect": "teach_ability",
  "power": null,
  "ability_id": "fire",
  "target": "single_ally",
  "battle_use": false,
  "field_use": true
}
```

鍵アイテムも `consumable` セクションに追加:

```json
{
  "item_id": "silver_key",
  "name": "銀の鍵",
  "description": "銀色に光る鍵。特定の宝箱を開けられる。",
  "price": 0,
  "effect": "key_item",
  "power": null,
  "target": null,
  "battle_use": false,
  "field_use": false
}
```

### ShopScene 状態遷移

```
main (買う / 売る / やめる)
  ├── buy → アイテム一覧(価格付き) → buy_confirm (個数選択) → 購入完了 → buy に戻る
  ├── sell → 所持品一覧(売値付き) → sell_confirm (個数選択) → 売却完了 → sell に戻る
  └── exit → game.pop_scene() で MapScene に戻る
```

### ShopScene の生成と初期化

```python
class ShopScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self._shop_id: str = ""
        self._shop_data: dict = {}
        # ... UI state

    def open(self, shop_id: str) -> None:
        """ショップを開く。push_scene の前に呼ぶ。"""
        self._shop_id = shop_id
        self._shop_data = self._load_shop(shop_id)

    def on_exit(self) -> None:
        """ショップ終了時。pop_scene() を呼ぶ。"""
        self.game.pop_scene()
```

### UI レイアウト (FF風)

```
┌───────────┬──────────────────────────┐
│ 買う      │ スチールソード      100G  │
│ 売る      │ ミスリルソード      300G  │
│ やめる    │ バトルアックス      280G  │
│           │ 魔法の杖            250G  │
├───────────┴──────────────────────────┤
│ ATK+8  現在:ATK+5  装備可能:全員     │  ← 装備中との比較
├──────────────────────────────────────┤
│ 所持金: 1500G                        │
└──────────────────────────────────────┘
```

### 購入フロー

1. アイテム選択 → 個数入力(↑↓で1〜99、所持金範囲内に制限)
2. 確認 → 所持金減算、`game.inventory` に追加
3. 購入メッセージ表示 → アイテム一覧に戻る
4. 存在しないアイテムIDの場合はログ警告し一覧から除外

### 売却フロー

1. 所持品から選択 → 売値表示 (`price * sell_rate`、切り捨て)
2. 個数入力 → 確認 → 所持金加算、インベントリから削除
3. 装備中アイテムは売却不可(警告表示)

### 装備比較表示

武器・防具選択時、パーティメンバーの現在装備との差分を表示:
- `ATK +8 → +14 (+6)` のように差分を色付き表示(上昇=緑、下降=赤)
- レベル不足の場合はグレーアウト + "Lv不足" 表示

※ジョブ制限は現状 `required_job: null` のため、将来対応。今回は実装しない。

### Lua API 拡張: npc.open_shop

```lua
-- scripts/npc/shopkeeper_weapon.lua
function on_talk()
    npc.say("武器屋", "いらっしゃい！何をお探しかな？")
    npc.open_shop("castle_town_weapon")
end
```

`npc.open_shop(shop_id)`:
- coroutine が `("shop", shop_id)` を yield
- MapScene がこれを検知し ShopScene に遷移 (push_scene)
- ShopScene 終了後 pop_scene → MapScene.on_resume() → coroutine を resume

---

## 3. 宿屋システム

### 方針

ShopScene ではなく、Lua 対話スクリプト + ScriptAPI で完結するシンプルな実装。

### データ (data/shops.json に統合)

```json
{
  "castle_town_inn": {
    "type": "inn",
    "name": "城下町 宿屋",
    "price": 50
  }
}
```

### Lua スクリプト例

```lua
-- scripts/npc/innkeeper.lua
function on_talk()
    npc.say("宿屋の主人", "一晩50ゴールドです。お泊まりになりますか？")
    local choice = npc.choice({"はい", "いいえ"})
    if choice == 1 then
        if party.get_gold() >= 50 then
            party.remove_gold(50)
            party.rest()
            event.fade_out()
            event.wait(1.0)
            event.fade_in()
            npc.say("宿屋の主人", "ゆっくりお休みいただけましたか？")
        else
            npc.say("宿屋の主人", "お金が足りないようですね…")
        end
    else
        npc.say("宿屋の主人", "またのお越しを。")
    end
end
```

### ScriptAPI 関数 (新規・既存整理)

| 名前空間 | 関数 | 状態 | 説明 |
|----------|------|------|------|
| `party` | `add_gold(n)` | **既存** | 所持金加算 (負の値で減算、0にclamp) |
| `party` | `get_gold()` | 新規 | 所持金取得。`return game.gold` |
| `party` | `remove_gold(n)` | 新規 | 所持金減算。内部的に `add_gold(-n)` を呼ぶ |
| `party` | `rest()` | 新規 | パーティ全員回復 (下記参照) |
| `event` | `fade_out()` | 新規 | 画面フェードアウト (yield) |
| `event` | `fade_in()` | 新規 | 画面フェードイン (yield) |
| `event` | `wait(sec)` | 新規 | 指定秒数待機 (yield) |
| `npc` | `open_shop(shop_id)` | 新規 | ショップ画面を開く (yield) |

### party.rest() の具体的な動作

```python
def party_rest():
    for member in game.party:  # list[dict]
        member["hp"] = member["max_hp"]
        member["mp"] = member["max_mp"]
        # 状態異常は回復しない (宿屋は HP/MP のみ)
```

---

## 4. MapScene の _advance_dialogue 拡張

### 課題

現在の `_advance_dialogue()` (map_scene.py:508-529) は `"say"` と `"choice"` のみ対応。
新しいコマンド (`"shop"`, `"fade_out"`, `"fade_in"`, `"wait"`) を追加する必要がある。

### 修正方針

```python
# map_scene.py: _advance_dialogue() 内の命令処理部分

if isinstance(yielded, tuple):
    cmd = yielded[0]
    if cmd == "say" and len(yielded) >= 3:
        # 既存: 対話表示
        speaker = str(yielded[1])
        text = str(yielded[2])
        self.dialogue_renderer.show_dialogue(speaker, text)

    elif cmd == "choice" and len(yielded) >= 2:
        # 既存: 選択肢表示
        options_raw = yielded[1]
        options = self._lua_table_to_list(options_raw)
        self.dialogue_renderer.show_choice(options)

    elif cmd == "shop" and len(yielded) >= 2:
        # 新規: ショップ遷移
        shop_id = str(yielded[1])
        shop_scene = self.game.scenes.get("shop")
        if shop_scene:
            shop_scene.open(shop_id)
            self.game.push_scene("shop")
            # コルーチンは保持したまま — on_resume() で resume される
        else:
            logger.warning("ShopScene not found")

    elif cmd == "fade_out":
        # 新規: スクリプトフェードアウト
        # 既存の fade_surface / fade_alpha を再利用
        self._start_script_fade("out")

    elif cmd == "fade_in":
        # 新規: スクリプトフェードイン
        self._start_script_fade("in")

    elif cmd == "wait" and len(yielded) >= 2:
        # 新規: 待機
        self._script_wait_timer = float(yielded[1])

    else:
        logger.warning("Unknown dialogue command: %s", cmd)
```

### フェード/ウェイトの実装

スクリプトフェードは、マップ遷移用の既存フェードシステム (`fade_surface`, `fade_alpha`,
`fade_state`) とは**別の状態変数**を使う。マップ遷移フェードとスクリプトフェードが
干渉しないようにする:

```python
# 新規状態変数
self._script_fade_state: str | None = None   # "out" / "in" / None
self._script_fade_alpha: int = 0
self._script_wait_timer: float = 0.0
```

`update()` 内でこれらを処理し、完了したらコルーチンを resume する。

### MapScene.on_resume()

```python
def on_resume(self):
    """push_scene から戻った時の処理。"""
    # ショップ終了後: コルーチンを再開
    if self.dialogue_coroutine is not None:
        self._advance_dialogue()
```

---

## 5. 宝箱システム

### 新規ファイル

- `src/world/treasure.py` — TreasureManager, ChestData, ChestResult

### TMX オブジェクト定義

```xml
<!-- 通常: アイテム宝箱 -->
<object name="Chest" type="chest" x="64" y="128" width="16" height="16">
  <property name="chest_id" value="cave_01"/>
  <property name="item" value="potion"/>
  <property name="quantity" type="int" value="3"/>
</object>

<!-- ゴールド宝箱 -->
<object name="Chest" type="chest" x="48" y="80" width="16" height="16">
  <property name="chest_id" value="cave_04"/>
  <property name="gold" type="int" value="500"/>
</object>

<!-- 鍵付き宝箱 -->
<object name="Chest" type="chest" x="96" y="64" width="16" height="16">
  <property name="chest_id" value="cave_02"/>
  <property name="item" value="sword_mythril"/>
  <property name="locked" type="bool" value="true"/>
  <property name="key_item" value="silver_key"/>
</object>

<!-- ミミック宝箱 (戦闘のみ、中身は無し) -->
<object name="Chest" type="chest" x="128" y="96" width="16" height="16">
  <property name="chest_id" value="cave_03"/>
  <property name="mimic" type="bool" value="true"/>
  <property name="enemy_group" value="mimic_01"/>
</object>
```

### 状態管理

- 開封状態: `WorldStateManager` の `flags.chest_<chest_id> = true`
- マップ再訪問・セーブ/ロードで保持

### インタラクション フロー

```
宝箱の前でアクションボタン
  ├── 開封済み → "からっぽだ。"
  ├── 鍵付き
  │     ├── 鍵あり → 鍵消費 (party.remove_item) → 開封
  │     └── 鍵なし → "鍵がかかっている！"
  ├── ミミック → バトルシーン遷移 → 戦闘のみ (中身なし、戦闘経験値が報酬)
  └── 通常 → アイテム/ゴールド取得
        → "ポーション×3 を手に入れた！"
        → フラグ設定
```

### ChestResult 定義

```python
from dataclasses import dataclass

@dataclass
class ChestResult:
    status: str         # "opened", "locked", "mimic", "already_opened"
    item: str | None    # 取得アイテムID (None if gold/mimic/locked)
    quantity: int       # 取得数
    gold: int           # 取得ゴールド
    enemy_group: str | None  # ミミックの敵グループID
    message: str        # 表示メッセージ ("ポーション×3 を手に入れた！" 等)
```

### TreasureManager インターフェース

```python
class ChestData:
    chest_id: str
    grid_x: int
    grid_y: int
    item: str | None
    quantity: int
    gold: int
    locked: bool
    key_item: str | None
    mimic: bool
    enemy_group: str | None

class TreasureManager:
    def __init__(self, world_state_manager, game):
        self._wsm = world_state_manager
        self._game = game  # inventory access for key checks

    def load_chests(self, map_id, tmx_data) -> None
    def get_chests(self) -> list[ChestData]
    def is_opened(self, chest_id) -> bool
    def interact(self, chest_id) -> ChestResult
    def is_chest_at(self, x, y) -> ChestData | None
```

`interact()` の動作:
- `is_opened()` チェック → `ChestResult(status="already_opened")`
- `locked` チェック → インベントリに `key_item` があるか → あれば消費して開封
- `mimic` チェック → `ChestResult(status="mimic", enemy_group=...)` 返す (バトル遷移はMapScene側)
- 通常 → アイテム/ゴールドを `game.inventory`/`game.gold` に加算、フラグ設定

### 描画

- 未開封: 茶色の矩形(箱) + 黄色の帯
- 開封済み: 暗い茶色の矩形(開いた箱)
- 宝箱タイルは通行不可

---

## 6. ダンジョンギミック

### 新規ファイル

- `src/world/gimmick_manager.py` — GimmickManager

### ギミック種別

#### 6.1 スイッチ & 連動ドア

TMX定義:
```xml
<object name="Switch" type="switch" x="96" y="64" width="16" height="16">
  <property name="switch_id" value="cave_sw_01"/>
  <property name="target" value="cave_door_01"/>
</object>

<object name="Door" type="switch_door" x="128" y="96" width="16" height="16">
  <property name="door_id" value="cave_door_01"/>
  <property name="default" value="closed"/>
</object>
```

動作:
- プレイヤーがスイッチ上に乗る or アクションボタン → 対応ドア開閉トグル
- 閉じたドアは壁扱い(通行不可)
- 状態: `flags.switch_<switch_id>` で永続化。値は `true`(ON) / `false`(OFF)
  - デフォルト `closed` + フラグ `true` → ドア開
  - デフォルト `closed` + フラグ `false` or 未設定 → ドア閉
- 描画: スイッチ=床の丸印(ON時は色変化)、ドア=壁色(閉) or 通路色(開)

#### 6.2 落とし穴

```xml
<object name="Pitfall" type="pitfall" x="80" y="48" width="16" height="16">
  <property name="pitfall_id" value="cave_pit_01"/>
  <property name="dest_map" value="dragon_cave_b2"/>
  <property name="dest_x" type="int" value="5"/>
  <property name="dest_y" type="int" value="8"/>
  <property name="visible" type="bool" value="false"/>
</object>
```

動作:
- `visible=false`: 見えない穴。踏むと落下演出(画面揺れ+暗転) → 下の階に遷移
- `visible=true`: 見える穴。通行不可
- 一度落ちたら `flags.pitfall_<id>_revealed = true` → 以降は見える(通行不可に変化)

#### 6.3 一方通行ドア

```xml
<object name="OneWay" type="one_way" x="64" y="32" width="16" height="16">
  <property name="direction" value="down"/>
</object>
```

動作:
- 指定方向からのみ通行可能、逆方向は壁扱い
- ダンジョンのショートカットや戻れないルート分岐に使用
- 描画: 矢印マーク

#### 6.4 鍵付きドア

```xml
<object name="LockedDoor" type="locked_door" x="112" y="48" width="16" height="16">
  <property name="door_id" value="cave_locked_01"/>
  <property name="key_item" value="cave_key"/>
</object>
```

動作:
- アクションボタン → インベントリに鍵があるか確認
- 鍵消費 → 開放、`flags.door_<door_id> = true` で永続化
- 描画: 鍵マーク付き壁 → 開放後は通路

### GimmickManager インターフェース

```python
@dataclass
class GimmickEvent:
    type: str          # "switch_toggle", "pitfall", "locked_door", "one_way_block", "door_opened"
    data: dict         # ギミック固有のデータ
    message: str = ""  # 表示メッセージ (あれば)

class GimmickManager:
    def __init__(self, world_state_manager, game):
        self._wsm = world_state_manager
        self._game = game  # inventory access for key checks

    def load_gimmicks(self, map_id, tmx_data) -> None
    def is_tile_blocked(self, x, y, move_direction: str | None = None) -> bool
    def on_player_step(self, x, y) -> GimmickEvent | None
    def interact(self, x, y, direction) -> GimmickEvent | None
```

### MapScene との統合: 方向パラメータ対応

現在の `_is_blocked_tile(tile_x, tile_y)` に方向パラメータを追加:

```python
def _is_blocked_tile(self, tile_x: int, tile_y: int, direction: str | None = None) -> bool:
    # NPCチェック (既存)
    for npc in self.current_npcs:
        if npc.grid_x == tile_x and npc.grid_y == tile_y:
            return True

    # 宝箱チェック (新規)
    if self.treasure_manager and self.treasure_manager.is_chest_at(tile_x, tile_y):
        return True

    # ギミックチェック (新規)
    if self.gimmick_manager and self.gimmick_manager.is_tile_blocked(tile_x, tile_y, direction):
        return True

    # TMXタイルチェック (既存)
    ...
```

`_try_player_step` の修正:

```python
def _try_player_step(self, dx: int, dy: int):
    # 移動方向を算出
    if dx > 0: direction = "right"
    elif dx < 0: direction = "left"
    elif dy > 0: direction = "down"
    else: direction = "up"

    # blocked_checker に方向を渡す
    target_x = self.player.grid_x + dx
    target_y = self.player.grid_y + dy
    if self._is_blocked_tile(target_x, target_y, direction):
        return
    # ... 既存の移動処理
```

注意: `Player.try_move_grid()` の `blocked_checker` コールバック引数も
`(x, y)` → `(x, y, direction=None)` に変更する。既存の呼び出し元は
`direction` を渡さなければ従来通り動作する(後方互換)。

その他の統合:
- `update()` 内で `on_player_step()` をチェック(落とし穴判定)
- アクションボタンで `interact()` をチェック(スイッチ/鍵付きドア)
- メッセージ表示は `dialogue_renderer.show_dialogue("", message)` で再利用

---

## 新規ファイル一覧

| ファイル | 説明 |
|---------|------|
| `src/scenes/shop_scene.py` | ショップ画面(買う/売る/装備比較) |
| `src/world/treasure.py` | 宝箱管理(ChestData, ChestResult, TreasureManager) |
| `src/world/gimmick_manager.py` | ダンジョンギミック管理 |
| `data/shops.json` | ショップ品揃え + 宿屋定義 |
| `scripts/npc/shopkeeper_weapon.lua` | 武器屋店員スクリプト |
| `scripts/npc/shopkeeper_armor.lua` | 防具屋店員スクリプト |
| `scripts/npc/shopkeeper_item.lua` | 道具屋店員スクリプト |
| `scripts/npc/shopkeeper_magic.lua` | 魔法屋店員スクリプト |
| `scripts/npc/innkeeper.lua` | 宿屋スクリプト |

## 既存ファイル修正一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/game.py` | シーンスタック追加 (`push_scene`/`pop_scene`)、ShopScene/TreasureManager/GimmickManager 初期化 |
| `src/scenes/base_scene.py` | `on_resume()` メソッド追加 |
| `src/scenes/map_scene.py` | `_advance_dialogue` に shop/fade/wait コマンド追加、`_is_blocked_tile` に direction 追加、`_try_player_step` 修正、宝箱/ギミック統合、`on_resume()` 実装 |
| `src/entities/player.py` | `try_move_grid()` の `blocked_checker` 引数に direction 対応 |
| `src/scripting/api.py` | `party.get_gold`/`remove_gold`/`rest`、`event.fade_out`/`fade_in`/`wait`、`npc.open_shop` |
| `data/items.json` | 巻物アイテム (scroll_fire/ice/thunder)、鍵アイテム (silver_key, cave_key) 追加 |
| `data/maps.json` | 建物内部マップ定義追加 (配列形式) |
| `data/npcs.json` | ショップ店員・宿屋NPC追加 |
