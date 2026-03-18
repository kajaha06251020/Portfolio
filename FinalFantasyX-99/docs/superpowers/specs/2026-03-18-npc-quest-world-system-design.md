# NPC/クエスト/三層世界システム & 既存システム見直し 設計仕様書

**作成日:** 2026-03-18
**プロジェクト:** FinalFantasyX-99 (Pygame JRPG)
**対象:** 商用リリース (Steam等)

---

## 1. 概要

本仕様書は以下の2つの領域を定義する。

1. **新規システム:** NPC/対話、クエスト、三層世界状態管理 — Luaスクリプトエンジン統合型
2. **既存システム見直し:** ステータス効果・ジョブ補正・装備補正の完全統合、バトルシーンのデータ駆動化

### 設計原則

- **スクリプトエンジン統合型:** 対話・イベント・クエスト進行をLuaで記述し、複雑な分岐ロジックを自然に表現する
- **データとロジックの分離:** NPC配置やクエスト定義などの静的データはJSON、動的挙動はLua
- **三層世界を前提:** すべてのシステムが地上/深界/夢界の三層構造を前提に設計される
- **既存アーキテクチャとの一貫性:** JSON駆動のデータ構造を維持しつつLuaで拡張する

---

## 2. スクリプトエンジン基盤

### 2.1 技術選定

| 項目 | 選定 |
|------|------|
| スクリプト言語 | Lua |
| Pythonバインディング | lupa (LuaJIT/Lua for Python) |
| 理由 | ゲーム業界のデファクトスタンダード。RPGツクール、LOVE2Dなど実績多数。MOD対応も視野に入る |

### 2.2 アーキテクチャ

```
Python (ゲームエンジン)
  ├── ScriptEngine (Lua Runtime管理)
  │     ├── Luaランタイムのライフサイクル管理
  │     ├── Python→Lua APIバインディング（サンドボックス化）
  │     └── スクリプトのホットリロード（開発時のみ）
  │
  ├── API Layer (LuaからアクセスできるPython関数群)
  │     ├── npc.say(speaker, text)
  │     ├── npc.choice(options)
  │     ├── quest.start(quest_id)
  │     ├── quest.complete(quest_id)
  │     ├── quest.get_state(quest_id)
  │     ├── quest.set_stage(stage_name)
  │     ├── quest.set_objective(text)
  │     ├── quest.update(quest_id, stage)
  │     ├── world.get_layer()
  │     ├── world.get_state(key)
  │     ├── world.set_state(key, value)
  │     ├── party.has_member(name)
  │     ├── party.get_level(name)
  │     ├── flag.get(name)
  │     ├── flag.set(name, value)
  │     ├── event.trigger(event_id)
  │     └── rules.register(event_type, callback)
  │
  └── Script Files (Luaスクリプト)
        ├── scripts/npc/
        ├── scripts/quest/
        ├── scripts/event/
        └── scripts/common/
```

### 2.3 サンドボックス

LuaスクリプトからはゲームAPIのみアクセス可能。以下を遮断する:

- ファイルシステムアクセス (`io`, `os`)
- ネットワークアクセス
- プロセス実行
- Lua標準ライブラリのうち危険なモジュール

商用リリース時のセキュリティとMOD安全性を確保する。

### 2.4 ホットリロード

- **開発モード:** Luaスクリプトのファイル変更を検知し、ゲーム再起動なしで反映
- **リリースモード:** 無効化。スクリプトは起動時に一括ロード

---

## 3. NPC/対話システム

### 3.1 NPCデータ構造 (JSON + Lua)

NPCの基本情報はJSON、挙動ロジックはLuaスクリプトの二層構成。

```json
// data/npcs.json
{
  "npc_001": {
    "name": "老賢者アルマ",
    "sprite": "npc_alma",
    "layers": {
      "physical": { "map": "castle_town", "x": 12, "y": 8 },
      "depth":    { "map": "depth_ruins", "x": 5, "y": 3 },
      "dream":    null
    },
    "script": "npc/alma.lua"
  }
}
```

- `layers`: 三層それぞれでの配置。`null`はその層に存在しないことを示す
- 同一NPCが層ごとに異なる場所・異なるスクリプト挙動を持つ

### 3.2 対話スクリプト (Lua)

```lua
-- scripts/npc/alma.lua

function on_talk()
  local layer = world.get_layer()
  if layer == "physical" then
    talk_physical()
  elseif layer == "depth" then
    talk_depth()
  end
end

function talk_physical()
  if not flag.get("met_alma") then
    npc.say("アルマ", "旅の者か…この地に足を踏み入れたのは久しぶりじゃ。")
    npc.say("アルマ", "お主、その腕の紋様…万層紋か？")
    flag.set("met_alma", true)
    return
  end

  if quest.get_state("depth_investigation") == "active" then
    local choice = npc.choice({
      "深界について聞く",
      "何でもない"
    })
    if choice == 1 then
      npc.say("アルマ", "深界は地上の歪みが沈殿した場所じゃ。")
      npc.say("アルマ", "だが…治すたびに壊れるのは、深界も同じことよ。")
      quest.update("depth_investigation", "alma_consulted")
    else
      npc.say("アルマ", "そうか。気をつけるのじゃぞ。")
    end
    return
  end

  npc.say("アルマ", "万層紋の力、くれぐれも過信するでないぞ。")
end

function talk_depth()
  npc.say("???", "…お主にはワシが見えるのか。")
  npc.say("???", "ここではワシの名は意味を持たぬ。")
  if flag.get("met_alma") then
    npc.say("???", "…地上のワシに、もう会ったのじゃな。")
  end
end
```

### 3.3 対話表示仕様

| 要素 | 仕様 |
|------|------|
| テキスト送り | 1文字ずつ表示（速度設定可能）、ボタンで即全文表示 |
| 話者名 | ウィンドウ上部に表示、未知NPCは「???」 |
| 選択肢 | 最大4つ、カーソルで選択、結果をLuaに返却 |
| 顔グラフィック | 将来対応のため枠を確保（初期実装ではなし） |
| SE | 対話開始音、選択音、決定音 |

### 3.4 NPC挙動

| 挙動 | 仕様 |
|------|------|
| 配置 | 層ごとにマップ・座標を持つ |
| 向き | プレイヤーが話しかけるとプレイヤー方向を向く |
| 移動パターン | 固定、巡回、ランダム歩行（NPCごとにJSON設定） |
| 出現条件 | Luaの `on_visible()` で動的に制御（フラグ・世界状態依存） |

---

## 4. クエストシステム

### 4.1 クエストデータ構造 (JSON + Lua)

```json
// data/quests.json
{
  "main_ch1_01": {
    "type": "main",
    "title": "万層紋の目覚め",
    "description": "腕に刻まれた紋様の正体を探る",
    "chapter": 1,
    "script": "quest/main_ch1_01.lua",
    "rewards": {
      "exp": 500,
      "gold": 300,
      "items": [{"id": "potion", "count": 3}]
    }
  },
  "sub_castle_01": {
    "type": "sub",
    "title": "深界の調査依頼",
    "description": "アルマの依頼で深界の異変を調べる",
    "chapter": null,
    "prerequisites": ["flag:met_alma"],
    "layers_involved": ["physical", "depth"],
    "script": "quest/sub_castle_01.lua",
    "rewards": {
      "exp": 800,
      "gold": 500,
      "items": [{"id": "ether", "count": 2}]
    }
  }
}
```

### 4.2 クエスト状態遷移

```
inactive → available → active → (stages...) → completed
                                      ↓
                                   failed (一部のクエストのみ)
```

| 状態 | 意味 |
|------|------|
| `inactive` | 前提条件未達成。クエストログに表示されない |
| `available` | 受注可能。NPCにアイコン表示 |
| `active` | 進行中。クエストログに表示 |
| ステージ | クエスト内の進行段階（Lua側で自由に定義） |
| `completed` | 完了。報酬付与済み |
| `failed` | 失敗。特定クエストのみ（期限切れ、選択肢ミスなど） |

### 4.3 クエスト進行スクリプト (Lua)

```lua
-- scripts/quest/sub_castle_01.lua

function on_check_available()
  return flag.get("met_alma")
    and world.get_state("depth_distortion") >= 3
end

function on_accept()
  npc.say("アルマ", "深界に異変が起きておる。")
  npc.say("アルマ", "地上では感じられぬが…歪みが溜まっておるのじゃ。")
  npc.say("アルマ", "調べてきてくれぬか。")
  quest.set_stage("investigate")
  quest.set_objective("深界の歪みの原因を調べる")
end

function on_stage_event(trigger)
  local stage = quest.get_stage()

  if stage == "investigate" and trigger == "depth_crystal_found" then
    npc.say("ヴェル", "この結晶…歪みの核か？")
    quest.set_stage("report")
    quest.set_objective("アルマに報告する")

  elseif stage == "report" and trigger == "talk_alma" then
    npc.say("アルマ", "そうか…やはり結晶化が始まっておるか。")
    local choice = npc.choice({
      "結晶を渡す",
      "結晶を手元に残す"
    })
    if choice == 1 then
      npc.say("アルマ", "預かろう。ワシが封印を施す。")
      world.set_state("depth_distortion",
        world.get_state("depth_distortion") - 2)
      flag.set("crystal_given_alma", true)
    else
      npc.say("アルマ", "…そうか。だが気をつけよ。")
      flag.set("crystal_kept", true)
    end
    quest.complete()
  end
end
```

### 4.4 クエストログUI

| 要素 | 仕様 |
|------|------|
| タブ | メイン / サブ / 完了済み |
| 表示 | タイトル、説明文、現在の目標、関連する層アイコン |
| ソート | メインは章順、サブは受注順 |
| マーカー | ミニマップ上にクエスト目標地点を表示（設定可能） |
| 上限 | 同時進行サブクエスト最大10件 |

### 4.5 三層世界との連動

| 仕組み | 説明 |
|--------|------|
| `layers_involved` | クエストがどの層にまたがるか定義 |
| `world.get_state()` / `set_state()` | クエスト進行が世界状態を変え、他の層にも波及 |
| 前提条件 | 「深界の歪み度が一定以上」など、三層状態をトリガーに使える |
| 結果の分岐 | プレイヤーの選択がどの層に影響するかがクエストごとに異なる |

---

## 5. 三層世界状態管理

### 5.1 ワールドステート構造

```json
// data/world_state.json（初期状態テンプレート）
{
  "global": {
    "chapter": 1,
    "story_phase": "awakening"
  },
  "layers": {
    "physical": {
      "distortion": 0,
      "healed_count": 0,
      "corruption_zones": []
    },
    "depth": {
      "distortion": 0,
      "crystallization": 0,
      "sealed_cores": []
    },
    "dream": {
      "stability": 100,
      "fragments_collected": 0,
      "unlocked_areas": []
    }
  },
  "flags": {},
  "quest_states": {}
}
```

### 5.2 三層連動ルールエンジン (Lua)

層間の影響をLuaルールとして定義する。

```lua
-- scripts/common/world_rules.lua

-- 地上で浄化 → 深界に歪みが沈殿
rules.register("on_state_change", function(key, old, new)

  if key == "physical.healed_count" and new > old then
    local depth_dist = world.get_state("depth.distortion")
    world.set_state("depth.distortion", depth_dist + (new - old) * 0.5)
  end

  if key == "depth.crystallization" and new > old then
    local stability = world.get_state("dream.stability")
    world.set_state("dream.stability",
      math.max(0, stability - (new - old) * 2))
  end

  if key == "dream.stability" and new <= 0 then
    event.trigger("dream_collapse")
    world.set_state("physical.distortion",
      world.get_state("physical.distortion") + 10)
  end

end)
```

### 5.3 「治すたびに壊れる」サイクル

物語の中核テーマをゲームメカニクスとして体現するフィードバックループ。

```
地上で浄化 → 深界に歪み蓄積 → 結晶化進行 → 夢界の安定度低下
    ↑                                              ↓
    ←←←←← 夢界崩壊で地上に異変 ←←←←←←←←←←←←←←←←←
```

プレイヤーが浄化を繰り返すほど、別の層が壊れていく。

### 5.4 層の移動

| 要素 | 仕様 |
|------|------|
| 移動手段 | 特定の「裂け目」ポイントでのみ層間移動可能 |
| 移動条件 | ストーリー進行やアイテムで裂け目が開放される |
| 演出 | 層ごとに画面エフェクト（色調変化、BGM切替） |
| 制限 | 一部クエスト中は移動不可（ロック制御はLuaから） |

### 5.5 NPC/クエストとの連携パターン

| 連携パターン | 例 |
|-------------|-----|
| NPCの出現/消失 | `dream.stability < 30` で夢界のNPCが消え始める |
| セリフ変化 | `depth.distortion` の値でNPCの警告度合いが変わる |
| クエスト開放 | `physical.healed_count >= 3` でサブクエスト出現 |
| クエスト分岐 | プレイヤーの浄化/放置選択が世界状態に反映され、後のクエスト展開が変わる |
| 商店品揃え | 層の状態によって購入可能なアイテムが変動 |

---

## 6. 既存システム見直し

### 6.1 優先度1: 未統合・未完成（正確性）

#### 6.1.1 ステータス効果のバトル統合

`StatusEffectManager` は完成しているが、`BattleScene` から一切呼ばれていない。

**統合ポイント:**

| バトルフェーズ | 呼び出すメソッド | 効果 |
|---------------|-----------------|------|
| ターン開始 | `on_turn_start()` | 毒ダメージ、期間管理 |
| 行動判定 | `get_action_restrictions()` | 睡眠/石化/停止チェック |
| ATB進行 | `get_atb_multiplier()` | スロウ/ヘイスト反映 |
| 攻撃命中 | `get_accuracy_multiplier()` | 暗闘反映 |
| ダメージ計算 | `get_damage_reduction_rate()` | プロテス反映 |
| 被物理攻撃 | `on_physical_attack()` | 睡眠解除 |
| 混乱時 | `get_random_action()` | ランダム行動 |

#### 6.1.2 ジョブステータス補正の実装

`job_ability.py:156` の `apply_job_stats()` が `pass` のまま。

**修正内容:** ジョブの `stat_bonuses` に定義された倍率を基本ステータスに適用する。

#### 6.1.3 装備ステータスの適用

`equipment.py:304-319` の `apply_equipment_stats()` がボーナス計算のみで適用しない。

**修正内容:** 装備ボーナスをステータス計算パイプラインに組み込む。

#### 6.1.4 ATBとステータス効果の接続

`atb.py` が `haste`/`slow` ブール値を直接参照しているが、`StatusEffectManager.get_atb_multiplier()` と連携していない。

**修正内容:** ATB進行時に `StatusEffectManager` から倍率を取得して適用する。

### 6.2 優先度2: ハードコード問題（拡張性）

#### 6.2.1 パーティ定義の外部化

`battle_scene.py:108-137` のインライン定義を `CharacterDataManager` に一元化する。

#### 6.2.2 魔法コマンドのデータ駆動化

`battle_scene.py:52-56` のハードコード魔法リストを `AbilitySystem` (abilities.json) から取得する形に変更。

#### 6.2.3 アイテムコマンドのデータ駆動化

`battle_scene.py:57-60` のハードコードアイテムリストを `ItemSystem` / `Inventory` から取得する形に変更。

#### 6.2.4 ターゲット選択UIの実装

`battle_scene.py:643-647` のランダム選択をプレイヤーのカーソル操作による対象選択に変更。

### 6.3 優先度3: 完成度向上

| 課題 | 修正内容 |
|------|---------|
| 混乱状態のランダム行動が未接続 | バトルの行動判定フェーズで `get_random_action()` を呼び出す |
| 装備耐性ボーナスが未実装 | `_get_resistance()` で装備の耐性値を反映する |
| 敵AIが通常攻撃のみ | 敵データにアビリティリストを追加し、AIルーチンで選択させる |
| プロテス/シェルが未接続 | `_deal_damage()` 内で `get_damage_reduction_rate()` を適用する |

### 6.4 ステータス計算の統一パイプライン

```
基本ステータス（レベルテーブル）
  × ジョブ補正（job.stat_bonuses）
  + 装備補正（equipment.stat_bonuses）
  = 最終ステータス
```

これを `CharacterDataManager` に一元化し、バトルシーンはそこから値を取得するだけにする。

---

## 7. ファイル構成（新規/変更）

### 7.1 新規ファイル

| パス | 目的 |
|------|------|
| `src/scripting/engine.py` | Luaランタイム管理、サンドボックス、ホットリロード |
| `src/scripting/api.py` | Lua→Python APIバインディング (npc, quest, world, flag, event, rules) |
| `src/npc/npc_manager.py` | NPC配置・表示・対話トリガー管理 |
| `src/npc/dialogue_renderer.py` | 対話ウィンドウ描画（テキスト送り、選択肢UI） |
| `src/quest/quest_manager.py` | クエスト状態管理・前提条件チェック・報酬付与 |
| `src/quest/quest_log_ui.py` | クエストログUI描画 |
| `src/world/world_state_manager.py` | 三層世界状態管理・ルールエンジン |
| `src/world/layer_transition.py` | 層間移動の制御・演出 |
| `data/npcs.json` | NPC定義データ |
| `data/quests.json` | クエスト定義データ |
| `data/world_state.json` | ワールドステート初期値テンプレート |
| `scripts/npc/` | NPC対話Luaスクリプト群 |
| `scripts/quest/` | クエスト進行Luaスクリプト群 |
| `scripts/event/` | イベントシーンLuaスクリプト群 |
| `scripts/common/world_rules.lua` | 三層連動ルール |
| `requirements.txt` | lupa追加 |

### 7.2 変更ファイル

| パス | 変更内容 |
|------|---------|
| `src/scenes/battle_scene.py` | ステータス効果統合、データ駆動化、ターゲット選択UI |
| `src/scenes/map_scene.py` | NPC表示・対話トリガー、層間移動、クエストマーカー |
| `src/scenes/menu_scene.py` | クエストログタブ追加 |
| `src/battle/atb.py` | StatusEffectManager連携 |
| `src/battle/damage.py` | ステータス効果によるダメージ補正統合 |
| `src/battle/job_ability.py` | `apply_job_stats()` 実装 |
| `src/battle/equipment.py` | `apply_equipment_stats()` 実装 |
| `src/battle/status_effects.py` | 装備耐性ボーナス反映 |
| `src/entities/character.py` | 統一ステータス計算パイプライン |
| `data/enemies.json` | 敵AIアビリティリスト追加 |

---

## 8. 対話表示の `npc.say()` / `npc.choice()` 実行フロー

Luaスクリプトは同期的に `npc.say()` を呼ぶが、実際の表示はPygameの非同期描画ループで行う。

```
Lua: npc.say("アルマ", "旅の者か…")
  ↓
Python API: DialogueRenderer.show(speaker, text)
  ↓
ゲームループ: テキスト1文字ずつ描画 → プレイヤーの入力待ち
  ↓
入力検知: Luaコルーチンを再開
  ↓
Lua: 次の npc.say() または npc.choice() へ進む
```

**コルーチン方式:** Luaスクリプトをコルーチンとして実行し、`npc.say()` / `npc.choice()` でyieldしてPython側に制御を返す。プレイヤー入力後にresumeして次の行へ進む。

---

## 9. 制約・前提条件

| 項目 | 内容 |
|------|------|
| Python | 3.10+ |
| lupa | 最新安定版 |
| Pygame | 2.5.0+ |
| pytmx | 3.32+ |
| セーブ/ロード | 本仕様の対象外（別途設計） |
| 実際のストーリー内容 | 本仕様はシステム仕様のみ。セリフ・イベント内容は別途制作 |
