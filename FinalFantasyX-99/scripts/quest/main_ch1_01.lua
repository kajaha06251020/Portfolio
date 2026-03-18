function on_check_available()
  return true
end

function on_accept()
  quest.set_stage("investigate_cave")
  quest.set_objective("竜の洞窟でドレイクを倒す")
end

function on_stage_event(trigger)
  local stage = quest.get_stage()

  if stage == "investigate_cave" and trigger == "met_alma" then
    quest.set_stage("investigate_cave")
    quest.set_objective("竜の洞窟でドレイクを倒す")
  end

  if trigger == "drake_defeated" then
    quest.set_stage("report_back")
    quest.set_objective("アルマに報告する")
  end
end
