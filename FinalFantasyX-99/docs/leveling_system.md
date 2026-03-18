# レベルアップシステム仕様書

## 概要
FFアニバーサリー「Final Fantasy X-99」のレベルアップシステム実装。
FF5型固定テーブルを採用し、拡張性を持たせています。

## システム構成

### 1. EXP獲得メカニズム
- **バトル勝利時**: 敵グループのベースEXP合計値を獲得
- **キャラクター毎**のEXP管理
- **敵側**: バトル参加敵ごとにEXP報酬を定義

### 2. レベルアップテーブル（FF5型）

#### 定義内容
- `level`: レベル番号（1-99）
- `required_exp`: そのレベルに到達するのに必要な累積EXP
- `growth_rates`: 各能力値の成長倍率セット（キャラクターごとの個性を「speed」係数で実装）

#### 能力値成長
```
新能力値 = 初期値 × (1.0 + 成長率 × (レベル - 1))
```

#### 対応キャラクター
1. **バッツ** - 物理アタッカー型（Attack重視）
2. **レナ** - 魔法サポート型（Magic重視）
3. **ガラフ** - タンク型（Defense・HP重視）

### 3. データ構造（JSON）

**leveling_table.json**
```json
{
  "levels": [
    {
      "level": 1,
      "required_exp": 0,
      "growth_rates": {
        "hp": 0.06,        // HP成長率
        "mp": 0.04,        // MP成長率
        "attack": 0.03,    // 攻撃力成長率
        "defense": 0.02,   // 防御力成長率
        "magic": 0.03      // 魔力成長率
      }
    },
    ...
  ],
  "character_bonuses": {
    "バッツ": {
      "attack_bonus": 1.15,
      "defense_bonus": 0.95,
      "magic_bonus": 0.9
    },
    "レナ": {
      "attack_bonus": 0.9,
      "defense_bonus": 1.0,
      "magic_bonus": 1.3
    },
    "ガラフ": {
      "attack_bonus": 1.1,
      "defense_bonus": 1.25,
      "magic_bonus": 0.7
    }
  }
}
```

### 4. 実装モジュール

#### `src/battle/leveling.py`
- `LevelingSystem` クラス：EXP管理・レベルアップ処理
- `calculate_exp_for_level(level)` 関数：必要EXP計算
- `level_up(actor, level_table)` 関数：レベルアップ処理実行
- `gain_exp(actor, exp_amount, level_table)` 関数：EXP獲得処理

### 5. バトル終了後の処理

1. **敵グループのEXP計算**
   - 敵ごとのベースEXP合計値を算出
   - パーティ全体で均等配分またはダメージ量応じた配分

2. **キャラクター毎のレベルアップチェック**
   ```
   if current_exp + gain_exp >= required_exp_for_next_level:
       - old_stats を保存
       - levels_gained = NEW_LEVEL - 現在レベル
       - for each level 新しいレベルまで:
           能力値を再計算
       - メッセージ表示: "{キャラ名}のレベルが{new_level}になった！"
       - 能力値増加量を表示
   ```

3. **新魔法習得チェック**（将来拡張）
   - レベル到達で新しい技・魔法を習得

#### 実装状況（2026-02-18 更新）
- 勝利時EXPは `encounter_group.base_rewards.exp` を優先して配分
- 生存メンバーに対してEXP均等配分、`LevelingSystem.gain_exp` でレベルアップ判定
- 勝利時に `Gold` を加算し、`drops` はドロップ率判定でインベントリへ付与
- 追加報酬として `JP`（ジョブポイント）を生存メンバーへ均等配分

## JSON データファイル

### 1. leveling_table.json
- レベル1～99のテーブル
- キャラクター別の成長ボーナス
- 推奨レベルごとのスキル習得トリガー（将来用）

### 2. enemy_exp_table.json
- 敵タイプごとのEXP報酬値
- パーティレベルに応じた調整係数

## 実装の流れ

1. **Phase 1**: levelingモジュール作成 + テーブル定義
2. **Phase 2**: battle_sceneに統合 + 敵倒した時のEXP獲得
3. **Phase 3**: UI表示（レベルアップアニメーション）
4. **Phase 4**: 新魔法・スキル習得システム連携

---

## 設計メモ

- FF5型固定テーブル採用理由：計画的なバランス調整が可能
- 成長率のキャラ差別化：能力値初期値 ×（1 + 成長率）で実現
- 将来FF6型対応：character_bonusesシステムで魔石風カスタマイズ可能に拡張可能
