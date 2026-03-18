function on_talk()
  local layer = world.get_layer()
  if layer == "physical" then
    if not flag.get("met_alma") then
      npc.say("アルマ", "旅の者か…この地に足を踏み入れたのは久しぶりじゃ。")
      npc.say("アルマ", "お主、その腕の紋様…万層紋か？")
      flag.set("met_alma", true)
    else
      npc.say("アルマ", "万層紋の力、くれぐれも過信するでないぞ。")
    end
  end
end
