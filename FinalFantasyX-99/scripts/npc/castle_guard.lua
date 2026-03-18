function on_talk()
  if flag.get("ch1_complete") then
    npc.say("衛兵", "ドレイク討伐の報告は王にも届いておる。")
    npc.say("衛兵", "お前の活躍、我々も誇りに思う。")
    return
  end

  if flag.get("quest_investigate_cave") then
    npc.say("衛兵", "竜の洞窟へ向かうのか？")
    npc.say("衛兵", "あの洞窟は危険だ。十分に準備してから行け。")
    return
  end

  npc.say("衛兵", "ここは王城だ。怪しい者は通さんぞ。")
  npc.say("衛兵", "…ふむ、旅人か。城下町のアルマ老師を訪ねるといい。")
end
