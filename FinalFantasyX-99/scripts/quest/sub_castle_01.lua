function on_check_available()
  return world.get_state("depth.distortion") >= 3
end

function on_accept()
  npc.say("アルマ", "深界に異変が起きておる。調べてきてくれぬか。")
  quest.set_stage("investigate")
  quest.set_objective("深界の歪みの原因を調べる")
end

function on_stage_event(trigger)
  local stage = quest.get_stage()
  if stage == "investigate" and trigger == "depth_crystal_found" then
    quest.set_stage("report")
    quest.set_objective("アルマに報告する")
  elseif stage == "report" and trigger == "talk_alma" then
    npc.say("アルマ", "そうか…やはり結晶化が始まっておるか。")
    local choice = npc.choice({"結晶を渡す", "結晶を手元に残す"})
    if choice == 1 then
      npc.say("アルマ", "預かろう。ワシが封印を施す。")
      world.set_state("depth.distortion", world.get_state("depth.distortion") - 2)
      flag.set("crystal_given_alma", true)
    else
      npc.say("アルマ", "…そうか。だが気をつけよ。")
      flag.set("crystal_kept", true)
    end
    quest.complete()
  end
end
