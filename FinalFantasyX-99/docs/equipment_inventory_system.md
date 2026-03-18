# 装備・インベントリシステム仕様書

## 概要
FFアニバーサリー「Final Fantasy X-99」の装備・インベントリシステム実装。
FF5風の装備スロット＆能力値補正メカニズムを採用。

## システム構成

### 1. インベントリシステム

#### インベントリ構造
- **消費アイテム**: ポーション、エーテル等（数量管理）
- **装備品**: 武器、防具（装備スロット管理）
- **重要アイテム**: ストーリーアイテム（フラグアイテム）

#### スロット構成（キャラクターごと）
```json
{
  "weapon_slots": 1,
  "armor_slots": 4,
  "accessory_slots": 2,
  "consumable_slots": 999,
  "key_items": 999
}
```

### 2. 装備システム

#### 装備スロット定義

| スロット | 数量 | 説明 |
|---------|------|------|
| weapon | 1 | 武器スロット |
| head | 1 | 頭防具（兜） |
| body | 1 | 体防具（鎧） |
| accessory1 | 1 | アクセサリ1 |
| accessory2 | 1 | アクセサリ2 |

#### 装備品の定義

```json
{
  "item_id": "sword_of_legend",
  "type": "weapon",
  "name": "伝説の剣",
  "description": "古い魔法が秘められた剣",
  "price": 500,
  "stat_bonuses": {
    "attack": 15,
    "magic": 5
  },
  "special_abilities": ["holy_blade_plus"],
  "required_level": 10,
  "required_job": null
}
```

### 3. 能力値補正メカニズム

#### 計算式
```
実ステータス = 基本値 × ジョブ補正 × (1 + 装備補正%)
```

例：バッツ（knight）がサーベル装備時
```
attack基本値: 18
ジョブ補正: 1.0（knight）
装備補正: +10（サーベル）
= 18 × 1.0 × (1 + 10/100) = 19.8 → 19
```

### 4. 各装備タイプ別仕様

#### 武器（weapon）
- **種類**: 剣、斧、槍、弓等
- **補正対象**: attack, magic, accuracy等
- **特殊効果**: 属性ダメージ、会心率上昇等

#### 防具（armor）
- **種類**: 兜(head), 鎧(body)
- **補正対象**: defense, magic_defense, hp等
- **特殊効果**: 状態異常耐性等

#### アクセサリ（accessory）
- **種類**: リング、ブレスレット等
- **補正対象**: 全能力値対応（バランス重視）
- **特殊効果**: 複合効果、強力な補正等

### 5. データ構造（JSON）

#### items.json
```json
{
  "weapons": [
    {
      "item_id": "sword_steel",
      "name": "スチールソード",
      "description": "鉄製の標準的な剣",
      "price": 100,
      "stat_bonuses": {
        "attack": 8,
        "magic": 0
      },
      "hit_rate": 100,
      "special_abilities": [],
      "required_level": 1,
      "required_job": null
    }
  ],
  "armor": [
    {
      "item_id": "plate_mail",
      "slot": "body",
      "name": "プレートメイル",
      "description": "鋼板製の重い鎧",
      "price": 80,
      "stat_bonuses": {
        "defense": 12,
        "hp": 20
      },
      "special_abilities": [],
      "required_level": 1,
      "required_job": null
    }
  ],
  "accessory": [
    {
      "item_id": "ring_power",
      "name": "パワーリング",
      "description": "力があふれ出す指輪",
      "price": 200,
      "stat_bonuses": {
        "attack": 5,
        "defense": 2
      },
      "special_abilities": [],
      "required_level": 5
    }
  ],
  "consumable": [
    {
      "item_id": "potion",
      "name": "ポーション",
      "description": "HP回復アイテム",
      "price": 50,
      "effect": "heal",
      "power": [35, 55],
      "target": "single_ally"
    }
  ]
}
```

#### inventory.json（プレイヤー状態保存）
```json
{
  "party_inventory": {
    "weapons": [
      {"item_id": "sword_steel", "quantity": 1, "equipped_by": "バッツ"}
    ],
    "armor": [
      {"item_id": "plate_mail", "quantity": 1, "slot": "body", "equipped_by": "バッツ"}
    ],
    "consumables": [
      {"item_id": "potion", "quantity": 5}
    ],
    "key_items": []
  }
}
```

### 6. 実装モジュール

#### `src/battle/equipment.py`
- `Item` クラス：アイテム定義
- `Equipment` クラス：装備品管理
- `Inventory` クラス：インベントリ管理
- `EquipmentSystem` クラス：装備システム全体管理

#### 公開API
```python
inventory = Inventory(actor)
equipment = EquipmentSystem()

# 装備
inventory.equip(item_id, slot)
inventory.unequip(slot)
inventory.get_equipped_items()

# アイテム
inventory.add_item(item_id, quantity)
inventory.remove_item(item_id, quantity)
inventory.get_item_count(item_id)

# 補正計算
bonuses = inventory.calculate_stat_bonuses(stat_type)
actual_stat = base_stat * job_multiplier * (1 + bonuses/100)
```

### 7. バトルUI統合

#### アイテムメニュー
- 消費アイテム一覧表示
- 個数表示
- 使用不可時の表示（在庫0等）

#### ステータス画面（将来）
- 現在の装備品表示
- ステータス補正表示
- 装備変更パネル

### 8. ゲーム進行との連携

#### 初期装備
- キャラクター別の初期装備を設定
- チュートリアルで装備説明

#### 敵のドロップアイテム
- 敵倒時にランダムドロップ
- 装備品/消費アイテム両対応

#### ショップ機能（将来）
- 防具屋、武器屋等
- 売却・購入メカニズム

### 9. 設計メモ

- **装備スロット制限**: FF5風の「どの装備でも装備可能」ではなく、スロット管理で柔軟に対応
- **能力値依存性**: 装備品は独立した能力値補正を持つ
- **ジョブとの連動**: 特定ジョブ専用装備（将来拡張）
- **継承性**: プレイヤーデータ永続化で実装

---

## 開発ロードマップ

### Phase 1: 基本装備システム
- Equipment/Itemクラス実装
- 装備データ定義（各装備タイプ5～10個）
- 装備･外し機能

### Phase 2: インベントリ管理
- Inventoryクラス実装
- 消費アイテム管理
- ステータス補正計算

### Phase 3: UI統合
- インベントリ画面実装
- 装備変更画面実装
- アイテム使用UI

### Phase 4: ゲーム進行統合
- ドロップアイテムシステム
- ショップ機能（オプション）
