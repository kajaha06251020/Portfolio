# ジョブ・アビリティシステム仕様書

## 概要
FFアニバーサリー「Final Fantasy X-99」のジョブ・アビリティシステム実装。
FF5型のジョブチェンジ＆アビリティ習得メカニズムを採用。

## システム構成

### 1. ジョブシステムの概念

#### ジョブの定義
- **基本属性**: ジョブID、名前、説明、アイコン
- **ステータス補正**: HP倍率、MP倍率、攻撃倍率、防御倍率、魔力倍率
- **習得アビリティ**: そのジョブで習得できる全アビリティリスト
- **必要条件**: ジョブチェンジの条件（レベル等）

#### 対応キャラクター別ジョブ

**バッツ**（ジョブの種族: 人間戦士系）
1. `knight` - ナイト：防御力特化、装甲技習得
2. `samurai` - 侍：会心率上昇、刀技習得
3. `dragoon` - 竜騎士：ジャンプ技、高攻撃力

**レナ**（ジョブの種族: 白魔術師系）
1. `white_mage` - 白魔道士：回復魔法特化、ケアル等習得
2. `dancer` - 踊り子：補助技、命中回避上昇
3. `summoner` - 召喚士：魔法技習得

**ガラフ**（ジョブの種族: 防御系）
1. `fighter` - ファイター：基本ジョブ、高攻撃力
2. `monk` - モンク：格闘技、修行奥義習得
3. `paladin` - パラディン：聖剣技、防御補助

### 2. アビリティシステム

#### アビリティの定義
- **アビリティID**: `ability_slam`, `cure`, `jump` など
- **名前**: "斬撃", "ケアル", "ジャンプ" など
- **説明**: 効果の説明文
- **タイプ**: `attack`, `magic`, `support`, `special` など
- **消費資源**: MP消費量、TP消費量（将来）
- **習得レベル**: そのジョブで習得するレベル
- **効果**: ダメージ計算式、回復量、状態異常付与等

#### アビリティタイプ別処理

| タイプ | 説明 | 消費 | 対象 |
|--------|------|------|------|
| `attack` | 物理攻撃系 | - | 敵単体/複数 |
| `magic` | 魔法系 | MP | 敵/味方選択 |
| `heal` | 回復系 | MP | 味方/自分 |
| `support` | 補助系 | MP/TP | 味方/自分 |
| `special` | 特殊技 | MP/TP | 状況依存 |

### 3. データ構造（JSON）

#### jobs.json
```json
{
  "jobs": [
    {
      "job_id": "knight",
      "name": "ナイト",
      "character": "バッツ",
      "description": "防具を軽くこなす騎士。防御力が高い。",
      "required_level": 1,
      "stat_bonuses": {
        "hp_multiplier": 1.1,
        "mp_multiplier": 0.9,
        "attack_multiplier": 1.0,
        "defense_multiplier": 1.25,
        "magic_multiplier": 0.8
      },
      "abilities": [
        {"ability_id": "slash", "learn_level": 1},
        {"ability_id": "shield_guard", "learn_level": 3},
        {"ability_id": "armor_technique", "learn_level": 5}
      ]
    },
    ...
  ]
}
```

#### abilities.json
```json
{
  "abilities": [
    {
      "ability_id": "slash",
      "name": "斬撃",
      "type": "attack",
      "description": "敵1体に通常攻撃",
      "mp_cost": 0,
      "power": [8, 12],
      "accuracy": 100,
      "target_type": "single_enemy"
    },
    {
      "ability_id": "cure",
      "name": "ケアル",
      "type": "magic",
      "description": "味方1体のHP回復",
      "mp_cost": 8,
      "power": [40, 55],
      "accuracy": 100,
      "target_type": "single_ally"
    },
    ...
  ]
}
```

### 4. ジョブチェンジシステム

#### メカニズム
1. **ジョブチェンジ実行**
   ```python
   actor.change_job(job_id)
   # → 新ジョブの能力値補正適用
   # → アビリティ習得済みリスト更新
   ```

2. **アビリティ習得判定**
   - キャラクターレベル >= アビリティ習得レベル
   - キャラクターがそのジョブに就いている
   - または `アビリティマスター` 的な汎用アビリティ（将来）

3. **ジョブ固有のステータス計算**
   ```
   実ステータス = 基本ステータス × ジョブ補正倍率 × 装備補正
   ```

### 5. 実装モジュール

#### `src/battle/job_ability.py`
- `Job` クラス：ジョブ定義管理
- `Ability` クラス：アビリティ定義管理
- `JobSystem` クラス：ジョブ管理システム
- `AbilitySystem` クラス：アビリティ習得・実行管理

####公開API
```python
# ジョブ系
actor.current_job = "knight"
job = leveling_system.get_job(job_id)
actor.change_job(job_id)
actor.get_available_abilities()  # 習得済みアビリティ一覧

# アビリティ系
ability = ability_system.get_ability(ability_id)
can_use = actor.can_use_ability(ability_id)
result = actor.use_ability(ability_id, target)
```

### 6. バトルUI統合

#### コマンドメニュー拡張
現在の「たたかう」「まほう」「アイテム」「ぼうぎょ」「にげる」に加えて、
ジョブアビリティ習得後は以下を追加：
- アビリティメニューで習得済みアビリティ一覧表示
- 個別アビリティごとの消費MP表示

#### メッセージログ表示
```
{キャラ名}は {アビリティ名} を使った！
→ ダメージ/回復量表示
```

### 7. 設計メモ

- **ジョブ別能力値補正**: `stat_multiplier` で柔軟に対応可能
- **アビリティの追加**: `abilities.json` に追加するだけで自動対応
- **将来拡張**:
  - アビリティマスターレベルシステム
  - 魔石によるアビリティ習得（FF6風）
  - ジョブレベルによるステータス上昇
  - 複数ジョブ習得時のハイブリッド対応

---

## 開発ロードマップ

### Phase 1: 基本ジョブシステム
- `JobSystem` クラス実装
- ジョブデータ定義（各キャラ3～4ジョブ）
- ジョブチェンジ処理

### Phase 2: アビリティ習得・実行
- `AbilitySystem` クラス実装
- アビリティデータ定義（15～20個）
- バトルUIとの統合

### Phase 3: ジョブUI
- ジョブ選択画面
- アビリティメニュー統合
- ジョブチェンジ画面

### Phase 4: ゲームバランス調整
- 各ジョブの相対的強さ調整
- アビリティの効果値チューニング
