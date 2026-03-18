# 宿屋システム 設計仕様書

**日付:** 2026-03-19
**ステータス:** 承認済み（v3 — spec reviewer フィードバック反映）

---

## 1. 概要

ドラクエ方式の宿屋システムを実装する。NPCに話しかけると InnScene が起動し、料金確認ダイアログが表示される。支払いを行うと全パーティメンバーのHP/MPが全回復する。セーブ機能は含まない（既存メニューを使用）。

---

## 2. アーキテクチャ

```
[NPC: innkeeper.lua]
    ↓ npc.open_inn(price)  →  coroutine.yield("inn", price)
[MapScene._advance_dialogue — elif cmd == "inn":]
    ↓ inn_scene.set_price(price); game.push_scene("inn")
[InnScene]
    ↓ 確認 → 回復 → game.pop_scene()
[MapScene.on_resume() → _advance_dialogue() → StopIteration → コルーチン終了]
```

`on_resume` は既存実装のまま動作する。`"inn"` 専用の分岐追加は不要。

### 新規・変更ファイル

| ファイル | 種別 | 内容 |
|---------|------|------|
| `src/scenes/inn_scene.py` | 新規 | 宿屋UI・支払い・回復ロジック |
| `scripts/npc/innkeeper.lua` | 変更 | 既存を差し替え：マップ料金を読んで `npc.open_inn(price)` を呼ぶ |
| `data/maps.json` | 変更 | `castle_town_inn` に `"inn_price": 10` を追加 |
| `src/scripting/api.py` | 変更 | `_register_npc` に `npc.open_inn` と `npc_get_inn_price` を追加 |
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

`src/scripting/api.py` の `_register_npc` メソッドに以下を追加する。

### 追加場所

既存の `lua.execute` ブロック（`npc.open_shop` 登録の直後）に続けて追記する：

```python
# --- 追加: inn サポート ---
def npc_get_inn_price() -> int:
    """現在マップの inn_price を返す（なければ 0）。
    現在のマップシーンの current_map_data（最後に遷移したマップの設定）から取得する。
    castle_town_inn にいない場合や inn_price キーがない場合は 0 を返し、
    innkeeper.lua が「満室」メッセージを表示する。
    """
    if api._game is None:
        logger.warning("npc.get_inn_price(): game is None")
        return 0
    map_scene = api._game.scenes.get("map")
    if map_scene is None:
        logger.warning("npc.get_inn_price(): MapScene not found, inn_price defaults to 0")
        return 0
    price = (map_scene.current_map_data or {}).get("inn_price", 0)
    if price == 0:
        logger.debug("npc.get_inn_price(): inn_price not set for current map, returning 0")
    return int(price)

# npc_table は既存の lua.execute ブロックが完了した後に再取得して参照の鮮度を保証する
npc_table = lua.eval("npc")
npc_table["get_inn_price"] = npc_get_inn_price

lua.execute("""
    function npc.open_inn(price)
        coroutine.yield("inn", price)
    end
""")
```

> **実装注意:**
> - `_register_npc` 内の最後の `lua.execute` が完了した後に `npc_table = lua.eval("npc")` で参照を取得すること（`npc = npc or {}` ブロック後でも同一テーブルを指すが、安全のため最後に取得する）。
> - `npc_table["get_inn_price"] = npc_get_inn_price` の Python 関数登録は、Lua 側の `function npc.open_inn(...)` 定義 **より前** に行うこと（`lua.execute` で `open_inn` を定義するとテーブル参照が変わる恐れがあるため、Python 関数を先に登録する）。

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

`on_resume` は変更不要。`dialogue_coroutine is not None` のとき `_advance_dialogue()` を呼ぶ既存ロジックが、宿屋から戻った際も正しく動作する（`npc.open_inn` の yield が resume され、スクリプト末尾で `StopIteration` → コルーチンが自動クリアされる）。

---

## 6. NPC スクリプト設計

### `scripts/npc/innkeeper.lua`（既存ファイルを差し替え）

既存の `innkeeper.lua` は Lua のみで完結する実装（`party.get_gold()` / `party.remove_gold()` / `party.rest()` 使用）。これを InnScene を使う実装に置き換える。置き換える理由は、専用の Python UI でパーティ HP 表示と 2 状態マシンを持つため。

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

> **注意:** `npc.say` → `coroutine.yield("say", ...)` / `npc.open_inn` → `coroutine.yield("inn", price)` / Lua 内に `game.*` グローバルは存在しない。

---

## 7. データ変更

### `data/maps.json` — castle_town_inn エントリに追加

```json
"inn_price": 10
```

（既存の `castle_town_inn` オブジェクト内に追加。他フィールドは変更不要。）

### `data/npcs.json` — 変更不要

`innkeeper` エントリは既に存在する。

---

## 8. InnScene 詳細設計

### 8.1 状態遷移

```
state: "confirm"
  ↓ はい選択
      gold >= price?
        YES → game.gold -= price → _recover_party() → pop_scene()
        NO  → state: "no_gold", message = "ゴールドが足りません。"
  ↓ いいえ選択 → pop_scene()
  ↓ Escape → pop_scene()

state: "no_gold"
  ↓ 任意のキー入力（ENTER / SPACE / Z / Escape）→ state = "confirm"
```

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
        self.price: int = 0          # set_price() で設定。on_enter() はリセットしない
        self.state: str = "confirm"  # confirm | no_gold
        self.selected_index: int = 0 # 0=はい, 1=いいえ
        self.message: str = ""

    def set_price(self, price: int) -> None:
        """push_scene の直前に呼ぶ。on_enter() より先に呼ぶこと。"""
        self.price = max(0, int(price))

    def on_enter(self) -> None:
        """シーン開始時に UI をリセット（price はリセットしない）。
        price == 0 のまま到達した場合は即 pop_scene() して抜ける。
        """
        self.state = "confirm"
        self.selected_index = 0
        self.message = ""
        if self.price == 0:
            self.game.pop_scene()

    def handle_events(self, events): ...

    def _confirm_yes(self) -> None:
        """ゴールドチェック → 減算 → 回復 → pop_scene()"""
        if self.game.gold >= self.price:
            self.game.gold -= self.price   # ゴールド減算
            self._recover_party()
            self.game.pop_scene()
        else:
            self.state = "no_gold"
            self.message = "ゴールドが足りません。"

    def _recover_party(self) -> None:
        """全パーティメンバーの HP/MP をインプレースで全回復する。
        game.party は character_data._party への参照のため replace_party() は不要。
        （party.rest() と同じパターン）
        """
        for member in self.game.party:
            member["hp"] = member.get("max_hp", member["hp"])
            member["mp"] = member.get("max_mp", member["mp"])

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
| `price == 0` | innkeeper.lua が早期リターン → InnScene は起動しない。万一起動しても `on_enter()` が即 `pop_scene()` |
| `gold == price` | 正常購入（`>=` 比較のため境界値は購入可） |
| 空パーティ | `game.party = []` で空ループ → サイレント成功 |
| `inn_price` キーなし | `npc.get_inn_price()` が `0` を返し → innkeeper.lua が満室メッセージを表示し InnScene は起動しない。`logger.debug` でログ出力 |

---

## 10. 成功条件

- NPC に話しかけると料金確認ダイアログが表示される
- 「はい」選択時、ゴールドが減り全員 HP/MP が全回復する（`game.party` のインメモリ値で検証）
- `gold == price`（境界値）でも正常に購入できる
- ゴールド不足時は「ゴールドが足りません」メッセージを表示し、何かキーを押すと confirm 状態に戻る
- 「いいえ」選択時は何もせず MapScene に戻る
- 回復はインメモリの `game.party` に即時反映される（ディスクへの書き込みはプレイヤーが手動セーブした際に行われる）
