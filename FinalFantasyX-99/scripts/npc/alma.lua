function on_talk()
  local layer = world.get_layer()
  if layer ~= "physical" then return end

  -- ドレイク討伐後の報告
  if flag.get("drake_defeated") and not flag.get("ch1_complete") then
    npc.say("アルマ", "おお…お主、ドレイクを倒したのか！")
    npc.say("アルマ", "見事じゃ。やはり万層紋の力は本物のようじゃな。")
    npc.say("アルマ", "これで大地の歪みも少しは収まるじゃろう。")
    npc.say("アルマ", "…だが、これは始まりに過ぎぬ。")
    npc.say("アルマ", "深界の影響は、まだこの世界を蝕んでおる。")
    npc.say("アルマ", "いずれ、より大きな試練が待ち受けておろう。")
    flag.set("ch1_complete", true)
    quest.update("main_ch1_01", "completed")
    quest.set_objective("第1章 完了")
    return
  end

  -- 第1章完了後
  if flag.get("ch1_complete") then
    npc.say("アルマ", "よくぞ戻った。世界はまだ揺れておる…")
    npc.say("アルマ", "次なる手がかりを探すのじゃ。")
    return
  end

  -- 初回会話
  if not flag.get("met_alma") then
    npc.say("アルマ", "旅の者か…この地に足を踏み入れたのは久しぶりじゃ。")
    npc.say("アルマ", "ほう…お主、その腕の紋様…万層紋か？")
    npc.say("アルマ", "この世界は今、崩壊の危機にある。")
    npc.say("アルマ", "北の竜の洞窟にドレイクという竜が棲み着いてな。")
    npc.say("アルマ", "あやつが暴れるせいで、大地の歪みが進んでおるのじゃ。")
    local choice = npc.choice({"調査する", "考えさせてくれ"})
    if choice == 1 then
      npc.say("アルマ", "頼もしいのう！")
      npc.say("アルマ", "竜の洞窟はフィールドの北にある洞窟じゃ。")
      npc.say("アルマ", "道中は魔物も多い。町の店で装備を整えてから行くがよい。")
      npc.say("アルマ", "気をつけて行くのじゃぞ。")
      flag.set("met_alma", true)
      flag.set("quest_investigate_cave", true)
      quest.start("main_ch1_01")
      quest.set_objective("竜の洞窟でドレイクを倒す")
      event.trigger("met_alma")
    else
      npc.say("アルマ", "ふむ…無理もない。じゃが、時間がないのも事実じゃ。")
      npc.say("アルマ", "気が変わったらまた来るがよい。")
    end
    return
  end

  -- クエスト受注後、ドレイク未討伐
  if flag.get("quest_investigate_cave") and not flag.get("drake_defeated") then
    npc.say("アルマ", "竜の洞窟は北にある。ドレイクを倒してくるのじゃ。")
    npc.say("アルマ", "装備は十分か？町の店で準備するのも良いぞ。")
    return
  end

  -- デフォルト
  npc.say("アルマ", "万層紋の力、くれぐれも過信するでないぞ。")
end
