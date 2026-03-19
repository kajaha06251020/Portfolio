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
