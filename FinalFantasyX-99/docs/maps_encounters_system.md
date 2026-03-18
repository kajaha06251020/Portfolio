# マップ/敵配置システム仕様書

## 概要
FFアニバーサリー「Final Fantasy X-99」のマップ・敵配置拡張。
複数フィールドとダイナミックな敵グループシステム。

## システム構成

### 1. マップシステムの拡張

#### 実装状況（2026-02-18）
- `pytmx` により `assets/Maps/*.tmx` と `*.tsx` を読み込み、タイルレイヤーをレンダリング
- `field_start` は `DF_Overworld_TileMap.tmx` を使用
- タイルプロパティ `Type` が `Wall/Sea/Mountain` のマスは通行不可
- プレイヤー移動はグリッドベース（1キー入力につき1マス移動）
- 画面はプレイヤー中心のカメラ追従
- `maps.json` の `transitions` を用いたマップ遷移を実装（遷移先 `to_entry` へのスポーン対応）
- エンカウントゾーンは `zone_id` 手動指定ではなく、プレイヤー座標から自動判定
- エンカウントは「現在マップ + 現在座標から導出したゾーン」で判定し、ゾーンごとの `enemy_groups` を参照
- 遭遇時に `encounter_group` を戦闘へ引き継ぎ、勝利時報酬（`base_rewards + drops + job_points`）は統一APIで確定反映

#### マップ構造
```
/assets/
  /maps/
    /tilesets/
      - grass_tileset.png
      - forest_tileset.png
      - cave_tileset.png
```

#### マップデータ（JSON）
```json
{
  "map_id": "field_1",
  "name": "グラスランド",
  "width": 16,
  "height": 12,
  "tileset": "grass_tileset",
  "tile_data": [[0, 1, 2, ...], ...],
  "event_zones": [
    {
      "zone_id": "zone_1",
      "x": 5,
      "y": 8,
      "width": 4,
      "height": 3,
      "encounter_rate": 50,
      "enemy_groups": ["group_forest_weak", "group_forest_normal"]
    }
  ],
  "npcs": [
    {
      "npc_id": "old_man",
      "x": 10,
      "y": 5,
      "sprite": "npc_oldman.png",
      "dialogue": "...いや、何でもない..."
    }
  ],
  "transitions": [
    {
      "from_zone": "exit_north",
      "to_map": "field_2",
      "to_zone": "entrance_south"
    }
  ]
}
```

### 2. 敵グループシステム

#### 敵グループ定義
```json
{
  "group_id": "group_forest_normal",
  "name": "スライムとゴブリン",
  "difficulty": 2,
  "enemy_composition": [
    {
      "enemy_type": "slime",
      "count": 2,
      "min_level": 10,
      "max_level": 14
    },
    {
      "enemy_type": "goblin",
      "count": 1,
      "min_level": 11,
      "max_level": 15
    }
  ],
  "formation": {
    "left_positions": [130, 260, 130],
    "right_positions": [100, 200, 300],
    "sprite_scale": [0.8, 1.0, 0.9]
  },
  "rewards": {
    "exp": 150,
    "gold": 80,
    "drops": [
      {"item_id": "potion", "rate": 30},
      {"item_id": "antidote", "rate": 20}
    ]
  }
}
```

#### 敵タイプ定義（enemies.json）
```json
{
  "enemies": {
    "slime": {
      "name": "スライム",
      "description": "ゼラチナスな敵。毒を吐く。",
      "icon": "enemy_slime",
      "color": [0, 150, 0],
      "level": 12,
      "hp": 25,
      "mp": 5,
      "attack": 10,
      "defense": 5,
      "speed": 1.0,
      "abilities": ["attack", "poison_spit"],
      "drops": [
        {"item_id": "potion", "rate": 20},
        {"item_id": "slime_jelly", "rate": 50}
      ]
    },
    ...
  }
}
```

### 3. エンカウントシステム

#### 敵遭遇メカニズム
```
エンカウント判定:
  if random(0, 100) < zone.encounter_rate:
    selected_group = choice(zone.enemy_groups)
    player.start_battle(selected_group)
```

#### レベル調整
```
敵グループのレベル = パーティ平均レベル × (0.8 ～ 1.2)
最小/最大レベルで制限
※ 詳細な難易度スケーリングはTiledを使用した実装が予定されています
```

### 4. マップ遷移システム

#### ゾーン管理
```
各マップは複数のゾーンで構成
- encounter_zone: 敵遭遇エリア
- safe_zone: 安全エリア（城など）
- transition_zone: マップ遷移ゾーン
```
※ Tiledを使用した実装が予定されています

### 5. データ構造

#### maps.json
```json
{
  "maps": [
    {
      "map_id": "field_1",
      "name": "グラスランド",
      "difficulty_range": [10, 15],
      "recommended_level": 12,
      "width": 16,
      "height": 12,
      "background": "grass_field.png",
      "music": "field_bgm_1"
    }
  ]
}
```

#### enemies.json
新規作成・敵タイプ定義全体管理

#### encounters.json
```json
{
  "encounters": {
    "field_1": {
      "zones": [
        {
          "zone_id": "forest_weak",
          "name": "西の森",
          "encounter_rate": 40,
          "enemy_groups": [
            "group_slime_only",
            "group_slime_goblin"
          ]
        }
      ]
    }
  }
}
```

### 6. 複数フィールドの実装

#### フィールド一覧（ゲーム序盤～中盤対応）

| マップID | 名前 | 推奨Lv | 敵 | 次のステージ |
|---------|------|--------|-----|----------|
| field_start | スタート平原 | 1-3 | スライム×1-2 | castle_town |
| forest_1 | 南の森 | 2-5 | スライム、ゴブリン | castle_town |
| castle_town | 街 | ～ | 敵なし（安全） | forest_2 |
| forest_2 | 東の森 | 5-10 | ゴブリン、オーク | mountain_pass |
| mountain_pass | 山越え | 10-15 | オーク、ドレイク | dragon_cave |
| dragon_cave | 竜の洞窟 | 15-20 | ドレイク（強） | town_2 |

### 7. 敵グループのバリエーション

#### 同一フィールド内での複数グループ
```
field_1:
  - group_weak: スライム×2 (初遭遇向け)
  - group_normal: スライム×1, ゴブリン×1 (標準)
  - group_hard: ゴブリン×2 (高レベル)
  - group_rare: ドレイク×1 (稀)
```

#### 敵AIバリエーション
- **AI_aggressive**: 毎ターン攻撃
- **AI_tactical**: 特定条件で魔法使用
- **AI_healer**: パーティメンバーの回復優先
- **AI_support**: 補助魔法中心

### 8. 実装モジュール

#### `src/scenes/map_scene.py` 拡張
- マップデータの読み込み
- エンカウント判定
- TMX/TSXレンダリング（`pytmx`）
- タイル単位移動（1マス移動）
- タイルプロパティを用いた簡易通行判定
- `maps.json` の `transitions` によるマップ遷移を実装
- プレイヤー座標からエンカウントゾーンを自動更新

#### `src/entities/enemy.py` 拡張
- 敵情報の定義拡張
- 敵グループの管理

#### `src/battle/encounter.py`（新規）
- エンカウント判定
- 敵グループ選択
- 座標ベースのエンカウントゾーン判定API
- 戦闘勝利時報酬（Gold + Drops）の統一確定API

#### `src/scenes/battle_scene.py` 拡張
- 勝利時のEXP分配・レベルアップ処理
- `encounter.py` の統一報酬APIを利用した Gold / Drops 反映

---

## 開発ロードマップ

### Phase 1: 基本マップシステム
- マップデータ構造定義
- 敵グループ定義
- マップ遷移ロジック

### Phase 2: エンカウント機能
- エンカウント判定実装
- 敵グループ選択機制
- ランダム敵生成

### Phase 3: フィールド展開
- 複数フィールドの実装（5～6マップ）
- 敵グループのバリエーション
- 推奨レベルシステム

### Phase 4: マップUI＆視覚効果
- マップ画像表示
- プレイヤーキャラ移動アニメ
- フィールドBGM

---

## ゲーム進行上の考慮点

### チュートリアルマップ
- field_start : スライムのみ出現（敵倒す練習）
- 逃げる機能の練習

### セーブポイント
- 町のセーブ施設で セーブ可能
- フィールドセーブは後々のアップデート対応

---

## グラフィックス・アセット要件

### タイルセット
- grass: 基本的な草原
- forest: 森（木、藪）
- cave: 洞窟（石、暗い背景）
- mountain: 山（岩、雪）
- castle: 城エリア

### NPC・敵スプライト
- NPC：汎用立ち絵
- 敵：バリエーション豊か（色違い等）

### BGM
- field: 冒険的なBGM
- cave: 緊迫感のあるBGM
- castle: 落ち着いた城BGM
