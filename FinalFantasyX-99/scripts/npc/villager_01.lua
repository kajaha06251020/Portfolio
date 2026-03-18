function on_talk()
  -- 第1章完了後
  if flag.get("ch1_complete") then
    npc.say("町の住人", "お前がドレイクを倒したんだって？すごいな！")
    npc.say("町の住人", "おかげで空の色も少し戻ってきた気がするよ。")
    return
  end

  -- ドレイク討伐後（報告前）
  if flag.get("drake_defeated") then
    npc.say("町の住人", "なんだか地面の揺れが収まったような…？")
    npc.say("町の住人", "何かあったのか？")
    return
  end

  -- クエスト受注後
  if flag.get("quest_investigate_cave") then
    npc.say("町の住人", "竜の洞窟に行くのか？気をつけろよ。")
    npc.say("町の住人", "ドレイクはかなり手強いらしいぞ。")
    npc.say("町の住人", "武器屋と道具屋で準備していった方がいい。")
    return
  end

  -- アルマに会った後
  if flag.get("met_alma") then
    npc.say("町の住人", "アルマ老師に会ったのか。あの人は物知りだよ。")
    npc.say("町の住人", "北の洞窟のことも聞いたんだろ？")
    return
  end

  -- 初期状態
  npc.say("町の住人", "最近、空の色がおかしいんだ…")
  local choice = npc.choice({"気になる", "そうか"})
  if choice == 1 then
    npc.say("町の住人", "やっぱりそう思うか？北の洞窟から何か出てきてるみたいだ。")
    npc.say("町の住人", "城の近くにいるアルマ老師なら何か知ってるかもしれないぞ。")
  else
    npc.say("町の住人", "…気にならないのか？まあいいさ。")
  end
end
