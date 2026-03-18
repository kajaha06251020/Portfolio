function on_talk()
  npc.say("町の住人", "最近、空の色がおかしいんだ…")
  local choice = npc.choice({"気になる", "そうか"})
  if choice == 1 then
    npc.say("町の住人", "やっぱりそう思うか？深界の影響かもしれないな。")
  else
    npc.say("町の住人", "…気にならないのか？まあいいさ。")
  end
end
