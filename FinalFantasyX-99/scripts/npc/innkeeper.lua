function on_talk()
    npc.say("宿屋の主人", "一晩50ゴールドです。お泊まりになりますか？")
    local choice = npc.choice({"はい", "いいえ"})
    if choice == 1 then
        if party.get_gold() >= 50 then
            party.remove_gold(50)
            party.rest()
            event.fade_out()
            event.wait(1.0)
            event.fade_in()
            npc.say("宿屋の主人", "ゆっくりお休みいただけましたか？よい旅を！")
        else
            npc.say("宿屋の主人", "お金が足りないようですね…")
        end
    else
        npc.say("宿屋の主人", "またのお越しを。")
    end
end
