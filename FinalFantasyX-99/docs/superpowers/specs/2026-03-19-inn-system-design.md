# 宿屋システム 設計仕様書

**日付:** 2026-03-19
**ステータス:** 承認済み（v2 — spec reviewer フィードバック反映）

---

## 1. 概要

ドラクエ方式の宿屋システムを実装する。NPCに話しかけると InnScene が起動し、料金確認ダイアログが表示される。支払いを行うと全パーティメンバーのHP/MPが全回復する。セーブ機能は含まない（既存メニューを使用）。

---

## 2. アーキテクチャ

```
[NPC: innkeeper.lua]
    ↓ coroutine.yield("inn", price)
[MapScene._advance_dialogue — elif cmd == "inn":]
    ↓ inn_scene.set_price(price); game.push_scene("inn")
[InnScene]
    ↓ 確認 → 回復 → game.pop_scene()
[MapScene に戻る (on_resume でコルーチンを終了)]
```

### 新規・変更ファイル

| ファイル | 種別 | 内容 |
|---------|------|------|
| `src/scenes/inn_scene.py` | 新規 | 宿屋UI・支払い・回復ロジック |
| `scripts/npc/innkeeper.lua` | 変更 | 既存を差し替え：マップ料金を読んで `npc.open_inn(price)` を呼ぶ |
| `data/maps.json` | 変更 | `castle_town_inn` に `"inn_price": 10` を追加 |
| `src/scripting/api.py` | 変更 | `npc` 名前空間に `npc.open_inn(price)` / `npc.get_inn_price()` を追加 |
| `src/scenes/map_scene.py` | 変更 | `_advance_dialogue` に `elif cmd == "inn":` ハンドラを追加 |
| `src/game.py` | 変更 | `"inn"` シーンを scenes 辞書に登録 |

> **注意:** `data/npcs.json` の `innkeeper` エントリは**既に存在する**（変更不要）。

---

## 3. 料金設計

料金は `data/maps.json` の各マップエントリに `"inn_price": N` フィールドで管理する。

| マップID | 価格 |
|---------|------|
| `castle_town_inn` | 10G |
| （将来の町2） | 30G |
| （将来の町3） | 80G |

NPC スクリプトは `npc.get_inn_price()` 経由でマップ料金を取得し、`npc.open_inn(price)` に渡す。

---

## 4. ScriptAPI 拡張

`src/scripting/api.py` の `_register_npc` メソッド末尾に以下の Lua ヘルパーを追加する：

```python
lua.execute("""
    function npc.open_inn(price)
        coroutine.yield("inn", price)
    end
    function npc.get_inn_price()
        return coroutine.yield("get_inn_price")
    end
""")
```

ただし `npc.get_inn_price()` は Python 側で値を返す必要があるため、より単純な方法として Python 関数を直接登録する：

```python
def npc_get_inn_price() -> int:
    """現在マップの inn_price を返す（なければ 0）"""
    if api._game is None:
        return 0
    map_scene = api._game.scenes.get("map")
    if map_scene is None:
        return 0
    return (map_scene.current_map_data or {}).get("inn_price", 0)

npc_table = lua.eval("npc")
npc_table["get_inn_price"] = npc_get_inn_price

lua.execute("""
    function npc.open_inn(price)
        coroutine.yield("inn", price)
    end
""")
```

---

## 5. MapScene 拡張

`_advance_dialogue` の `elif cmd == "shop":` ブロックの後に追加：

```python
elif cmd == "inn" and len(yielded) >= 2:
    # 宿屋遷移: コルーチンを保持したまま InnScene へ
    price = int(yielded[1])
    inn_scene = self.game.scenes.get("inn")
    if inn_scene:
        inn_scene.set_price(price)
        self.game.push_scene("inn")
    else:
        logger.warning("InnScene not registered")
```

`on_resume` は `shop` と同様にコルーチン終了処理が自動的に行われる（既存の `on_resume` ロジックを確認し、必要なら `"inn"` も対応させる）。

---

## 6. NPC スクリプト設計

### `scripts/npc/innkeeper.lua`（既存ファイルを差し替え）

```lua
-- 宿屋のおやじ NPC スクリプト
function on_talk()
    local price = npc.get_inn_price()

    if price <= 0 then
        npc.say("宿屋の主人", "いらっしゃいませ！\n本日は満室でございます。")
        return
    end

    npc.say("宿屋の主人", "いらっしゃいませ！\n1泊 " .. price .. "G でございます。")
    npc.open_inn(price)
end
```

> **注意:** `npc.say` は `coroutine.yield("say", ...)` で実装されている。`npc.open_inn` は `coroutine.yield("inn", price)` で実装されている。Lua 内に `game.*` グローバルは存在しない。

---

## 7. データ変更

### `data/maps.json` — castle_town_inn エントリに追加

```json
"inn_price": 10
```

（既存の `castle_town_inn` オブジェクト内に追加。他フィールドは変更不要。）

### `data/npcs.json` — 変更不要

`innkeeper` エントリは既に存在する：

```json
"innkeeper": {
  "name": "宿屋の主人",
  "sprite": "npc_innkeeper",
  "script": "npc/innkeeper.lua",
  "movement": "fixed",
  "layers": {
    "physical": { "map": "castle_town_inn", "x": 4, "y": 1 }
  }
}
```

---

## 8. InnScene 詳細設計

### 8.1 状態遷移

```
state: "confirm"
  ↓ はい選択
      ゴールド >= price?
        YES → ゴールド減算 → _recover_party() → pop_scene()
        NO  → state: "no_gold"
  ↓ いいえ選択 → pop_scene()

state: "no_gold"
  ↓ 任意のキー入力（ENTER / SPACE / Z / Escape）→ state: "confirm"
```

> **注意:** `recovering` 状態は不要。回復は瞬時に実行し、その後即 `pop_scene()` を呼ぶ。フェード演出は `innkeeper.lua` がすでに `event.fade_out/wait/fade_in` を使って実装しているため InnScene 側で行わない。

### 8.2 UI レイアウト

**confirm 状態:**

```
┌──────────────────────────────────────────┐
│  宿屋                                     │
│                                          │
│  左パネル: パーティ状態                    │
│  ┌──────────────┐                        │
│  │ キャラ名 HP {current}/{max}            │
│  │ キャラ名 HP {current}/{max}            │
│  └──────────────┘                        │
│                                          │
│  右パネル:                                │
│  「1泊 10G です。                          │
│   お泊まりになりますか？」                  │
│                                          │
│  ▶ はい                                   │
│    いいえ                                 │
│                                          │
│  所持ゴールド: {gold}G                    │
└──────────────────────────────────────────┘
```

**no_gold 状態:**

```
┌──────────────────────────────────────────┐
│  宿屋                                     │
│                                          │
│  「ゴールドが足りません。」                 │
│                                          │
│  （何かキーを押してください）              │
└──────────────────────────────────────────┘
```

### 8.3 InnScene クラス設計

```python
class InnScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.price: int = 0          # set_price() で設定
        self.state: str = "confirm"  # confirm | no_gold
        self.selected_index: int = 0 # 0=はい, 1=いいえ
        self.message: str = ""

    def set_price(self, price: int) -> None:
        """push_scene の直前に呼ぶ。on_enter() は price をリセットしない。"""
        self.price = price

    def on_enter(self) -> None:
        """シーン開始時にUIリセット（price はリセットしない）。"""
        self.state = "confirm"
        self.selected_index = 0
        self.message = ""

    def handle_events(self, events): ...

    def _confirm_yes(self) -> None:
        """ゴールドチェック → 減算 → 回復 → pop_scene()"""
        if self.game.gold >= self.price:
            self.game.gold -= self.price  # ゴールド減算
            self._recover_party()
            self.game.pop_scene()
        else:
            self.state = "no_gold"
            self.message = "ゴールドが足りません。"

    def _recover_party(self) -> None:
        """全パーティメンバーの HP/MP を全回復する。"""
        party = getattr(self.game, "party", [])
        for member in party:
            member["hp"] = member.get("max_hp", member["hp"])
            member["mp"] = member.get("max_mp", member["mp"])
        self.game.character_data.replace_party(party)

    def update(self): ...
    def draw(self, screen): ...
```

### 8.4 キー入力仕様

| 状態 | キー | アクション |
|------|------|-----------|
| confirm | ↑↓ | selected_index を 0/1 切替 |
| confirm | Enter/Space/Z | selected_index==0 → _confirm_yes(); ==1 → pop_scene() |
| confirm | Escape | pop_scene()（キャンセル） |
| no_gold | Enter/Space/Z/Escape | state = "confirm" |

---

## 9. エッジケース

| ケース | 挙動 |
|--------|------|
| `price == 0` | innkeeper.lua が早期リターンするため InnScene は起動しない |
| `gold == price` | 正常購入（`>=` チェックのため境界値は購入可） |
| 空パーティ | `_recover_party` は `party = []` で空ループ（サイレント成功） |
| `inn_price` キーなし | `npc.get_inn_price()` が 0 を返し → innkeeper.lua が満室メッセージ |

---

## 10. 成功条件

- NPC に話しかけると料金確認ダイアログが表示される
- 「はい」選択時、ゴールドが減り全員 HP/MP が全回復する
- ゴールド不足時は「ゴールドが足りません」メッセージを表示し、何かキーを押すと confirm 状態に戻る
- 「いいえ」選択時は何もせず MapScene に戻る
- `gold == price`（境界値）でも正常に購入できる
- 回復後のパーティ状態がセーブデータに正しく保存される
