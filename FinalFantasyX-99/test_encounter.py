#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
敵グループシステムのテストスクリプト
"""

import json
from pathlib import Path
from src.entities.enemy_system import EnemySystem
from src.battle.encounter import EncounterManager


def test_encounter_groups_data():
    """敵グループJSONデータの確認"""
    print("=" * 60)
    print("【敵グループデータの読み込みテスト】")
    print("=" * 60)
    
    groups_file = Path(__file__).parent / "data" / "encounter_groups.json"
    with open(groups_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    groups = data.get("encounter_groups", {})
    print(f"\n読み込んだ敵グループ数: {len(groups)}")
    
    for group_id, group_data in groups.items():
        print(f"\n【{group_data['name']}】 (難度: {group_data['difficulty']})")
        print(f"  グループID: {group_id}")
        print(f"  推奨レベル: {group_data['recommended_level_range']}")
        enemy_composition = [f"{e['enemy_type']}x{e['min_count']}-{e['max_count']}" for e in group_data['enemies']]
        print(f"  敵構成: {enemy_composition}")
        print(f"  報酬: EXP {group_data['base_rewards']['exp']} / Gold {group_data['base_rewards']['gold']}")
        
        # ドロップ確認
        drops = group_data.get("drops", [])
        if drops:
            print(f"  ドロップアイテム:")
            for drop in drops:
                print(f"    - {drop['item_id']} (ドロップ率: {drop['rate']}%)")
        else:
            print(f"  ドロップアイテム: なし ⚠️")


def test_enemy_system():
    """EnemySystemの初期化テスト"""
    print("\n" + "=" * 60)
    print("【EnemySystemの初期化テスト】")
    print("=" * 60)
    
    enemy_system = EnemySystem()
    
    # 敵タイプの読み込み確認
    print(f"\n読み込んだ敵タイプ数: {len(enemy_system.enemies_data)}")
    print(f"敵タイプ一覧: {', '.join(enemy_system.enemies_data.keys())}")
    
    # 敵グループの読み込み確認
    print(f"\n読み込んだ敵グループ数: {len(enemy_system.encounter_groups_data)}")
    print(f"敵グループ一覧: {', '.join(enemy_system.encounter_groups_data.keys())}")
    
    # マップデータの読み込み確認
    print(f"\n読み込んだマップ数: {len(enemy_system.maps_data)}")
    print(f"マップ一覧: {', '.join(enemy_system.maps_data.keys())}")


def test_encounter_generation():
    """敵グループ生成のテスト"""
    print("\n" + "=" * 60)
    print("【敵グループ生成のテスト】")
    print("=" * 60)
    
    enemy_system = EnemySystem()
    
    # テスト用敵グループを生成
    test_groups = [
        ("group_slime_only", 1),
        ("group_slime_goblin", 3),
        ("group_drake_single", 15),
    ]
    
    for group_id, party_level in test_groups:
        print(f"\n【{group_id}】 - パーティレベル: {party_level}")
        
        encounter_group = enemy_system.create_encounter_group(group_id, party_level=party_level)
        
        if encounter_group:
            print(f"  グループ名: {encounter_group.name}")
            print(f"  生成敵数: {len(encounter_group.enemies)}")
            
            for i, enemy in enumerate(encounter_group.enemies, 1):
                print(f"    敵{i}: {enemy.name} レベル {enemy.level} (HP: {enemy.max_hp}, 攻撃: {enemy.attack})")
            
            print(f"  総EXP報酬: {encounter_group.total_exp_reward()}")
            print(f"  総ゴール報酬: {encounter_group.total_gold_reward()}")
        else:
            print(f"  ❌ 敵グループの生成に失敗しました")


def test_zone_encounter():
    """ゾーン別敵遭遇のテスト"""
    print("\n" + "=" * 60)
    print("【ゾーン別敵遭遇のテスト】")
    print("=" * 60)
    
    enemy_system = EnemySystem()
    
    # field_start マップをテスト
    map_id = "field_start"
    map_data = enemy_system.get_map(map_id)
    
    if map_data:
        print(f"\nマップ: {map_data['name']} (マップID: {map_id})")
        print(f"マップ全体のエンカウント率: {map_data.get('encounter_rate', 0)}%")
        
        zones = map_data.get("encounter_zones", [])
        print(f"敵遭遇ゾーン数: {len(zones)}")
        
        for zone in zones:
            print(f"\n  ゾーン: {zone['description']} (ID: {zone['zone_id']})")
            print(f"    位置: ({zone['x']}, {zone['y']}) - サイズ: {zone['width']}x{zone['height']}")
            print(f"    エンカウント率: {zone.get('encounter_rate', 0)}%")
            print(f"    敵グループ: {', '.join(zone.get('enemy_groups', []))}")


def test_encounter_manager():
    """EncounterManagerの動作テスト"""
    print("\n" + "=" * 60)
    print("【EncounterManagerの動作テスト】")
    print("=" * 60)
    
    encounter_manager = EncounterManager()
    
    # マップに入場
    encounter_manager.enter_map("field_start")
    print(f"\n現在のマップ: {encounter_manager.get_current_map_info()['name']}")
    
    # 利用可能なゾーンを確認
    zones = encounter_manager.get_available_zones_for_map("field_start")
    print(f"利用可能なゾーン数: {len(zones)}")


def main():
    """メイン処理"""
    print("\n🎮 敵グループシステム テストスイート 🎮\n")
    
    try:
        test_encounter_groups_data()
        test_enemy_system()
        test_encounter_generation()
        test_zone_encounter()
        test_encounter_manager()
        
        print("\n" + "=" * 60)
        print("✅ すべてのテストが完了しました")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
