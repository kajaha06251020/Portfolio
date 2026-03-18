# ドアシステム設計仕様書

**日付:** 2026-03-18
**対象:** FinalFantasyX-99
**ステータス:** 承認済み

---

## 概要

ワールドマップや各マップから移動できる出口（ドア）が存在しない問題を解決するため、
Tiled / pytmx を使ったドアギミックシステムを新規実装する。

ドラゴンクエスト風の動作を目標とする：
- **基本ドア** — プレイヤーが接触すると自動で開き、マップ遷移が発生する
- **鍵付きドア** — 対応する鍵アイテムを所持していれば開く（鍵は消費しない）
- **アニメーション** — 大扉はスプライトアニメーション、通常ドアはタイル消滅で表現する

---

## 既存 `locked_door` との共存方針

`GimmickManager` には既存の `type="locked_door"` が実装されている。

| 比較項目 | 既存 `locked_door`（GimmickManager） | 新 `door`（DoorManager） |
|---|---|---|
| 開け方 | アクションボタンを押す | 接触で自動開放 |
| 鍵の指定 | `key_item`（特定アイテムID） | `key_tier`（階層制・非消費） |
| 鍵の消費 | 消費する | 消費しない |
| 目的 | パズルギミック（同マップ内） | 出入口・マップ遷移 |

**共存方針:** 両者を並行して使用する。既存マップの `locked_door` は変更しない。
新しいマップの出入口・建物ドアには `door` タイプを使用する。
フラグ名前空間の衝突を避けるため、DoorManager のフラグは `dv2_<door_id>` を使用する。

---

## Tiled 設定

### オブジェクトレイヤー構成

Tiledの **Objectレイヤー（"Objects"）** に `type="door"` のオブジェクトを配置する。
通常ドアのタイル消滅用に **Tileレイヤー（"Doors"）** を別途用意する。

### プロパティ定義

`locked` プロパティは廃止。`key_tier == 0` が「鍵不要」の唯一の判定基準とする。
プロパティ名はすべて `snake_case` に統一する。

| プロパティ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| `door_id` | string | ✅ | ドアの一意ID（状態フラグ名 `dv2_<door_id>` に使用） |
| `door_animation` | bool | ✅ | `true`=スプライトアニメ、`false`=タイル消滅 |
| `key_tier` | int | ❌ | 必要な鍵のtier（1〜3、省略または0で鍵不要） |
| `dest_map` | string | ❌ | 遷移先マップID。`_prev` で前のマップへ戻る |
| `dest_x` | int | ❌ | 遷移先X座標（グリッド） |
| `dest_y` | int | ❌ | 遷移先Y座標（グリッド） |
| `entry` | string | ❌ | 遷移先の名前付きエントリーゾーンID |
| `sprite` | string | ❌ | スプライトシートのファイル名（拡張子なし） |
| `anim_frames` | int | ❌ | アニメーションのフレーム数（デフォルト: 2） |
| `anim_speed` | float | ❌ | 1フレームあたりの秒数（デフォルト: 0.12） |

### TMX 例

**通常ドア（鍵なし・タイル消滅）:**
```xml
<object type="door" x="96" y="112" width="16" height="16">
  <properties>
    <property name="door_id"        value="inn_entrance"/>
    <property name="door_animation" type="bool" value="false"/>
    <property name="key_tier"       type="int"  value="0"/>
    <property name="dest_map"       value="inn_interior"/>
    <property name="dest_x"         type="int"  value="3"/>
    <property name="dest_y"         type="int"  value="8"/>
  </properties>
</object>
```

**大扉（まほうのカギ必要・スプライトアニメ）:**
```xml
<object type="door" x="160" y="64" width="32" height="32">
  <properties>
    <property name="door_id"        value="castle_gate"/>
    <property name="door_animation" type="bool"  value="true"/>
    <property name="key_tier"       type="int"   value="2"/>
    <property name="sprite"         value="door_large"/>
    <property name="anim_frames"    type="int"   value="4"/>
    <property name="anim_speed"     type="float" value="0.12"/>
    <property name="dest_map"       value="castle_interior"/>
    <property name="dest_x"         type="int"   value="8"/>
    <property name="dest_y"         type="int"   value="10"/>
  </properties>
</object>
```

**出口ドア（前のマップへ戻る）:**
```xml
<object type="door" x="48" y="128" width="16" height="16">
  <properties>
    <property name="door_id"        value="inn_exit"/>
    <property name="door_animation" type="bool" value="false"/>
    <property name="key_tier"       type="int"  value="0"/>
    <property name="dest_map"       value="_prev"/>
  </properties>
</object>
```

---

## 鍵システム

### 鍵の階層（DQスタイル・消費なし）

| アイテムID | 名前 | tier | 開けられる扉 |
|---|---|---|---|
| `thieves_key` | とうぞくのカギ | 1 | tier 1 |
| `magic_key` | まほうのカギ | 2 | tier 1〜2 |
| `final_key` | さいごのカギ | 3 | tier 1〜3（全て） |

上位の鍵は下位の扉も開けられる。鍵はインベントリから消費されない。

### 判定ロジック

インベントリは `game.inventory`（`dict[str, int]` 型、`{item_id: count}`）を渡す。

```python
KEY_TIER_MAP = {
    "thieves_key": 1,
    "magic_key":   2,
    "final_key":   3,
}

def _get_player_key_tier(inventory: dict) -> int:
    """所持している最高ランクの鍵のtierを返す"""
    best = 0
    for key_id, tier in KEY_TIER_MAP.items():
        if inventory.get(key_id, 0) > 0:
            best = max(best, tier)
    return best

def can_open(door: Door, inventory: dict) -> bool:
    if door.key_tier == 0:
        return True   # 鍵不要
    return _get_player_key_tier(inventory) >= door.key_tier
```

### メッセージ

```python
def get_locked_message(door: Door, inventory) -> str:
    player_tier = _get_player_key_tier(inventory)
    if player_tier == 0:
        return "カギが必要だ！"
    else:
        return "持っているカギでは開かなかった！"
```

---

## アーキテクチャ

### 新規ファイル

```
src/world/door_manager.py    # DoorManager 本体
assets/images/doors/         # ドアスプライト格納ディレクトリ
  door_large.png             # 大扉スプライトシート（横N枚・1行）
```

### 変更ファイル

```
src/scenes/map_scene.py      # DoorManager 統合・遷移処理・_redraw_tmx_surface() 追加
data/items.json              # 鍵3種を追加
```

### データクラス

```python
@dataclass
class Door:
    door_id: str
    x: int                   # グリッド座標
    y: int
    animated: bool           # door_animation プロパティ
    key_tier: int            # 0 = 鍵不要
    dest_map: str | None     # "_prev" で前のマップへ戻る
    dest_x: int | None
    dest_y: int | None
    entry: str | None
    sprite: str | None
    anim_frames: int = 2
    anim_speed: float = 0.12
    # 実行時状態
    is_open: bool = False
    anim_frame: float = 0.0
    anim_playing: bool = False

@dataclass
class DoorResult:
    status: str              # "opened" | "locked_no_key" | "locked_wrong_key"
    message: str | None
    dest_map: str | None
    dest_x: int | None
    dest_y: int | None
    entry: str | None
```

### DoorManager インターフェース

```python
class DoorManager:
    def load_from_tmx(self, tmx_data) -> None
    def is_tile_blocked(self, x: int, y: int) -> bool
        # 閉じているドアのみ True を返す。is_open=True のドアは False
    def try_open(self, x: int, y: int, inventory) -> DoorResult | None
        # ドアがない座標では None を返す
        # is_tile_blocked() が True の座標でのみ呼ばれることを前提とする
    def update(self, dt: float) -> None
    def draw(self, surface, cam_x: int, cam_y: int) -> None
    def is_animating(self) -> bool
    def get_door_at(self, x: int, y: int) -> Door | None
```

---

## MapScene 統合

### `_try_player_step()` の変更

現状の `_try_player_step()` は移動失敗時に何も返さない。
ドア処理を割り込ませるため、`blocked_checker` 内でドアチェックを行う。

```python
def _make_blocked_checker(self):
    def checker(x, y, direction=None):
        # ... 既存チェック（NPC, chest, gimmick, tile） ...

        # ドアチェック：閉じているドアに接触した場合
        if self.door_manager.is_tile_blocked(x, y):
            result = self.door_manager.try_open(x, y, self.game.inventory)
            if result is None:
                return True   # ドアだが開けられない（フォールバック）
            if result.status in ("locked_no_key", "locked_wrong_key"):
                self.dialogue_renderer.show_dialogue("", result.message)
                return True   # 移動ブロック
            # status == "opened": ドアが開いた
            if result.dest_map:
                self._begin_door_transition(result)
            return False   # 通過OK（アニメ完了後に遷移コールバックが発火）
        return False
    return checker
```

### 処理フロー

```
プレイヤーが移動キー押下
        ↓
_try_player_step(dx, dy) → blocked_checker(next_x, next_y)
        ↓
door_manager.is_tile_blocked(next_x, next_y)
   ├── False（ドアなし or 開いている）→ 通常移動
   └── True（閉じたドアあり）
              ↓
        door_manager.try_open(next_x, next_y, inventory)
              ├── locked_no_key    → メッセージ「カギが必要だ！」→ 移動ブロック
              ├── locked_wrong_key → メッセージ「持っているカギでは開かなかった！」→ 移動ブロック
              └── opened
                    ├── door_animation=false → タイル消滅（即時）→ 通過OK
                    └── door_animation=true  → アニメ開始 → 通過OK
                                                  ↓ アニメ完了後コールバック
                              dest_map あり → _begin_door_transition()
                              dest_map なし → 開いたまま（同マップ内扉）
```

### アニメーション中のロック

```python
def update(self, dt):
    self.door_manager.update(dt)
    if self.door_manager.is_animating():
        return   # 入力・移動を全てロック
```

### `_prev` 遷移

既存の `return_points` 辞書を使用する。
`return_points` は `{town_or_dungeon_map_id: {"map_id": field_map_id, "x": int, "y": int}}` の構造。

```python
def _begin_door_transition(self, result: DoorResult):
    dest = result.dest_map
    dest_x = result.dest_x
    dest_y = result.dest_y

    if dest == "_prev":
        rp = self.return_points.get(self.current_map)
        if rp:
            dest   = rp["map_id"]
            dest_x = rp.get("x")
            dest_y = rp.get("y")
        else:
            # フォールバック: return_points が未記録の場合は遷移しない
            return

    self._begin_transition({
        "kind":   "map",
        "map_id": dest,
        "dest_x": dest_x,
        "dest_y": dest_y,
        "entry":  result.entry,
    })
```

---

## 描画方式

### タイル消滅型（`door_animation=false`）

1. Tiledの `"Doors"` Tileレイヤーにドアタイルを配置する
2. `try_open()` 成功時に `layer.data[y][x] = None` で消去する
   - pytmx の `TiledTileLayer.data` はミュータブルなリストであり書き換え可能
3. `MapScene._redraw_tmx_surface()` でサーフェスを再描画する
   - このメソッドは `MapScene` に新規追加する（既存の `_build_tmx_surface(tw, th)` のラッパー）
   - `_build_tmx_surface` はスケール後のピクセルサイズを引数に取り、内部で `self.tmx_surface` に直接代入する
   ```python
   def _redraw_tmx_surface(self):
       tw = self.tmx_data.tilewidth * self.tmx_tile_scale
       th = self.tmx_data.tileheight * self.tmx_tile_scale
       self._build_tmx_surface(tw, th)
   ```
4. WorldStateManagerに `dv2_<door_id> = True` を保存する

### スプライトアニメーション型（`door_animation=true`）

スプライトシート形式（横にフレームを並べた1行画像）：

```
door_large.png:
┌──────┬──────┬──────┬──────┐
│ f=0  │ f=1  │ f=2  │ f=3  │  ← 閉 → 開
└──────┴──────┴──────┴──────┘
```

- `update(dt)` でフレームをインクリメント
- 最終フレーム到達 → `is_open=True`、`_on_door_animation_complete(door)` をコールバック
- 完全に開いた後は描画をスキップ（下のタイルレイヤーが見える）

アニメーション完了後の遷移は `DoorManager` に登録したコールバックで通知する。

```python
# DoorManager 側：コールバックの登録と呼び出し
class DoorManager:
    def __init__(self):
        self.on_door_opened = None   # MapScene が callable を代入する

    def _finish_animation(self, door: Door):
        door.is_open = True
        door.anim_playing = False
        if self.on_door_opened:
            self.on_door_opened(door)   # MapScene へ通知

# MapScene 側：コールバックの登録
self.door_manager.on_door_opened = self._on_door_animation_complete

def _on_door_animation_complete(self, door: Door):
    """アニメ完了後に状態保存 + マップ遷移を発火する"""
    self.world_state.set_flag(f"dv2_{door.door_id}", True)
    if door.dest_map:
        result = DoorResult(
            status="opened", message=None,
            dest_map=door.dest_map, dest_x=door.dest_x,
            dest_y=door.dest_y, entry=door.entry,
        )
        self._begin_door_transition(result)
```

---

## 状態永続化

WorldStateManagerのフラグで一度開けたドアを記憶する：

```
flag: dv2_<door_id> = True
```

`GimmickManager` の `door_<id>` フラグとは名前空間を分離する（`dv2_` プレフィックス）。
マップロード時にフラグを確認し、`True` であれば `is_open=True` で初期化。
一度開けたドアは再訪時も開いたまま。

---

## 実装対象外（スコープ外）

- ドアが閉じる動作（開いたら永続的に開いたまま）
- ドアのノック音・BGM変化などの音響演出（別タスクで対応）
- Lua スクリプトからのドア制御 API（必要になれば追加）
- 既存 `GimmickManager.locked_door` の DoorManager への移行（既存マップはそのまま）

---

## 実装ファイル一覧

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/world/door_manager.py` | 新規 | DoorManager・Door・DoorResult クラス |
| `src/scenes/map_scene.py` | 変更 | DoorManager 統合、`_begin_door_transition()`、`_redraw_tmx_surface()` 追加 |
| `data/items.json` | 変更 | とうぞくのカギ・まほうのカギ・さいごのカギ追加 |
| `assets/images/doors/` | 新規 | スプライト画像格納ディレクトリ |
