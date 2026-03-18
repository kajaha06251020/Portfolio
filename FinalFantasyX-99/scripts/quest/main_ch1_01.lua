function on_check_available()
  return true
end

function on_accept()
  quest.set_stage("awakening")
  quest.set_objective("万層紋について調べる")
end

function on_stage_event(trigger)
  local stage = quest.get_stage()
  if stage == "awakening" and trigger == "met_alma" then
    quest.set_stage("seek_wisdom")
    quest.set_objective("アルマに万層紋について聞く")
  end
end
