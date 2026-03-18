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

## Tiled 設定

### オブジェクトレイヤー構成

Tiledの **Objectレイヤー（"Objects"）** に `type="door"` のオブジェクトを配置する。
通常ドアのタイル消滅用に **Tileレイヤー（"Doors"）** を別途用意する。

### プロパティ定義

| プロパティ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| `door_id` | string | ✅ | ドアの一意ID（状態管理に使用） |
| `DoorAnimation` | bool | ✅ | `true`=スプライトアニメ、`false`=タイル消滅 |
| `locked` | bool | ✅ | 鍵が必要かどうか |
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
    <property name="door_id"       value="inn_entrance"/>
    <property name="DoorAnimation" type="bool" value="false"/>
    <property name="locked"        type="bool" value="false"/>
    <property name="dest_map"      value="inn_interior"/>
    <property name="dest_x"        type="int"  value="3"/>
    <property name="dest_y"        type="int"  value="8"/>
  </properties>
</object>
```

**大扉（まほうのカギ必要・スプライトアニメ）:**
```xml
<object type="door" x="160" y="64" width="32" height="32">
  <properties>
    <property name="door_id"       value="castle_gate"/>
    <property name="DoorAnimation" type="bool"  value="true"/>
    <property name="locked"        type="bool"  value="true"/>
    <property name="key_tier"      type="int"   value="2"/>
    <property name="sprite"        value="door_large"/>
    <property name="anim_frames"   type="int"   value="4"/>
    <property name="anim_speed"    type="float" value="0.12"/>
    <property name="dest_map"      value="castle_interior"/>
    <property name="dest_x"        type="int"   value="8"/>
    <property name="dest_y"        type="int"   value="10"/>
  </properties>
</object>
```

**出口ドア（前のマップへ戻る）:**
```xml
<object type="door" x="48" y="128" width="16" height="16">
  <properties>
    <property name="door_id"       value="inn_exit"/>
    <property name="DoorAnimation" type="bool" value="false"/>
    <property name="locked"        type="bool" value="false"/>
    <property name="dest_map"      value="_prev"/>
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

```python
KEY_TIER_MAP = {
    "thieves_key": 1,
    "magic_key":   2,
    "final_key":   3,
}

def _get_player_key_tier(inventory) -> int:
    """所持している最高ランクの鍵のtierを返す"""
    best = 0
    for key_id, tier in KEY_TIER_MAP.items():
        if inventory.has_item(key_id):
            best = max(best, tier)
    return best

def can_open(door: Door, inventory) -> bool:
    if door.key_tier == 0:
        return True
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
src/scenes/map_scene.py      # DoorManager 統合・遷移処理
data/items.json              # 鍵3種を追加
```

### データクラス

```python
@dataclass
class Door:
    door_id: str
    x: int                   # グリッド座標
    y: int
    animated: bool           # DoorAnimation プロパティ
    locked: bool
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
    status: str              # "opened" | "locked_no_key" | "locked_wrong_key" | "already_open"
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
    def try_open(self, x: int, y: int, inventory) -> DoorResult | None
    def update(self, dt: float) -> None
    def draw(self, surface, cam_x: int, cam_y: int) -> None
    def is_animating(self) -> bool
    def get_door_at(self, x: int, y: int) -> Door | None
```

---

## MapScene 統合

### 処理フロー

```
プレイヤーが移動キー押下
        ↓
_try_player_step(dx, dy)
        ↓
blocked_checker(next_x, next_y)
        ↓
door_manager.is_tile_blocked(next_x, next_y)
   ├── False（開いている）→ 通常移動（スルー）
   └── True（閉じている）→ 移動ブロック
              ↓
        door_manager.try_open(next_x, next_y, inventory)
              ├── locked_no_key    → メッセージ「カギが必要だ！」
              ├── locked_wrong_key → メッセージ「持っているカギでは開かなかった！」
              ├── already_open     → 通過OK（念のため）
              └── opened
                    ├── DoorAnimation=false → タイル消滅（即時）
                    └── DoorAnimation=true  → アニメ開始（完了後コールバック）
                              ↓ アニメ完了 or 即時
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

```python
def _begin_door_transition(self, result: DoorResult):
    dest = result.dest_map
    if dest == "_prev":
        dest = self.return_map   # MapScene が管理する「前のマップID」
    self._begin_transition({
        "kind":   "map",
        "map_id": dest,
        "dest_x": result.dest_x,
        "dest_y": result.dest_y,
        "entry":  result.entry,
    })
```

---

## 描画方式

### タイル消滅型（`DoorAnimation=false`）

1. Tiledの `"Doors"` Tileレイヤーにドアタイルを配置
2. `try_open()` 成功時に `layer.data[y][x] = None` で消去
3. `_redraw_tmx_surface()` でサーフェスを再描画
4. WorldStateManagerに `door_<id> = True` を保存

### スプライトアニメーション型（`DoorAnimation=true`）

スプライトシート形式（横にフレームを並べた1行画像）：

```
door_large.png:
┌──────┬──────┬──────┬──────┐
│ f=0  │ f=1  │ f=2  │ f=3  │  ← 閉 → 開
└──────┴──────┴──────┴──────┘
```

- `update(dt)` でフレームをインクリメント
- 最終フレーム到達 → `is_open=True`、`_on_door_animation_complete()` 呼び出し
- 完全に開いた後は描画をスキップ（下のタイルレイヤーが見える）

---

## 状態永続化

WorldStateManagerのフラグで一度開けたドアを記憶する：

```
flag: door_<door_id> = True
```

マップロード時にフラグを確認し、`True` であれば `is_open=True` で初期化。
一度開けたドアは再訪時も開いたまま。

---

## 実装対象外（スコープ外）

- ドアが閉じる動作（開いたら永続的に開いたまま）
- ドアのノック音・BGM変化などの音響演出（別タスクで対応）
- Lua スクリプトからのドア制御 API（必要になれば追加）

---

## 実装ファイル一覧

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/world/door_manager.py` | 新規 | DoorManager・Door・DoorResult クラス |
| `src/scenes/map_scene.py` | 変更 | DoorManager 統合、遷移処理 |
| `data/items.json` | 変更 | とうぞくのカギ・まほうのカギ・さいごのカギ追加 |
| `assets/images/doors/` | 新規 | スプライト画像格納ディレクトリ |
