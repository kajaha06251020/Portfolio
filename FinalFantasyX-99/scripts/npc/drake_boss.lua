function on_visible()
  -- ドレイク討伐後は表示しない
  return not flag.get("drake_defeated")
end

function on_talk()
  if flag.get("drake_defeated") then
    return
  end

  npc.say("ドレイク", "グルルル…人間か…")
  npc.say("ドレイク", "この洞窟は我の領域だ。")
  npc.say("ドレイク", "去れ！さもなくば灰にしてくれる！")

  local choice = npc.choice({"戦う！", "引き返す"})
  if choice == 1 then
    npc.say("ドレイク", "愚かな…！滅びるがいい！")
    local result = event.start_battle("drake", 1, 12)
    if result == "victory" then
      flag.set("drake_defeated", true)
      quest.update("main_ch1_01", "report_back")
      quest.set_objective("アルマに報告する")
      npc.say("", "ドレイクを倒した！")
      npc.say("", "大地の揺れが収まっていく…")
      npc.say("", "城下町のアルマに報告しよう。")
    else
      npc.say("", "…意識が遠のいていく…")
    end
  else
    npc.say("ドレイク", "フン…賢明な判断だ。二度と来るな。")
  end
end
