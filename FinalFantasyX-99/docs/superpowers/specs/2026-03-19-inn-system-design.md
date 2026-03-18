# 宿屋システム 設計仕様書

**日付:** 2026-03-19
**ステータス:** 承認済み

---

## 1. 概要

ドラクエ方式の宿屋システムを実装する。NPCに話しかけると料金確認ダイアログが表示され、支払いを行うと全パーティメンバーのHP/MPが全回復する。セーブ機能は含まない（既存メニューを使用）。

---

## 2. アーキテクチャ

```
[NPC: innkeeper.lua]
    ↓ script_api.start_inn(price)
[InnScene]
    ↓ 確認 → 回復 → game.pop_scene()
[MapScene に戻る]
```

### 新規・変更ファイル

| ファイル | 種別 | 内容 |
|---------|------|------|
| `src/scenes/inn_scene.py` | 新規 | 宿屋UI・支払い・回復ロジック |
| `scripts/npc/innkeeper.lua` | 新規 | 宿屋NPCスクリプト |
| `data/npcs.json` | 変更 | innkeeper NPC エントリを追加 |
| `data/maps.json` | 変更 | `castle_town_inn` に `inn_price: 10` を追加 |
| `src/scripting/api.py` | 変更 | `start_inn(price)` API メソッドを追加 |
| `src/game.py` | 変更 | `"inn"` シーンを scenes 辞書に登録 |

---

## 3. 料金設計

料金は `data/maps.json` の各マップエントリに `"inn_price": N` フィールドで管理する。章・地域が進むにつれて価格が上がる設計。

| マップID | 価格 |
|---------|------|
| `castle_town_inn` | 10G |
| （将来の町2） | 30G |
| （将来の町3） | 80G |

NPC スクリプトは `ScriptAPI.get_map_inn_price()` 経由でマップの料金を取得し、`start_inn(price)` に渡す。

---

## 4. InnScene 詳細設計

### 4.1 状態遷移

```
state: "confirm"
  ↓ はい選択 → ゴールド足りる？
      YES → state: "recovering" → 回復 → pop_scene()
      NO  → state: "no_gold" → メッセージ表示 → "confirm" に戻る
  ↓ いいえ選択 → pop_scene()
```

### 4.2 UI レイアウト

```
┌──────────────────────────────────────────┐
│  宿屋                                     │
│                                          │
│  左パネル: パーティ状態                    │
│  ┌──────────────┐                        │
│  │ バッツ  HP 全快                        │
│  │ レナ    HP 全快                        │
│  │ ガラフ  HP 全快                        │
│  └──────────────┘                        │
│                                          │
│  右パネル: 確認                            │
│  「1泊 10G です。                          │
│   お泊まりになりますか？」                  │
│                                          │
│  ▶ はい                                   │
│    いいえ                                 │
└──────────────────────────────────────────┘
│  所持ゴールド: 500G                        │
└──────────────────────────────────────────┘
```

### 4.3 InnScene クラス設計

```python
class InnScene(BaseScene):
    def __init__(self, game):
        self.price: int = 0          # start_inn() で設定
        self.state: str = "confirm"  # confirm | recovering | no_gold
        self.selected_index: int = 0 # 0=はい, 1=いいえ
        self.message: str = ""

    def set_price(self, price: int): ...
    def on_enter(self): ...
    def handle_events(self, events): ...
    def _confirm_yes(self): ...      # ゴールドチェック → 回復 → pop
    def _recover_party(self): ...    # 全員HP/MP全回復
    def update(self): ...
    def draw(self, screen): ...
```

---

## 5. ScriptAPI 拡張

### 5.1 追加メソッド

```python
def start_inn(self, price: int) -> None:
    """宿屋シーンを起動する"""
    inn_scene = self.game.scenes.get("inn")
    if inn_scene:
        inn_scene.set_price(price)
        self.game.push_scene("inn")

def get_map_inn_price(self) -> int:
    """現在マップの inn_price を返す（なければ 0）"""
    map_scene = self.game.scenes.get("map")
    if not map_scene:
        return 0
    return (map_scene.current_map_data or {}).get("inn_price", 0)
```

---

## 6. NPC スクリプト設計

### `scripts/npc/innkeeper.lua`

```lua
-- 宿屋のおやじ NPC スクリプト
local price = game.get_map_inn_price()

if price > 0 then
    game.say("いらっしゃいませ！\n1泊 " .. price .. "G でございます。")
else
    game.say("いらっしゃいませ！\n本日は満室でございます。")
    return
end

game.start_inn(price)
```

---

## 7. データ変更

### `data/maps.json` — castle_town_inn エントリに追加

```json
"inn_price": 10
```

### `data/npcs.json` — innkeeper NPC を追加

```json
{
  "npc_id": "innkeeper",
  "name": "宿屋のおやじ",
  "script": "innkeeper",
  "position": {"x": 5, "y": 3},
  "map_id": "castle_town_inn",
  "sprite": "npc_innkeeper.png",
  "facing": "down"
}
```

---

## 8. 回復ロジック

```python
def _recover_party(self):
    party = getattr(self.game, "party", [])
    for member in party:
        member["hp"] = member.get("max_hp", member["hp"])
        member["mp"] = member.get("max_mp", member["mp"])
    # CharacterDataManager にも反映
    self.game.character_data.replace_party(party)
```

---

## 9. 成功条件

- NPC に話しかけると料金ダイアログが表示される
- 「はい」選択時、ゴールドが減り全員HP/MPが全回復する
- ゴールド不足時はメッセージを表示してキャンセルできる
- 「いいえ」選択時は何もせず MapScene に戻る
- 回復後のパーティ状態がセーブデータに正しく保存される
